"""ステートフルストリームプロセッサー：Redpanda から読んでタンブリング窓集計と異常検知。
使い方:
  # プロセッサー（先に起動）
  python3 05_stream_processor.py consumer
  # データ生成
  python3 05_stream_processor.py producer
"""
import asyncio
import json
import math
import random
import statistics
import sys
import time
from collections import defaultdict
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

BOOTSTRAP = "localhost:19092"
TOPIC = "sensor-events"
GROUP_ID = "stream-processors"
WINDOW_SEC = 5.0
ANOMALY_SIGMA = 2.5


# ──────────────────────────────────────────────
# プロデューサー側
# ──────────────────────────────────────────────

async def run_producer():
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode(),
        key_serializer=lambda k: k.encode() if k else None,
    )
    await producer.start()
    print(f"[producer] 接続: {BOOTSTRAP}  トピック: {TOPIC}")
    print("[producer] 送信中... (Ctrl-C で停止)\n")

    sensors = ["pi-cpu", "pi-memory", "pi-temp"]
    bases = {"pi-cpu": 40.0, "pi-memory": 60.0, "pi-temp": 50.0}
    seq = 0
    try:
        while True:
            for s in sensors:
                spike = random.random() < 0.02
                val = bases[s] + (random.gauss(0, 5) if not spike else random.uniform(80, 100))
                val = round(max(0.0, val), 1)
                await producer.send(TOPIC, key=s, value={
                    "sensor_id": s, "value": val, "ts": time.time(), "seq": seq,
                })
                if spike:
                    print(f"[producer] *** 異常値注入 *** {s}={val}")
            seq += 1
            if seq % 10 == 0:
                print(f"[producer] {seq * len(sensors)} 件送信")
            await asyncio.sleep(1.0)
    except KeyboardInterrupt:
        print(f"\n[producer] 終了: {seq * len(sensors)} 件送信")
    finally:
        await producer.stop()


# ──────────────────────────────────────────────
# コンシューマー（ステートフル処理）側
# ──────────────────────────────────────────────

class Accumulator:
    def __init__(self):
        self.values: list[float] = []

    def add(self, v: float):
        self.values.append(v)

    def flush(self) -> dict | None:
        if not self.values:
            return None
        result = {
            "count": len(self.values),
            "mean": statistics.mean(self.values),
            "max": max(self.values),
            "stdev": statistics.stdev(self.values) if len(self.values) >= 2 else 0.0,
            "latest": self.values[-1],
        }
        self.values.clear()
        return result


async def run_consumer():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode()),
        key_deserializer=lambda k: k.decode() if k else None,
    )
    await consumer.start()
    assigned = consumer.assignment()
    parts = sorted(tp.partition for tp in assigned) if assigned else []
    print(f"[processor] 接続: {BOOTSTRAP}  グループ: {GROUP_ID}")
    print(f"[processor] パーティション割り当て: {parts}")
    print(f"[processor] 窓サイズ: {WINDOW_SEC:.0f}s  異常閾値: {ANOMALY_SIGMA}σ\n")

    accumulators: dict[str, Accumulator] = defaultdict(Accumulator)
    window_num = 0
    total_received = 0

    # メッセージ受信タスク
    async def ingest():
        nonlocal total_received
        async for msg in consumer:
            v = msg.value
            accumulators[v["sensor_id"]].add(v["value"])
            total_received += 1

    # 窓集計タスク
    async def windowed_flush():
        nonlocal window_num
        # 最初の窓境界まで整列
        wait = math.ceil(time.time() / WINDOW_SEC) * WINDOW_SEC - time.time()
        if wait > 0:
            await asyncio.sleep(wait)
        while True:
            await asyncio.sleep(WINDOW_SEC)
            window_num += 1
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"=== 窓 #{window_num}  {ts}  累計={total_received}件 ===")
            if not accumulators:
                print("  (データなし)\n")
                continue
            for key in sorted(accumulators):
                s = accumulators[key].flush()
                if s is None:
                    continue
                is_anom = (
                    s["stdev"] > 0 and
                    abs(s["latest"] - s["mean"]) / s["stdev"] > ANOMALY_SIGMA
                )
                z = abs(s["latest"] - s["mean"]) / s["stdev"] if s["stdev"] > 0 else 0.0
                status = f"[*** 異常 z={z:.2f} ***]" if is_anom else "[正常]"
                print(
                    f"  {key:<12}: 件数={s['count']:3d}  "
                    f"平均={s['mean']:.1f}  最大={s['max']:.1f}  "
                    f"σ={s['stdev']:.1f}  {status}"
                )
            print()

    try:
        await asyncio.gather(ingest(), windowed_flush())
    except KeyboardInterrupt:
        print(f"\n[processor] 終了: 合計 {total_received} 件処理")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "consumer"
    if mode == "producer":
        asyncio.run(run_producer())
    else:
        asyncio.run(run_consumer())
