"""NATS Pub/Sub と Queue Subscribe デモ。
使い方:
  ターミナル1: python3 05_nats_pubsub.py subscriber
  ターミナル2: python3 05_nats_pubsub.py publisher
  --- または Queue Subscribe ---
  ターミナル1: python3 05_nats_pubsub.py worker 1
  ターミナル2: python3 05_nats_pubsub.py worker 2
  ターミナル3: python3 05_nats_pubsub.py producer 10
"""
import asyncio
import random
import sys
import time
import nats

NATS_URL = "nats://localhost:4222"


async def publisher():
    nc = await nats.connect(NATS_URL)
    print(f"[pub] 接続: {NATS_URL}")
    try:
        for _ in range(10):
            cpu = round(random.uniform(10, 90), 1)
            mem = round(random.uniform(40, 80), 1)
            await nc.publish("sensor.pi-master.cpu", str(cpu).encode())
            print(f"[pub] sensor.pi-master.cpu = {cpu}")
            await nc.publish("sensor.pi-master.memory", str(mem).encode())
            print(f"[pub] sensor.pi-master.memory = {mem}")
            await asyncio.sleep(1.0)
    finally:
        await nc.drain()


async def subscriber():
    nc = await nats.connect(NATS_URL)
    print(f"[sub] 接続: {NATS_URL}")

    async def handler(msg):
        print(f"[sub] {msg.subject}: {msg.data.decode()}")

    await nc.subscribe("sensor.>", cb=handler)
    print("[sub] 購読: sensor.>")
    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        await nc.drain()


async def worker(worker_id: int):
    nc = await nats.connect(NATS_URL)
    print(f"[worker{worker_id}] 接続: {NATS_URL}  待機中...")

    async def handler(msg):
        task_id = msg.data.decode()
        result = int(task_id) ** 2
        await asyncio.sleep(0.1)
        print(f"[worker{worker_id}] タスク{task_id} → 結果={result}")

    # queue group を指定すると同一グループ内で負荷分散
    await nc.subscribe("tasks", queue="workers", cb=handler)
    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        await nc.drain()


async def producer(n: int):
    nc = await nats.connect(NATS_URL)
    await asyncio.sleep(0.5)
    print(f"[producer] {n} 件のタスクを送信")
    for i in range(n):
        await nc.publish("tasks", str(i).encode())
        await asyncio.sleep(0.2)
    await nc.drain()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "publisher"
    arg = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    if mode == "publisher":
        asyncio.run(publisher())
    elif mode == "subscriber":
        asyncio.run(subscriber())
    elif mode == "worker":
        asyncio.run(worker(arg))
    elif mode == "producer":
        asyncio.run(producer(arg))
