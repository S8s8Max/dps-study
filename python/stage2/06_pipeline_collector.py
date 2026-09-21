"""パイプライン コレクター：NATS SUB で結果を集約してスループットを表示する。
使い方:
  python3 06_pipeline_collector.py
"""
import ast
import asyncio
import time
import nats

NATS_URL = "nats://localhost:4222"
RESULT_SUBJECT = "pipeline.results"


async def main():
    nc = await nats.connect(NATS_URL)
    print(f"[collector] 接続: NATS {NATS_URL}")
    print(f"[collector] 購読: {RESULT_SUBJECT}")

    count = 0
    start_time = None

    async def handler(msg):
        nonlocal count, start_time
        if count == 0:
            start_time = time.perf_counter()
        count += 1
        data = ast.literal_eval(msg.data.decode())
        print(
            f"[collector] #{count:<3} "
            f"worker={data['worker']}  "
            f"入力={data['input']:<5} "
            f"結果={data['result']:<7} "
            f"({data['elapsed']}s)"
        )

    await nc.subscribe(RESULT_SUBJECT, cb=handler)
    print("[collector] 待機中 (Ctrl-C で終了)\n")
    try:
        await asyncio.sleep(300)
    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.perf_counter() - start_time if start_time else 0
        throughput = count / elapsed if elapsed > 0 else 0
        print(f"\n[collector] === 完了 ===")
        print(f"[collector] 合計: {count} 件  スループット: {throughput:.1f} 件/秒")
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
