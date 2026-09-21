"""Ray タスク：モンテカルロ π 推定で multiprocessing と Ray を比較。
使い方:
  python3 02_ray_tasks.py
"""
import math
import multiprocessing
import random
import time
import ray


# ── モンテカルロ π 推定 ──

def monte_carlo_serial(n_total: int) -> float:
    inside = sum(
        1 for _ in range(n_total)
        if random.random() ** 2 + random.random() ** 2 <= 1.0
    )
    return 4.0 * inside / n_total


def _worker_chunk(n: int) -> int:
    rng = random.Random()
    return sum(
        1 for _ in range(n)
        if rng.random() ** 2 + rng.random() ** 2 <= 1.0
    )


def monte_carlo_multiprocessing(n_total: int, n_workers: int) -> float:
    chunk = n_total // n_workers
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_worker_chunk, [chunk] * n_workers)
    return 4.0 * sum(results) / (chunk * n_workers)


@ray.remote
def ray_chunk(n: int) -> int:
    rng = random.Random()
    return sum(
        1 for _ in range(n)
        if rng.random() ** 2 + rng.random() ** 2 <= 1.0
    )


def monte_carlo_ray(n_total: int, n_tasks: int) -> float:
    chunk = n_total // n_tasks
    refs = [ray_chunk.remote(chunk) for _ in range(n_tasks)]
    total_inside = sum(ray.get(refs))
    return 4.0 * total_inside / (chunk * n_tasks)


def monte_carlo_ray_wait(n_total: int, n_tasks: int) -> float:
    """ray.wait() でバックプレッシャーを制御しながら結果を取得する。"""
    chunk = n_total // n_tasks
    refs = [ray_chunk.remote(chunk) for _ in range(n_tasks)]
    total_inside = 0
    pending = list(refs)
    while pending:
        done, pending = ray.wait(pending, num_returns=min(4, len(pending)))
        total_inside += sum(ray.get(done))
    return 4.0 * total_inside / (chunk * n_tasks)


def benchmark(label: str, fn, *args) -> tuple[float, float]:
    t0 = time.perf_counter()
    pi = fn(*args)
    elapsed = time.perf_counter() - t0
    print(f"  {label:<28}: π≈{pi:.5f}  {elapsed:.3f}s")
    return pi, elapsed


def main():
    N = 4_000_000
    WORKERS = 4

    ray.init(
        num_cpus=WORKERS,
        object_store_memory=128 * 1024 * 1024,
        ignore_reinit_error=True,
    )
    print("[ray] 初期化完了\n")
    print(f"=== モンテカルロ π 推定  (N={N:,}) ===")

    _, t_serial = benchmark("直列", monte_carlo_serial, N)
    _, t_mp = benchmark(f"multiprocessing({WORKERS})", monte_carlo_multiprocessing, N, WORKERS)
    _, t_ray = benchmark(f"Ray タスク({WORKERS})", monte_carlo_ray, N, WORKERS)
    _, t_wait = benchmark(f"Ray wait({WORKERS})", monte_carlo_ray_wait, N, WORKERS)

    print()
    print(f"  multiprocessing スピードアップ: {t_serial/t_mp:.1f}×")
    print(f"  Ray スピードアップ             : {t_serial/t_ray:.1f}×")
    print(f"  Ray wait スピードアップ        : {t_serial/t_wait:.1f}×")
    print()
    print("  [備考] Ray は初回起動コストがある。2回目以降は multiprocessing と同等。")

    # ── ray.wait を使ったバックプレッシャーの実演 ──
    print("\n=== ray.wait バックプレッシャー制御 ===")
    print("  100 タスクを投入し、完了したものを 10 件ずつ取得する")
    refs = [ray_chunk.remote(10_000) for _ in range(100)]
    batch_results = []
    pending = list(refs)
    while pending:
        done, pending = ray.wait(pending, num_returns=min(10, len(pending)))
        batch_results.extend(ray.get(done))
        if len(batch_results) % 30 == 0:
            print(f"  {len(batch_results)} 件完了...")
    print(f"  完了: {len(batch_results)} 件")

    ray.shutdown()
    print("\n[ray] 終了")


if __name__ == "__main__":
    main()
