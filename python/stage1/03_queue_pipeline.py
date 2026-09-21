"""Queue を使ったプロデューサー・コンシューマーパターンのデモ。"""
import time
from multiprocessing import Process, Queue


def producer(queue: Queue, count: int) -> None:
    for i in range(count):
        queue.put(i)
    queue.put(None)  # 終了シグナル


def consumer(in_queue: Queue, out_queue: Queue) -> None:
    while True:
        item = in_queue.get()
        if item is None:
            break
        out_queue.put(item * item)  # 二乗して出力キューへ


if __name__ == "__main__":
    COUNT = 10_000
    in_q: Queue = Queue()
    out_q: Queue = Queue()

    start = time.perf_counter()

    p = Process(target=producer, args=(in_q, COUNT))
    c = Process(target=consumer, args=(in_q, out_q))

    p.start()
    c.start()
    p.join()
    c.join()

    results = []
    while not out_q.empty():
        results.append(out_q.get())

    elapsed = time.perf_counter() - start
    print(f"Queue パイプライン: {COUNT} アイテム処理完了")
    print(f"処理時間: {elapsed:.3f} 秒")
    print(f"最初の 5 件: {results[:5]}")
    print(f"最後の 5 件: {results[-5:]}")
