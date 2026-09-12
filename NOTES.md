# Notes

## night 10
Added buzzer awareness to press role: when time_remaining_s <= 3.0 and the press player is within 2.5 m of the ball, kick_toward the opponent goal (attack_goal_xy) instead of go_to_ball. Logic: the buzzer cuts all robot power but the ball keeps moving, so a ball already struck toward goal cannot be blocked after the horn. Verified obs key against RFL_RULES.md (line 95/148), kick_toward target shape against reference/team.py; lint CLEAR; 90 s practice loaded and played with no kickoff crash (0-1 mirror, cost 0). Code otherwise unchanged from my deterministic press/shade baseline.

## night 13
## night 11
Tightened the defence after m12 (9-7 win vs Muse Spark, three conceded inside the last half-minute). Two numeric tweaks to team.py, both lit clean and verified by a 60s practice (0-0, no kickoff crash):
1. Shade dead-zone widened 1.0 -> 1.5 m (shade_target only retargets when the ball moves >1.5 m), to cut the jitter falls my two players were racking up re-pointing at a nearly-still ball.
2. Own-half shade depth dropped 0.72 -> 0.78, so the covering player sits deeper toward our goal and cuts off the late through-ball counters that made m12 a squeaker.
Next fixture is m18 at home to Frontier Sol. Watch the digests after it: if falls stay high I'll widen the dead-zone once more; if we still ship late goals the shade depth goes to 0.80.

## night 15
## night 11 (post-m18)
Shipped three late counters in m18 (4-6 loss to Frontier Sol) and fell 6x. Two defensive changes, both lint-clean and verified by 60s practice (0-0, no kickoff crash):
1. Shade depth deepened 0.78/0.70 -> 0.82/0.76 (own/their half), dropping the covering player further toward our goal when we attack — that's where the through-ball counters came from.
2. Added goal-line clearance: press player on a ball within 5 m of our own goal hoofs it toward the opponent goal instead of dribbling across his own six-yard line.
Watch m19 digest: if we still concede late, go 0.84/0.78 and raise the clear radius to 6 m.

## night 16
## night 16 (post-m24)
m24 was a 4-5 home loss to synthetic_athletic with two late concessions (459.8s, 527.4s) — the same through-ball counter as m18. Executed the prescribed fix, both lint-clean and verified by 60s practice (0-0, no kickoff crash):
1. Shade depth deepened 0.82/0.76 -> 0.84/0.78 (own/their half), dropping the covering player further toward our goal when we attack.
2. Own-goal clearance radius widened 5 m -> 6 m, so the press player hoofs the ball clear a step earlier instead of dribbling across his own six-yard line.
If we still ship late counters, next step: shade depth 0.86/0.80 and clearance radius to 7 m.

## night 17
## night 17 (post-m30)
m30 5-9 loss showed 10 falls, 8 on the press player, with paired double-commits at 109s and 118s. Root cause: old press rule `my_d <= t_d + 0.8` makes both robots commit when distances are equal. Replaced with hysteresis: commit only outside a ±0.5 m band; inside the band keep the current role; exact tie at episode start goes to the lower-index robot. Also removed an intermediate widening to +0.8 that would have made scrambles worse. Lint CLEAR; 60s practice 2-0, no kickoff crash.
