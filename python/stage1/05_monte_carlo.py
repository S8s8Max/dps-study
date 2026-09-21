"""モンテカルロ法で π を推定（逐次 vs multiprocessing 比較）"""
import random
import time
from multiprocessing import Pool, cpu_count


def estimate_pi(n_samples: int) -> float:
    inside = 0
    for _ in range(n_samples):
        x, y = random.random(), random.random()
        if x * x + y * y <= 1.0:
            inside += 1
    return inside / n_samples


N = 10_000_000
WORKERS = cpu_count()
CHUNK = N // WORKERS


if __name__ == "__main__":
    print(f"=== モンテカルロ法で π を推定 ===")
    print(f"サンプル数: {N:,}（各プロセス: {CHUNK:,}）\n")

    # 逐次処理
    start = time.perf_counter()
    seq_pi = estimate_pi(N) * 4
    seq_time = time.perf_counter() - start
    print(f"逐次処理:    {seq_time:.2f} 秒  π ≈ {seq_pi:.5f}")

    # Pool.map による並列処理
    start = time.perf_counter()
    with Pool(WORKERS) as pool:
        partial = pool.map(estimate_pi, [CHUNK] * WORKERS)
    mp_pi = sum(partial) / WORKERS * 4
    mp_time = time.perf_counter() - start
    print(f"Pool.map:    {mp_time:.2f} 秒  π ≈ {mp_pi:.5f}"
          f"  ← {seq_time/mp_time:.1f}x 速い")
