# 03 Ray アクター

## 学習目標

- Ray Actor でステートフルな分散オブジェクトを作れる
- Stage 3 の「キー付き状態管理」を Actor で置き換えられる
- 複数 Actor に処理を分散して並列実行できる
- Actor のライフサイクル（起動・呼び出し・終了）を管理できる

---

## 1. Ray タスク vs Ray アクター

```
Ray タスク（@ray.remote 関数）:
  - ステートレス：呼び出しごとに独立
  - 副作用なし
  - スケールしやすい（任意ノードで実行）

Ray アクター（@ray.remote クラス）:
  - ステートフル：内部状態を保持
  - メソッド呼び出しがシリアルに実行される
  - 状態の一貫性が保証される
```

### イメージ

```
通常の Python クラス:
  counter = Counter()
  counter.increment()      ← 同期・ローカル

Ray アクター:
  counter = Counter.remote()
  counter.increment.remote()  ← 非同期・リモートノードで実行
  ray.get(counter.get.remote())
```

---

## 2. Actor の定義と使い方

```python
@ray.remote
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self, n: int = 1):
        self.count += n

    def get(self) -> int:
        return self.count

# Actor インスタンスを作成（リモートに配置）
counter = Counter.remote()

# メソッドを非同期呼び出し
for _ in range(100):
    counter.increment.remote()

# 結果を取得
total = ray.get(counter.get.remote())
print(total)  # 100
```

---

## 3. アクターのライフサイクル

```python
# 名前付きアクター（他のプロセスからも参照できる）
counter = Counter.options(name="my-counter").remote()

# 別プロセスから参照
counter = ray.get_actor("my-counter")

# 明示的に終了
ray.kill(counter)
```

ハンドルを保持している限りアクターは生き続ける。
どこからも参照されなくなると GC でクリーンアップされる。

---

## 4. 複数 Actor でシャーディング

大量のキーを 1 つの Actor で処理するとボトルネックになる。
キーをハッシュで N 個の Actor に振り分ける（シャーディング）。

```python
NUM_SHARDS = 4

@ray.remote
class Shard:
    def __init__(self):
        self.state = {}

    def add(self, key: str, value: float):
        if key not in self.state:
            self.state[key] = {"count": 0, "total": 0.0}
        self.state[key]["count"] += 1
        self.state[key]["total"] += value

    def get_all(self) -> dict:
        return {k: v["total"] / v["count"] for k, v in self.state.items()}

# 4 つのシャードを起動
shards = [Shard.remote() for _ in range(NUM_SHARDS)]

def get_shard(key: str) -> Shard:
    return shards[hash(key) % NUM_SHARDS]

# 各イベントを対応するシャードへ
get_shard("pi-cpu").add.remote("pi-cpu", 42.5)
get_shard("pi-memory").add.remote("pi-memory", 61.0)
```

---

## 5. Stage 3 との比較

| 項目 | Stage 3（self実装） | Stage 4（Ray Actor） |
|------|-------------------|----------------------|
| 状態の場所 | メインプロセスのメモリ | リモートノードのメモリ |
| 耐障害性 | プロセスが落ちると失う | Actor を再起動して復旧可 |
| スケール | シングルプロセス | 複数ノードに分散 |
| コード | asyncio で自前管理 | `.remote()` で自動並列 |

---

## 6. 実装：シャーディングカウンター

```bash
python3 python/stage4/03_ray_actors.py
```

### 期待する出力

```
[ray] アクター起動: 4 シャード

=== イベント投入 ===
  10000 件投入中...
  投入完了: 1.23s

=== 集計結果 ===
  シャード 0: pi-cpu      → 件数=2512  平均=40.1
  シャード 1: pi-memory   → 件数=2489  平均=60.3
  シャード 2: pi-temp     → 件数=2501  平均=51.0
  シャード 3: pi-disk     → 件数=2498  平均=30.2

  合計 10000 件  スループット: 8123 件/秒
```

---

## 7. まとめ

| 概念 | 説明 |
|------|------|
| Actor | ステートフルな分散オブジェクト |
| `.remote()` | 非同期メソッド呼び出し（ObjectRef を返す） |
| 名前付き Actor | `Actor.options(name=...)` でグローバル参照 |
| シャーディング | `hash(key) % N` でキーを Actor に振り分け |

次は **Dask** で NumPy/pandas を自動で並列化する。
