"""Queue を使ったプロデューサー・コンシューマーパターンのデモ。

順序が重要:
  子プロセスが Queue に入れたデータを親が引き取る前に join() すると
  デッドロックする。詳細は docs/stage1/04-parallel-patterns.md を参照。
"""
import time
from multiprocessing import Process, Queue

DONE = None  # 終了シグナル（None はプロセス間でも同一オブジェクトのまま届く）


def producer(queue: Queue, count: int) -> None:
    for i in range(count):
        queue.put(i)
    queue.put(DONE)


def consumer(in_queue: Queue, out_queue: Queue) -> None:
    while True:
        item = in_queue.get()
        if item is DONE:
            break
        out_queue.put(item * item)
    out_queue.put(DONE)


if __name__ == "__main__":
    COUNT = 10_000
    in_q: Queue = Queue()
    out_q: Queue = Queue()

    start = time.perf_counter()

    p = Process(target=producer, args=(in_q, COUNT))
    c = Process(target=consumer, args=(in_q, out_q))
    p.start()
    c.start()

    # join() より先に受け取りきる。逆順にするとデッドロックする
    results = []
    while True:
        item = out_q.get()
        if item is DONE:
            break
        results.append(item)

    p.join()
    c.join()

    elapsed = time.perf_counter() - start
    print(f"Queue パイプライン: {COUNT} アイテム処理完了")
    print(f"受け取った結果: {len(results)} 件")
    print(f"処理時間: {elapsed:.3f} 秒")
    print(f"最初の 5 件: {results[:5]}")
    print(f"最後の 5 件: {results[-5:]}")
