# Notes

## night 10
Added buzzer awareness to press role: when time_remaining_s <= 3.0 and the press player is within 2.5 m of the ball, kick_toward the opponent goal (attack_goal_xy) instead of go_to_ball. Logic: the buzzer cuts all robot power but the ball keeps moving, so a ball already struck toward goal cannot be blocked after the horn. Verified obs key against RFL_RULES.md (line 95/148), kick_toward target shape against reference/team.py; lint CLEAR; 90 s practice loaded and played with no kickoff crash (0-1 mirror, cost 0). Code otherwise unchanged from my deterministic press/shade baseline.
