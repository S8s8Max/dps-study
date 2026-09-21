"""Pool.map / imap で素数探索を並列化するデモ。"""
import time
from multiprocessing import Pool, cpu_count


def count_primes(n: int) -> int:
    """n 未満の素数の個数を返す"""
    count = 0
    for i in range(2, n):
        if all(i % d != 0 for d in range(2, int(i**0.5) + 1)):
            count += 1
    return count


LIMIT = 50_000
WORKERS = cpu_count()
CHUNKS = [LIMIT // WORKERS * (i + 1) for i in range(WORKERS)]


if __name__ == "__main__":
    print(f"=== 素数探索（0〜{LIMIT} を {WORKERS} 分割）===\n")

    # 逐次処理
    start = time.perf_counter()
    seq_results = [count_primes(n) for n in CHUNKS]
    seq_time = time.perf_counter() - start
    total = seq_results[-1]
    print(f"逐次処理:    {seq_time:.2f} 秒  （{total} 個の素数）")

    # Pool.map
    start = time.perf_counter()
    with Pool(WORKERS) as pool:
        map_results = pool.map(count_primes, CHUNKS)
    map_time = time.perf_counter() - start
    print(f"Pool.map:    {map_time:.2f} 秒  （{map_results[-1]} 個の素数）  "
          f"← {seq_time/map_time:.1f}x 速い")

    # Pool.imap（イテレータで返す）
    start = time.perf_counter()
    with Pool(WORKERS) as pool:
        imap_results = list(pool.imap(count_primes, CHUNKS))
    imap_time = time.perf_counter() - start
    print(f"Pool.imap:   {imap_time:.2f} 秒  （{imap_results[-1]} 個の素数）")
