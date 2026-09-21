"""Ray Hello World：ray.init / @ray.remote / ray.get の基本。
使い方:
  python3 01_ray_hello.py
"""
import os
import time
import ray


@ray.remote
def hello(worker_id: int) -> str:
    return f"Hello from worker {worker_id}  (PID={os.getpid()})"


@ray.remote
def slow_double(x: int, delay: float = 0.1) -> int:
    time.sleep(delay)
    return x * 2


def main():
    # Pi 3B 向けにオブジェクトストアを 128MB に制限
    ray.init(
        num_cpus=4,
        object_store_memory=128 * 1024 * 1024,
        ignore_reinit_error=True,
    )
    resources = ray.cluster_resources()
    print(f"[ray] 初期化完了")
    print(f"  CPUs: {resources.get('CPU', 0):.0f}  "
          f"メモリ: {resources.get('memory', 0) / 1024**3:.1f}GB\n")

    # ── 基本: 8 タスクを並列に投入 ──
    print("[ray] タスク実行: 8 個を並列")
    t0 = time.perf_counter()
    refs = [hello.remote(i) for i in range(8)]
    results = ray.get(refs)
    elapsed = time.perf_counter() - t0
    for r in results:
        print(f"  → {r}")
    print(f"  完了: {len(results)} タスク  {elapsed:.3f}s\n")

    # ── 直列 vs 並列 の時間比較 ──
    n = 16
    delay = 0.1

    print(f"[ray] 直列実行: {n} タスク（各 {delay}s）")
    t0 = time.perf_counter()
    serial = [ray.get(slow_double.remote(i, delay)) for i in range(n)]
    serial_time = time.perf_counter() - t0
    print(f"  直列: {serial_time:.2f}s  合計={sum(serial)}")

    print(f"[ray] 並列実行: {n} タスク（各 {delay}s）")
    t0 = time.perf_counter()
    refs = [slow_double.remote(i, delay) for i in range(n)]
    parallel = ray.get(refs)
    parallel_time = time.perf_counter() - t0
    print(f"  並列: {parallel_time:.2f}s  合計={sum(parallel)}")
    print(f"  スピードアップ: {serial_time / parallel_time:.1f}×\n")

    # ── ray.put でオブジェクトを共有 ──
    print("[ray] ray.put: 大きなリストを共有")
    big_list = list(range(100_000))
    ref = ray.put(big_list)

    @ray.remote
    def sum_slice(data_ref, start: int, end: int) -> int:
        data = ray.get(data_ref)
        return sum(data[start:end])

    chunk = len(big_list) // 4
    refs = [sum_slice.remote(ref, i * chunk, (i + 1) * chunk) for i in range(4)]
    total = sum(ray.get(refs))
    expected = sum(big_list)
    print(f"  合計: {total}  期待値: {expected}  {'OK' if total == expected else 'NG'}")

    ray.shutdown()
    print("\n[ray] 終了")


if __name__ == "__main__":
    main()
