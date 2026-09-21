"""Stage 1 総合ベンチマーク。
プロセス数別の速度向上を計測してアムダールの法則を体感する。
"""
import random
import time
from multiprocessing import Pool, cpu_count


def count_primes(n: int) -> int:
    count = 0
    for i in range(2, n):
        if all(i % d != 0 for d in range(2, int(i**0.5) + 1)):
            count += 1
    return count


def estimate_pi(n_samples: int) -> float:
    inside = 0
    for _ in range(n_samples):
        x, y = random.random(), random.random()
        if x * x + y * y <= 1.0:
            inside += 1
    return inside / n_samples


def bench(label: str, func, data, workers_list):
    print(f"\n【{label}】")

    # 逐次
    start = time.perf_counter()
    seq = [func(d) for d in data]
    seq_time = time.perf_counter() - start
    print(f"  逐次処理 (1 プロセス):  {seq_time:.2f} 秒")

    for w in workers_list:
        start = time.perf_counter()
        with Pool(w) as pool:
            pool.map(func, data)
        t = time.perf_counter() - start
        print(f"  Pool ({w:2d} プロセス):      {t:.2f} 秒  ({seq_time/t:.1f}x)")


if __name__ == "__main__":
    cores = cpu_count()
    print(f"=== Stage 1 ベンチマーク（コア数: {cores}）===")

    # 素数探索
    N = 50_000
    bench(
        f"素数探索 (N={N})",
        count_primes,
        [N] * max(4, cores),
        [2, cores, min(cores * 2, 8)],
    )

    # モンテカルロ π
    M = 10_000_000
    bench(
        f"モンテカルロ π (N={M:,})",
        estimate_pi,
        [M // cores] * cores,
        [2, cores],
    )

    print("\n=== 速度向上サマリー（素数探索）===")
    print("processes,speedup")
    data = [N] * cores
    start = time.perf_counter()
    [count_primes(d) for d in data]
    seq_t = time.perf_counter() - start
    print(f"1,1.00")
    for w in [2, 3, cores, cores + 2, cores * 2]:
        if w > cores * 2:
            break
        start = time.perf_counter()
        with Pool(w) as pool:
            pool.map(count_primes, data)
        t = time.perf_counter() - start
        print(f"{w},{seq_t/t:.2f}")
