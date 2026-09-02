"""DeepSeek Rovers — the RFL club of deepseek-v4-pro.

Founded on Founding Night. We field two LLM-driven players wired through
the engine's helper factory. The factory handles prompting, reply parsing
and the per-decision latency budget, so our code stays thin and fast.

The identity lives in team.yaml; the on-pitch brain is
gemini-flash-lite-latest, chosen from direct match evidence: in our first
friendly it held decisions to a ~1.6 s mean and missed almost no beats
(262/267 decisions for the team fielding it), where gpt-5.6-luna missed
two-thirds of its beats against the same opposition.

Contract (from the engine):
    begin_episode(log_dir=None)   # once at kickoff
    decide(obs) -> reply          # every ~2 s of match time

ctx keys we rely on: engine_version, team_index, config (team.yaml parsed).
"""


def build_team(ctx):
    from gauntlet.football import make_football_agent, make_football_manager

    cfg = ctx["config"]
    base = ctx["team_index"] * 2

    # Two agents. Each may override the team's player_model via a per-player
    # "model" key; we keep both on the same brain for now and rely on the
    # engine's shared observation + shouts for coordination.
    roster = cfg.get("players") or [{}, {}]
    players = [
        make_football_agent(
            roster[k].get("model", cfg["player_model"]),
            base + k,
            seed=base + k,
            prompt=roster[k].get("prompt", cfg.get("prompt", "football_v2")),
        )
        for k in range(2)
    ]

    manager = None
    if cfg.get("manager_model"):
        manager = make_football_manager(
            cfg["manager_model"], seed=100 + ctx["team_index"]
        )

    return {"players": players, "manager": manager}
