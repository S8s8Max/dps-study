"""NATS Request/Reply デモ（計算サービス）。
使い方:
  ターミナル1: python3 05_nats_reqrep.py service
  ターミナル2: python3 05_nats_reqrep.py client
"""
import asyncio
import sys
import nats

NATS_URL = "nats://localhost:4222"
SUBJECT = "calc.double"


async def service():
    nc = await nats.connect(NATS_URL)
    print(f"[service] 待機中: {SUBJECT}")

    async def handler(msg):
        n = int(msg.data.decode())
        result = n * 2
        print(f"[service] 要求: {n}  → 応答: {result}")
        await msg.respond(str(result).encode())

    await nc.subscribe(SUBJECT, cb=handler)
    try:
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        await nc.drain()


async def client():
    nc = await nats.connect(NATS_URL)
    print(f"[client] 接続: {NATS_URL}")
    try:
        for n in [21, 7, 100, 3]:
            reply = await nc.request(SUBJECT, str(n).encode(), timeout=5.0)
            result = reply.data.decode()
            print(f"[client] 要求: {n}  → 応答: {result}")
            await asyncio.sleep(0.5)
    finally:
        await nc.drain()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "client"
    if mode == "service":
        asyncio.run(service())
    else:
        asyncio.run(client())
