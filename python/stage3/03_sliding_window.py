"""スライディング窓：移動平均と 3σ 異常検知。
使い方:
  # ターミナル 1: データ生成（異常値を注入するには --spike オプション）
  python3 01_stateful_counter.py gen
  # ターミナル 2: スライディング窓
  python3 03_sliding_window.py
"""
import asyncio
import json
import statistics
import time
from collections import defaultdict, deque
import nats

NATS_URL = "nats://localhost:4222"
SUBJECT = "events.sensor.*"
WINDOW_SEC = 30.0     # 窓幅（秒）
UPDATE_INTERVAL = 2.0  # 表示更新間隔（秒）
ANOMALY_SIGMA = 2.5   # 異常判定の閾値（σ）


class TimeWindow:
    """時刻ベースのスライディング窓バッファ。"""

    def __init__(self, window_sec: float):
        self._window = window_sec
        self._buf: deque[tuple[float, float]] = deque()  # (timestamp, value)

    def add(self, value: float):
        now = time.monotonic()
        self._buf.append((now, value))
        cutoff = now - self._window
        while self._buf and self._buf[0][0] < cutoff:
            self._buf.popleft()

    def values(self) -> list[float]:
        cutoff = time.monotonic() - self._window
        return [v for t, v in self._buf if t >= cutoff]

    def __len__(self):
        return len(self._buf)


def detect_anomaly(value: float, vals: list[float], threshold: float) -> tuple[bool, float]:
    if len(vals) < 5:
        return False, 0.0
    mean = statistics.mean(vals)
    stdev = statistics.stdev(vals)
    if stdev == 0:
        return False, 0.0
    z = abs(value - mean) / stdev
    return z > threshold, z


async def main():
    nc = await nats.connect(NATS_URL)
    print(f"[sliding] NATS 接続: {NATS_URL}")
    print(f"[sliding] 窓: {WINDOW_SEC:.0f} 秒  更新: {UPDATE_INTERVAL:.0f} 秒ごと\n")

    windows: dict[str, TimeWindow] = defaultdict(lambda: TimeWindow(WINDOW_SEC))
    latest: dict[str, float] = {}

    async def handler(msg):
        data = json.loads(msg.data)
        key = data["sensor_id"]
        val = data["value"]
        windows[key].add(val)
        latest[key] = val

    await nc.subscribe(SUBJECT, cb=handler)

    try:
        while True:
            await asyncio.sleep(UPDATE_INTERVAL)
            if not windows:
                continue

            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(ts)
            for key in sorted(windows):
                vals = windows[key].values()
                if len(vals) < 2:
                    continue
                mean = statistics.mean(vals)
                stdev = statistics.stdev(vals)
                current = latest.get(key, 0.0)
                is_anom, z = detect_anomaly(current, vals, ANOMALY_SIGMA)
                status = f"[*** 異常 z={z:.2f} ***]" if is_anom else "[正常]"
                print(
                    f"  {key:<12}: 平均={mean:.1f}  σ={stdev:.1f}  "
                    f"最新={current:.1f}  {status}"
                )
            print()
    except KeyboardInterrupt:
        print("[sliding] 終了")
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
