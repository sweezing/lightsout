"""Load test for live delivery (Feature 4, Table 5: 100 concurrent connections,
delivery <= 3 s).

Opens N WebSocket readers looking at the same region, posts one card, and
reports how many readers received it and how long the slowest one took.

    pip install websockets
    python tools/ws_load_test.py                 # against http://localhost:8080
    python tools/ws_load_test.py --n 200 --base http://localhost:8080
"""
import argparse
import asyncio
import json
import time
import urllib.request
import uuid

import websockets

async def reader(url, ready, got, marker):
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"type": "viewport", "min_x": -1500, "min_y": -1500, "max_x": 1500, "max_y": 1500}))
        await ws.recv()
        ready.append(1)
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), 15))
            if msg.get("type") == "card.created" and msg["card"]["text"] == marker:
                got.append(time.monotonic())
                return

async def main(base, n):
    ws_url = base.replace("http", "ws", 1) + "/ws/canvas/"
    marker = f"load test {uuid.uuid4().hex[:6]}"
    ready, got = [], []
    tasks = [asyncio.create_task(reader(ws_url, ready, got, marker)) for _ in range(n)]
    while len(ready) < n:
        await asyncio.sleep(0.05)

    t0 = time.monotonic()
    req = urllib.request.Request(
        f"{base}/api/cards/", method="POST",
        data=json.dumps({"text": marker, "x": 5, "y": 5}).encode(),
        headers={"Content-Type": "application/json", "X-Session-Token": uuid.uuid4().hex},
    )
    await asyncio.to_thread(urllib.request.urlopen, req)
    await asyncio.gather(*tasks, return_exceptions=True)
    slowest = max(got) - t0 if got else float("nan")
    verdict = "PASS" if len(got) == n and slowest <= 3 else "FAIL"
    print(f"{len(got)}/{n} readers received the card; slowest {slowest:.3f} s (target <= 3 s) {verdict}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    asyncio.run(main(a.base.rstrip("/"), a.n))
