# 04 並列パターン

## 学習目標

- Map/Reduce パターンを multiprocessing と mpi4py で実装できる
- Scatter/Gather パターンで行列乗算を並列化できる
- パイプラインパターンで段階的な処理を並列化できる
- パターンに合った手法（multiprocessing vs mpi4py）を選択できる

---

## 1. 概念説明

### 3 大並列パターン

```
【Map/Reduce】
データを分割して同じ処理を並列実行し、結果を集約する。
最も基本的で使用頻度が高い。

  Input: [d1, d2, d3, d4]
         ↓   ↓   ↓   ↓   (Map: 各プロセスで処理)
       [r1, r2, r3, r4]
         ↓               (Reduce: 結果を集約)
        result

【Scatter/Gather（データ並列）】
大きなデータを分割して各プロセスに配布し、処理後に収集。
行列演算や画像処理に向く。

  [===大きな配列===]
    ↓↓↓↓ Scatter
  [a][b][c][d]   ← 各プロセスが担当部分を処理
    ↑↑↑↑ Gather
  [===結果配列===]

【パイプライン（タスク並列）】
処理を段階に分け、各段階を別プロセスが担当。
ストリーム処理に向く。

  入力 → [フィルター] → [変換] → [集計] → 出力
            rank=0        rank=1    rank=2
```

### パターンの選択基準

| パターン | 向く処理 | 実装手段 |
|---|---|---|
| Map/Reduce | 独立した計算の集約 | `Pool.map` + reduce |
| Scatter/Gather | 大配列の分割処理 | `mpi4py` の scatter/gather |
| パイプライン | 順序付き段階処理 | `Queue` または MPI Send/Recv |

---

## 2. Map/Reduce パターン

### モンテカルロ法で円周率を推定する

```
π を求めるアイデア：
  単位正方形の中にランダムに点を打つ
  円の中に入った点の割合 ≈ π/4

  ┌─────────────┐
  │  ●●●  ●    │
  │ ●●●●●●●   │  ← 正方形 (1×1)
  │  ●●○○●●●  │     ○ = 円の外
  │   ●●●○●   │
  └─────────────┘
```

```bash
python3 python/stage1/05_monte_carlo.py
```

期待する出力：

```
=== モンテカルロ法で π を推定 ===
サンプル数: 10,000,000（各プロセス: 2,500,000）

逐次処理:    4.21 秒  π ≈ 3.14159
Pool.map:    1.18 秒  π ≈ 3.14162  ← 3.6x 速い
```

### multiprocessing での実装ポイント

```python
from multiprocessing import Pool, cpu_count
import random

def estimate_pi(n_samples: int) -> float:
    inside = 0
    for _ in range(n_samples):
        x, y = random.random(), random.random()
        if x*x + y*y <= 1.0:
            inside += 1
    return inside / n_samples

if __name__ == "__main__":
    N = 10_000_000
    workers = cpu_count()
    chunk = N // workers

    # Map: 各プロセスが部分推定
    with Pool(workers) as pool:
        partial_pis = pool.map(estimate_pi, [chunk] * workers)

    # Reduce: 平均を取る
    pi = sum(partial_pis) / workers * 4
    print(f"π ≈ {pi:.5f}")
```

---

## 3. Scatter/Gather パターン（行列乗算）

### 行列の行ごとに並列処理する

```
A × B の計算（A は n×n 行列）

  A の行を各プロセスに Scatter
  ┌────────┐
  │ row 0  │ → rank=0 が処理
  │ row 1  │ → rank=1 が処理
  │ row 2  │ → rank=2 が処理
  │ row 3  │ → rank=3 が処理
  └────────┘
  結果を Gather で rank=0 に集約
```

```bash
mpirun -np 4 python3 python/stage1/05_mpi_matmul.py
```

期待する出力：

```
=== 行列乗算（MPI Scatter/Gather）===
行列サイズ: 400×400
逐次処理:    0.89 秒
MPI 並列:    0.26 秒  ← 3.4x 速い
結果の正確性: OK
```

---

## 4. パイプラインパターン

### 3 段階の処理をパイプライン化する

```
[ 生データ ] → [ フィルター ] → [ 変換 ] → [ 集計 ]
  (入力)         (rank=0)       (rank=1)   (rank=2)
```

```bash
mpirun -np 3 python3 python/stage1/05_mpi_pipeline.py
```

パイプライン処理のポイント：

```python
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

ITEMS = 20

if rank == 0:
    # ステージ1: フィルター（偶数のみ通す）
    for i in range(ITEMS):
        if i % 2 == 0:
            comm.send(i, dest=1)
    comm.send(None, dest=1)   # 終了シグナル

elif rank == 1:
    # ステージ2: 変換（2 乗）
    while True:
        item = comm.recv(source=0)
        if item is None:
            comm.send(None, dest=2)
            break
        comm.send(item * item, dest=2)

elif rank == 2:
    # ステージ3: 集計
    total = 0
    while True:
        item = comm.recv(source=1)
        if item is None:
            break
        total += item
    print(f"合計: {total}")
```

---

## 5. よくあるエラーと対処法

### Map/Reduce で結果の順序が崩れる

`pool.map` は順序を保証しますが、`pool.imap_unordered` は保証しません。

```python
# ✓ 順序を保証したいとき
results = pool.map(func, data)

# ✓ 順序不要で早く結果を得たいとき
results = list(pool.imap_unordered(func, data))
```

### MPI の Scatter でデータ数がプロセス数で割り切れない

```python
# ✓ 端数は rank=0 が受け持つ
n = len(data)
chunk = n // size
remainder = n % size

if rank == 0:
    my_data = data[:chunk + remainder]
else:
    start = chunk * rank + remainder
    my_data = data[start:start + chunk]
```

---

## 6. まとめと次のステップ

### 今回の学習内容

| パターン | 実装方法 | 向くユースケース |
|---|---|---|
| Map/Reduce | `Pool.map` + `sum` / `max` など | 独立した計算の並列化 |
| Scatter/Gather | `mpi4py` scatter/gather | 大配列の分割処理 |
| パイプライン | `Queue` または MPI Send/Recv | 段階的なストリーム処理 |

### 次のステップ

`05-benchmark.md` でこれまでの実装を系統的にベンチマークします。
プロセス数と速度向上の関係（アムダールの法則）を実測データで確認します。

```bash
cat docs/stage1/05-benchmark.md
```
