"""Run an RFL team as a REMOTE process (rfl-0.2 networked league).

This is what a participating team actually ships: their own process, their
own compute, their own model keys - connected to the game server by nothing
but the wire contract. This reference runner reuses the engine's LLM player
helpers; a real team would substitute anything they like.

    python teams/remote_runner.py ws://127.0.0.1:8800 \
        "Sample United" SMP 0.15,0.4,0.95 blue \
        llm:google:gemini-robotics-er-1.6-preview
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gauntlet.cli import _load_env_file  # noqa: E402
from rfl_client import RFLClient  # noqa: E402


def main():
    url, name, code, rgb, color_name, model = sys.argv[1:7]
    _load_env_file()
    from gauntlet.football import make_football_agent
    agents = {i: make_football_agent(model, i, seed=i) for i in (0, 1)}
    for a in agents.values():
        a.begin_episode()

    def player(idx, obs):
        obs["_frames"] = obs.pop("frames")
        obs["_frame"] = obs["_frames"][-1]
        return agents[idx].decide(obs)

    RFLClient(
        url=url,
        team_card={"name": name, "code": code,
                   "color": [float(v) for v in rgb.split(",")],
                   "color_name": color_name},
        player_fn=player,
    ).run()


if __name__ == "__main__":
    main()
