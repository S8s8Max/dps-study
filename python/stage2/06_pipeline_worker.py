"""パイプライン ワーカー：ZeroMQ PULL でタスクを受け取り NATS PUB で結果を送る。
使い方:
  python3 06_pipeline_worker.py 1
  python3 06_pipeline_worker.py 2
"""
import asyncio
import sys
import time
import zmq
import nats

WORKER_PORT = 5560
NATS_URL = "nats://localhost:4222"
RESULT_SUBJECT = "pipeline.results"


async def main(worker_id: int):
    # ZeroMQ: プロデューサーからタスクを Pull
    ctx = zmq.Context()
    pull = ctx.socket(zmq.PULL)
    pull.connect(f"tcp://localhost:{WORKER_PORT}")

    # NATS: 結果をコレクターへ Publish
    nc = await nats.connect(NATS_URL)
    print(f"[worker{worker_id}] 起動: タスク待機中")

    # ZeroMQ をノンブロッキングで使うため asyncio と組み合わせる
    loop = asyncio.get_event_loop()
    try:
        while True:
            # タスクが来るまで非同期に待つ
            try:
                task = await loop.run_in_executor(None, lambda: pull.recv_json(flags=0))
            except zmq.Again:
                await asyncio.sleep(0.01)
                continue

            start = time.perf_counter()
            result = task["value"] ** 2
            await asyncio.sleep(0.05)  # 処理時間をシミュレート
            elapsed = time.perf_counter() - start

            payload = {
                "id": task["id"],
                "input": task["value"],
                "result": result,
                "worker": worker_id,
                "elapsed": round(elapsed, 3),
            }
            await nc.publish(RESULT_SUBJECT, str(payload).encode())
            print(f"[worker{worker_id}] タスク {task['id']:2d}  → 結果 {result:<5}  ({elapsed:.3f}s)")

    except KeyboardInterrupt:
        print(f"[worker{worker_id}] 終了")
    finally:
        pull.close()
        ctx.term()
        await nc.drain()


if __name__ == "__main__":
    wid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(main(wid))
