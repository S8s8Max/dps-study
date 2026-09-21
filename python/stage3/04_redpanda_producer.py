"""Redpanda プロデューサー：センサーデータをキー付きで送信する。
使い方:
  python3 04_redpanda_producer.py
"""
import asyncio
import json
import random
import time
from aiokafka import AIOKafkaProducer

BOOTSTRAP = "localhost:19092"
TOPIC = "sensor-events"
INTERVAL = 1.0


async def main():
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode(),
        key_serializer=lambda k: k.encode() if k else None,
    )
    await producer.start()
    print(f"[producer] Redpanda 接続: {BOOTSTRAP}")
    print(f"[producer] トピック: {TOPIC}")
    print("[producer] 送信中... (Ctrl-C で停止)\n")

    sensors = ["pi-cpu", "pi-memory", "pi-temp"]
    bases = {"pi-cpu": 40.0, "pi-memory": 60.0, "pi-temp": 50.0}
    seq = 0
    try:
        while True:
            ts = time.time()
            for sensor in sensors:
                # まれに異常値を注入（学習用）
                spike = random.random() < 0.02
                val = bases[sensor] + (random.gauss(0, 5) if not spike else random.uniform(80, 100))
                val = round(max(0.0, val), 1)
                record = {
                    "sensor_id": sensor,
                    "value": val,
                    "timestamp": ts,
                    "seq": seq,
                }
                # key= を指定することで同じセンサーは同じパーティションへ
                meta = await producer.send(TOPIC, key=sensor, value=record)
                if spike:
                    print(f"[producer] *** 異常値注入 *** {sensor}={val}  "
                          f"partition={meta.partition}")
            seq += 1
            if seq % 10 == 0:
                print(f"[producer] #{seq * len(sensors)} 件送信")
            await asyncio.sleep(INTERVAL)
    except KeyboardInterrupt:
        print(f"\n[producer] 終了: {seq * len(sensors)} 件送信")
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
