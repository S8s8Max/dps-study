"""GIL の影響を確認するデモ。
CPU バウンド処理に threading を使っても速くならず、
multiprocessing なら速くなることを示す。
"""
import time
import threading
from multiprocessing import Pool, cpu_count


def cpu_work(n: int) -> int:
    """CPU バウンドな処理（素数カウント）"""
    count = 0
    for i in range(2, n):
        if all(i % d != 0 for d in range(2, int(i**0.5) + 1)):
            count += 1
    return count


N = 50_000
WORKERS = cpu_count()  # Pi 3B では 4
CHUNKS = [N] * WORKERS


def run_sequential():
    return [cpu_work(n) for n in CHUNKS]


def run_threaded():
    results = [None] * WORKERS

    def worker(idx, n):
        results[idx] = cpu_work(n)

    threads = [threading.Thread(target=worker, args=(i, n)) for i, n in enumerate(CHUNKS)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return results


def run_multiprocessing():
    with Pool(WORKERS) as p:
        return p.map(cpu_work, CHUNKS)


if __name__ == "__main__":
    print(f"=== GIL デモ (コア数: {WORKERS}) ===\n")

    start = time.perf_counter()
    run_sequential()
    seq_time = time.perf_counter() - start
    print(f"逐次処理        (1プロセス):  {seq_time:.2f} 秒")

    start = time.perf_counter()
    run_threaded()
    thr_time = time.perf_counter() - start
    print(f"スレッド並列    ({WORKERS}スレッド): {thr_time:.2f} 秒  ← GIL により速くならない")

    start = time.perf_counter()
    run_multiprocessing()
    mp_time = time.perf_counter() - start
    print(f"プロセス並列    ({WORKERS}プロセス): {mp_time:.2f} 秒  ← {seq_time/mp_time:.1f}x 速い")
