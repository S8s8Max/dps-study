"""Ray アクター：シャーディングカウンターでステートフル分散処理。
使い方:
  python3 03_ray_actors.py
"""
import random
import time
import ray


# ── シャード（キーごとの状態を保持する Actor）──

@ray.remote
class StateShard:
    def __init__(self, shard_id: int):
        self.shard_id = shard_id
        self.state: dict[str, dict] = {}

    def add(self, key: str, value: float):
        if key not in self.state:
            self.state[key] = {"count": 0, "total": 0.0, "max": float("-inf")}
        s = self.state[key]
        s["count"] += 1
        s["total"] += value
        s["max"] = max(s["max"], value)

    def get_summary(self) -> dict:
        return {
            k: {
                "count": v["count"],
                "mean": v["total"] / v["count"],
                "max": v["max"],
            }
            for k, v in self.state.items()
        }

    def get_shard_id(self) -> int:
        return self.shard_id


# ── シャーディングマネージャー ──

class ShardedState:
    def __init__(self, n_shards: int = 4):
        self.n_shards = n_shards
        self.shards = [StateShard.remote(i) for i in range(n_shards)]

    def add(self, key: str, value: float):
        shard = self.shards[hash(key) % self.n_shards]
        shard.add.remote(key, value)

    def get_all_summaries(self) -> dict:
        refs = [s.get_summary.remote() for s in self.shards]
        results = {}
        for shard_result in ray.get(refs):
            results.update(shard_result)
        return results


# ── タスク：センサーデータを前処理してシャードへ投入 ──

@ray.remote
def preprocess(events: list[dict]) -> list[tuple[str, float]]:
    """外れ値をクリップして (key, value) のリストを返す。"""
    out = []
    for e in events:
        val = max(0.0, min(100.0, e["value"]))  # 0〜100 にクリップ
        out.append((e["sensor_id"], val))
    return out


def generate_events(n: int) -> list[dict]:
    sensors = ["pi-cpu", "pi-memory", "pi-temp", "pi-disk"]
    bases = {"pi-cpu": 40.0, "pi-memory": 60.0, "pi-temp": 50.0, "pi-disk": 30.0}
    events = []
    for _ in range(n):
        s = random.choice(sensors)
        spike = random.random() < 0.01
        val = bases[s] + (random.gauss(0, 5) if not spike else random.uniform(90, 120))
        events.append({"sensor_id": s, "value": val})
    return events


def main():
    N_EVENTS = 10_000
    BATCH_SIZE = 500
    N_SHARDS = 4

    ray.init(
        num_cpus=4,
        object_store_memory=128 * 1024 * 1024,
        ignore_reinit_error=True,
    )
    print(f"[ray] アクター起動: {N_SHARDS} シャード\n")

    state = ShardedState(n_shards=N_SHARDS)

    print(f"=== イベント投入: {N_EVENTS:,} 件（バッチサイズ={BATCH_SIZE}）===")
    t0 = time.perf_counter()

    events = generate_events(N_EVENTS)
    batches = [events[i:i + BATCH_SIZE] for i in range(0, N_EVENTS, BATCH_SIZE)]

    # バッチごとに前処理（Ray タスク）→ シャードへ投入
    preprocess_refs = [preprocess.remote(batch) for batch in batches]
    for batch_pairs in ray.get(preprocess_refs):
        for key, val in batch_pairs:
            state.add(key, val)

    elapsed = time.perf_counter() - t0
    print(f"  投入完了: {elapsed:.3f}s  スループット: {N_EVENTS/elapsed:.0f} 件/秒\n")

    print("=== 集計結果 ===")
    summaries = state.get_all_summaries()
    total_count = 0
    for key in sorted(summaries):
        s = summaries[key]
        shard_id = hash(key) % N_SHARDS
        total_count += s["count"]
        print(
            f"  シャード {shard_id}: {key:<12} → "
            f"件数={s['count']:5d}  平均={s['mean']:.1f}  最大={s['max']:.1f}"
        )
    print(f"\n  合計 {total_count:,} 件  スループット: {total_count/elapsed:.0f} 件/秒")

    ray.shutdown()
    print("\n[ray] 終了")


if __name__ == "__main__":
    main()
