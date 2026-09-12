"""
DeepSeek Rovers — deterministic 2v2 tactics. No LLM calls, no latency,
no spend.

Roles, recomputed every decision from the shared detections:
  * press  — the player nearer the ball drives it at the opponent goal
             via the engine's go_to_ball skill (which already orbits to the
             correct side of the ball and steers + dribbles goal-ward).
  * shade  — the farther player holds a point between the ball and our own
             goal, ready for the second ball or a rebound.

A fallen robot holds still. A stale ball memory (not seen for >2 s) sends
players back toward their own goal rather than chasing a ghost.
"""

import math


def _d(a, b):
    """Euclidean distance between two (x, y) points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _pt(v, default=None):
    if v is None:
        return default
    try:
        return (float(v[0]), float(v[1]))
    except (TypeError, IndexError, ValueError):
        return default


class Rover:
    """One player. Identical code for both shirts; role falls out of geometry."""

    def __init__(self, index):
        self.index = index
        self.role = None  # 'press' or 'shade'; used only to gate shouts.
        self.shade_target = None  # last covering point, for the dead-zone.
        self.shade_ball = None  # ball position that last chose the shade point.

    def begin_episode(self, log_dir=None):
        self.role = None
        self.shade_target = None
        self.shade_ball = None

    def decide(self, obs):
        det = obs.get("detections") or {}
        ball = det.get("ball") if isinstance(det, dict) else None
        selfp = obs.get("self") or {}
        you = obs.get("you") or {}
        t_left = obs.get("time_remaining_s")

        my_pos = _pt(selfp.get("field_xy"))
        attack = _pt(you.get("attack_goal_xy"))
        defend = _pt(you.get("defend_goal_xy"))

        # Fallen: lie still, wait for self-recovery, and tell the
        # teammate to take over pressing.
        if selfp.get("fallen"):
            if self.role != "down":
                self.role = "down"
                return {"skill": "hold", "say": "down"}
            return {"skill": "hold"}

        # No localization and no ball: stay put.
        if my_pos is None and (ball is None or not ball.get("field_xy")):
            return {"skill": "hold"}

        # Ball lost from sight for a while: fall back toward our own goal.
        if ball is None or not ball.get("field_xy"):
            if defend is not None:
                self.role = "shade"
                return {"skill": "walk_to", "target": list(defend)}
            return {"skill": "hold"}

        bxy = _pt(ball.get("field_xy"))
        if bxy is None:
            return {"skill": "hold"}

        # Stale memory (not currently seen, age rising): recover position.
        if not ball.get("seen_now", True) and ball.get("age_s", 0.0) > 2.0:
            if defend is not None:
                self.role = None
                return {"skill": "walk_to", "target": list(defend)}
            return {"skill": "hold"}

        my_d = _d(my_pos, bxy) if my_pos is not None else 1e9

        # Distance from the ball to the nearest visible, standing teammate.
        # A fallen teammate cannot press; counting them makes the upright
        # player misjudge who is nearer and abandon a loose ball.
        teammates = det.get("teammates") or []
        t_d = 1e9
        for t in teammates:
            if t.get("fallen"):
                continue
            txy = _pt(t.get("field_xy"))
            if txy is not None:
                t_d = min(t_d, _d(txy, bxy))

        # The nearer player presses. A small hysteresis margin prevents
        # role flapping when the two are side by side.
        press = my_d <= t_d + 0.4

        if press:
            new_role = "press"
            # Clear danger: if the ball is right on our own goal and I am
            # on it, hoof it upfield toward the opponent goal instead of
            # dribbling across our own six-yard line.
            near_own_goal = (defend is not None and _d(bxy, defend) <= 5.0)
            if near_own_goal and my_d <= 2.5 and attack is not None:
                reply = {"skill": "kick_toward", "target": list(attack)}
                say = "clearing" if self.role != new_role else ""
            # Near the buzzer: strike at goal rather than dribble. The
            # buzzer cuts all power, so a ball already moving at the
            # goal cannot be blocked once the clock hits zero.
            elif (t_left is not None and t_left <= 3.0 and my_d <= 2.5
                    and attack is not None):
                reply = {"skill": "kick_toward", "target": list(attack)}
                say = "shooting" if self.role != new_role else ""
            else:
                # go_to_ball approaches the correct side (orbiting if
                # needed) and drives the ball at the opponent goal.
                reply = {"skill": "go_to_ball"}
                say = "I've got it" if self.role != new_role else ""
        else:
            new_role = "shade"
            if defend is not None and attack is not None:
                # Hold goal-side of the ball, but how deep depends on which
                # half the ball is in. When the ball is in our half, drop
                # deep toward our own goal to protect the empty net; when
                # the ball is in their half, stay close enough to support
                # the press or pounce on a rebound.
                ax = attack[0] - defend[0]
                ay = attack[1] - defend[1]
                mx = (attack[0] + defend[0]) / 2.0
                my = (attack[1] + defend[1]) / 2.0
                own_half = (bxy[0] - mx) * ax + (bxy[1] - my) * ay < 0.0
                # Stay deeper: the higher the fraction, the closer the shade
                # holds to our own goal. When we attack (ball in their half)
                # the shade must not follow high upfield — that is what left
                # us exposed to through-ball counters.
                depth = 0.82 if own_half else 0.76
                tx = bxy[0] + depth * (defend[0] - bxy[0])
                ty = bxy[1] + depth * (defend[1] - bxy[1])
                # Dead-zone: only retarget when the ball has moved
                # meaningfully since the covering point was last chosen,
                # so the shade does not jitter (and fall) while the ball
                # barely moves at the press player's feet.
                if self.shade_ball is None or _d(self.shade_ball, bxy) > 1.5:
                    self.shade_target = [tx, ty]
                    self.shade_ball = bxy
                target = self.shade_target if self.shade_target is not None else [tx, ty]
                reply = {"skill": "walk_to", "target": target}
            else:
                # No own-goal fix available; stay put rather than crash.
                reply = {"skill": "hold"}
            say = "covering" if self.role != new_role else ""

        if say:
            # Shouts are public by design; keep them sparse (only on role
            # changes) so the pitch isn't noise.
            reply["say"] = say

        self.role = new_role
        return reply


def build_team(ctx):
    """Return two identical hand-written tactical players."""
    return {
        "players": [Rover(0), Rover(1)],
        "manager": None,
    }
