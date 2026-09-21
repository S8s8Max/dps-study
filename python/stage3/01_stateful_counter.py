"""ステートフル カウンター：NATS でセンサーイベントを受信しキーごとに集計する。
使い方:
  # ターミナル 1: データ生成
  python3 01_stateful_counter.py gen
  # ターミナル 2: カウンター
  python3 01_stateful_counter.py
"""
import asyncio
import json
import random
import sys
import time
from collections import defaultdict
import nats

NATS_URL = "nats://localhost:4222"
SUBJECT = "events.sensor.*"
PUBLISH_SUBJECT_FMT = "events.sensor.{}"
REPORT_INTERVAL = 5.0


async def run_generator():
    nc = await nats.connect(NATS_URL)
    print("[gen] NATS 接続: " + NATS_URL)
    sensors = ["pi-cpu", "pi-memory", "pi-temp"]
    bases = {"pi-cpu": 40.0, "pi-memory": 60.0, "pi-temp": 50.0}
    seq = 0
    try:
        while True:
            for s in sensors:
                val = max(0.0, bases[s] + random.gauss(0, 5))
                payload = json.dumps({"sensor_id": s, "value": round(val, 1), "seq": seq}).encode()
                await nc.publish(PUBLISH_SUBJECT_FMT.format(s), payload)
            seq += 1
            if seq % 10 == 0:
                print(f"[gen] {seq * len(sensors)} 件送信")
            await asyncio.sleep(1.0)
    except KeyboardInterrupt:
        print("[gen] 終了")
    finally:
        await nc.drain()


async def run_counter():
    nc = await nats.connect(NATS_URL)
    print(f"[counter] NATS 接続: {NATS_URL}")
    print(f"[counter] 購読: {SUBJECT}")

    # キーごとの状態: {sensor_id: {"count": int, "total": float, "latest": float}}
    state: dict[str, dict] = defaultdict(lambda: {"count": 0, "total": 0.0, "latest": 0.0})
    total_received = 0
    last_report = time.monotonic()

    async def handler(msg):
        nonlocal total_received, last_report
        data = json.loads(msg.data)
        key = data["sensor_id"]
        val = data["value"]

        # ステートを更新
        s = state[key]
        s["count"] += 1
        s["total"] += val
        s["latest"] = val
        total_received += 1

        # 定期レポート
        now = time.monotonic()
        if now - last_report >= REPORT_INTERVAL:
            last_report = now
            print(f"\n--- {REPORT_INTERVAL:.0f}秒ごとの集計 ---")
            for k in sorted(state):
                st = state[k]
                avg = st["total"] / st["count"] if st["count"] else 0.0
                print(f"  {k:<12}: {st['count']:3d} 件  最新値={st['latest']:.1f}  平均={avg:.1f}")
            print(f"--- 累計 {total_received} 件受信 ---")

    await nc.subscribe(SUBJECT, cb=handler)
    print("[counter] 待機中 (Ctrl-C で終了)\n")
    try:
        await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n[counter] 終了: 合計 {total_received} 件")
        await nc.drain()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "counter"
    if mode == "gen":
        asyncio.run(run_generator())
    else:
        asyncio.run(run_counter())
