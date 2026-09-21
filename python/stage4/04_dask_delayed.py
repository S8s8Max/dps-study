"""dask.delayed：カスタム並列ワークフローの構築と実行。
使い方:
  python3 04_dask_delayed.py
"""
import math
import multiprocessing
import random
import time
from dask import delayed, compute
import dask


# ── delayed 関数の定義 ──

@delayed
def generate_sample(seed: int, n: int) -> list[float]:
    rng = random.Random(seed)
    return [rng.gauss(50.0, 10.0) for _ in range(n)]


@delayed
def filter_outliers(values: list[float], z_thresh: float = 3.0) -> list[float]:
    if len(values) < 2:
        return values
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    stdev = math.sqrt(variance)
    if stdev == 0:
        return values
    return [v for v in values if abs(v - mean) / stdev <= z_thresh]


@delayed
def compute_stats(values: list[float]) -> dict:
    if not values:
        return {}
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1) if n > 1 else 0.0
    return {
        "count": n,
        "mean": round(mean, 3),
        "stdev": round(math.sqrt(variance), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


@delayed
def merge_stats(stats_list: list[dict]) -> dict:
    total_count = sum(s.get("count", 0) for s in stats_list)
    total_mean = sum(s.get("mean", 0) * s.get("count", 0) for s in stats_list)
    return {
        "partitions": len(stats_list),
        "total_count": total_count,
        "overall_mean": round(total_mean / total_count, 3) if total_count else 0,
    }


def build_pipeline(n_partitions: int = 8, n_per_partition: int = 10_000):
    """遅延実行グラフを構築して返す（まだ計算しない）。"""
    stats_list = []
    for i in range(n_partitions):
        samples = generate_sample(seed=i, n=n_per_partition)
        clean = filter_outliers(samples)
        stats = compute_stats(clean)
        stats_list.append(stats)
    return merge_stats(stats_list)


def main():
    N_PARTITIONS = 8
    N_PER_PARTITION = 10_000

    print("=== dask.delayed ワークフロー ===\n")

    # ── グラフ構築（計算はしない）──
    print(f"[dask] グラフ構築: {N_PARTITIONS} パーティション × {N_PER_PARTITION:,} サンプル")
    pipeline = build_pipeline(N_PARTITIONS, N_PER_PARTITION)
    print(f"  グラフノード数: {len(dict(pipeline.__dask_graph__()))}")

    # ── シングルスレッドで実行（デバッグ比較用）──
    print("\n[dask] 実行: synchronous スケジューラー")
    t0 = time.perf_counter()
    result_sync = pipeline.compute(scheduler="synchronous")
    t_sync = time.perf_counter() - t0
    print(f"  結果: {result_sync}")
    print(f"  時間: {t_sync:.3f}s")

    # ── スレッドプールで並列実行 ──
    print("\n[dask] 実行: threaded スケジューラー")
    t0 = time.perf_counter()
    result_thread = pipeline.compute(scheduler="threads")
    t_thread = time.perf_counter() - t0
    print(f"  結果: {result_thread}")
    print(f"  時間: {t_thread:.3f}s  スピードアップ: {t_sync/t_thread:.1f}×")

    # ── プロセスプールで並列実行 ──
    n_cpu = multiprocessing.cpu_count()
    print(f"\n[dask] 実行: processes スケジューラー ({n_cpu} CPUs)")
    t0 = time.perf_counter()
    result_proc = pipeline.compute(scheduler="processes")
    t_proc = time.perf_counter() - t0
    print(f"  結果: {result_proc}")
    print(f"  時間: {t_proc:.3f}s  スピードアップ: {t_sync/t_proc:.1f}×")

    # ── 複数のグラフを同時に compute ──
    print("\n[dask] compute(): 複数パイプラインを同時実行")
    pipelines = [build_pipeline(4, 5_000) for _ in range(3)]
    t0 = time.perf_counter()
    results = compute(*pipelines, scheduler="threads")
    t_multi = time.perf_counter() - t0
    for i, r in enumerate(results):
        print(f"  パイプライン {i}: {r}")
    print(f"  時間: {t_multi:.3f}s")

    print("\n[dask] 完了")


if __name__ == "__main__":
    main()
