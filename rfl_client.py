"""RFL client SDK (rfl-0.2) - connect a team to a networked RFL match.

Self-contained: copy this single file into your team's codebase. Requires
only `websockets`, `numpy`, and `Pillow`. Your compute runs on YOUR machine;
the game server only ever sees your velocity commands.

Usage:
    from rfl_client import RFLClient

    def my_player(player_index, obs):
        # obs matches docs/RFL_RULES.md; obs["frames"] is a list of two
        # numpy RGB arrays [older, current]. Return {"vx","vy","wz"}.
        return {"vx": 0.5, "vy": 0.0, "wz": 0.0}

    RFLClient(
        url="ws://127.0.0.1:8800",
        team_card={"name": "My Team", "code": "MYT",
                   "color": [0.2, 0.8, 0.3], "color_name": "green"},
        player_fn=my_player,
    ).run()

player_fn is called concurrently for your two players; keep it thread-safe.
Reply within the server's deadline (sent in `settings` and per message) or
the decision is lost - that is the league's packet-drop rule, not an error.
"""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import io
import json


class RFLClient:
    def __init__(self, url: str, team_card: dict, player_fn,
                 max_workers: int = 2):
        self.url = url
        self.team_card = dict(team_card)
        self.player_fn = player_fn
        self.max_workers = max_workers
        self.team_index = None
        self.settings = {}
        self.fixture = None

    @staticmethod
    def _decode_frames(obs: dict) -> dict:
        import numpy as np
        from PIL import Image
        frames = []
        for b64 in obs.pop("frames_jpeg", []):
            frames.append(np.array(Image.open(io.BytesIO(base64.b64decode(b64)))))
        obs["frames"] = frames
        return obs

    def run(self):
        asyncio.run(self._run())
        return self.fixture

    async def _run(self):
        import websockets
        pool = concurrent.futures.ThreadPoolExecutor(self.max_workers)
        async with websockets.connect(self.url, max_size=8 * 1024 * 1024) as ws:
            hello = json.loads(await ws.recv())
            assert hello.get("type") == "hello", f"unexpected: {hello}"
            self.team_index = hello["team_index"]
            self.settings = hello.get("settings", {})
            await ws.send(json.dumps({"type": "register", **self.team_card}))
            print(f"[{self.team_card.get('code')}] registered as team "
                  f"{self.team_index} (engine {hello.get('engine')})")
            loop = asyncio.get_running_loop()

            async def answer(m):
                obs = self._decode_frames(m["obs"])
                try:
                    cmd = await loop.run_in_executor(
                        pool, self.player_fn, m["player"], obs)
                except Exception as e:
                    print(f"[{self.team_card.get('code')}] player_fn error: {e}")
                    return
                if cmd:
                    await ws.send(json.dumps({
                        "type": "cmd", "player": m["player"],
                        "seq": m["seq"], "cmd": cmd}))

            async for raw in ws:
                m = json.loads(raw)
                t = m.get("type")
                if t == "obs":
                    asyncio.ensure_future(answer(m))
                elif t == "kickoff":
                    print(f"[{self.team_card.get('code')}] kickoff!")
                elif t == "full_time":
                    self.fixture = m.get("fixture")
                    f = self.fixture
                    print(f"[{self.team_card.get('code')}] FULL TIME: "
                          f"{f['home']['code']} {f['home']['goals']} - "
                          f"{f['away']['goals']} {f['away']['code']}")
                    break
        pool.shutdown(wait=False, cancel_futures=True)
