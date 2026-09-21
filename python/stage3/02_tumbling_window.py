"""タンブリング窓：NATS で受信したセンサーデータを固定時間窓で集計する。
使い方:
  # ターミナル 1: データ生成
  python3 01_stateful_counter.py gen
  # ターミナル 2: タンブリング窓集計
  python3 02_tumbling_window.py
"""
import asyncio
import json
import math
import statistics
import time
from collections import defaultdict
import nats

NATS_URL = "nats://localhost:4222"
SUBJECT = "events.sensor.*"
WINDOW_SEC = 5.0


def next_boundary(interval: float) -> float:
    now = time.time()
    return math.ceil(now / interval) * interval


class WindowAccumulator:
    def __init__(self):
        self.values: list[float] = []

    def add(self, v: float):
        self.values.append(v)

    def summary(self) -> dict | None:
        if not self.values:
            return None
        return {
            "count": len(self.values),
            "mean": statistics.mean(self.values),
            "max": max(self.values),
            "stdev": statistics.stdev(self.values) if len(self.values) >= 2 else 0.0,
        }

    def reset(self):
        self.values.clear()


async def main():
    nc = await nats.connect(NATS_URL)
    print(f"[window] NATS 接続: {NATS_URL}")
    print(f"[window] 窓サイズ: {WINDOW_SEC:.0f} 秒\n")

    accumulators: dict[str, WindowAccumulator] = defaultdict(WindowAccumulator)

    async def handler(msg):
        data = json.loads(msg.data)
        accumulators[data["sensor_id"]].add(data["value"])

    await nc.subscribe(SUBJECT, cb=handler)

    window_num = 0
    # 最初の窓境界まで待機して整列させる
    wait = next_boundary(WINDOW_SEC) - time.time()
    if wait > 0:
        await asyncio.sleep(wait)

    try:
        while True:
            window_start = time.monotonic()
            await asyncio.sleep(WINDOW_SEC)
            window_num += 1

            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"=== 窓 #{window_num}  {ts} ===")
            if not accumulators:
                print("  (データなし)")
            for key in sorted(accumulators):
                s = accumulators[key].summary()
                if s:
                    print(
                        f"  {key:<12}: 件数={s['count']:3d}  "
                        f"平均={s['mean']:.1f}  最大={s['max']:.1f}  σ={s['stdev']:.1f}"
                    )
                    accumulators[key].reset()
            print()
    except KeyboardInterrupt:
        print("[window] 終了")
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
