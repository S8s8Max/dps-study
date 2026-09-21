# 04 Dask 基礎と DataFrame

## 学習目標

- `dask.delayed` でカスタム並列ワークフローを記述できる
- Dask グラフを可視化して実行計画を確認できる
- `dask.dataframe` で pandas を自動で並列化できる
- `dask.distributed` でローカルクラスターを起動できる

---

## 1. Dask とは

```
pandas / NumPy: 単一マシン・メモリに収まるデータ用

Dask: 同じ API でメモリを超えた大規模データを処理

  pandas.DataFrame → dask.dataframe.DataFrame
  numpy.array      → dask.array.Array
  (カスタム)        → dask.delayed
```

### 実行モデル

Dask は **遅延評価（Lazy）** で動作する。

```python
result = df.groupby("sensor").mean()  # ← まだ計算しない
result.compute()                       # ← ここで初めて計算する
```

`.compute()` を呼ぶまで実際の計算は行わない。
その間に計算グラフ（DAG）を最適化する。

---

## 2. dask.delayed

任意の Python 関数を「遅延実行」に変換する。

```python
from dask import delayed

@delayed
def load(path: str):
    import pandas as pd
    return pd.read_csv(path)

@delayed
def process(df):
    return df[df["value"] > 50]

@delayed
def summarize(df):
    return df.groupby("sensor").mean()

# グラフを構築（まだ計算しない）
loaded = load("data.csv")
filtered = process(loaded)
result = summarize(filtered)

# 実行
output = result.compute()
```

### 並列化の例

```python
results = [process.remote(i) for i in range(8)]  # Ray 風

# Dask では:
results = [delayed(process)(i) for i in range(8)]
total = delayed(sum)(results)
total.compute()  # 8 タスクが並列実行される
```

---

## 3. dask.dataframe

pandas の DataFrame をパーティションに分割して並列処理する。

```
dask.dataframe:
  パーティション 0: 行 0〜9999
  パーティション 1: 行 10000〜19999
  パーティション 2: 行 20000〜29999
  ...
  → 各パーティションを並列に処理
```

```python
import dask.dataframe as dd

# CSV を読む（遅延）
df = dd.read_csv("data/*.csv")

# pandas と同じ API
result = (df
    .groupby("sensor_id")["value"]
    .mean()
    .compute()          # 実行
)
print(result)
```

### pandas との API 比較

| 操作 | pandas | Dask |
|------|--------|------|
| 読み込み | `pd.read_csv("f.csv")` | `dd.read_csv("*.csv")` |
| フィルター | `df[df.a > 0]` | `df[df.a > 0]`（同じ）|
| グループ集計 | `df.groupby("k").mean()` | `df.groupby("k").mean().compute()` |
| 行追加 | `pd.concat([a, b])` | `dd.concat([a, b])` |
| 実行 | 即時 | `.compute()` まで遅延 |

---

## 4. スケジューラーの選択

```python
# 同期（デバッグ用）
result.compute(scheduler="synchronous")

# スレッド（IO バウンドに向く）
result.compute(scheduler="threads")

# プロセス（CPU バウンドに向く、Pi 3B では注意）
result.compute(scheduler="processes")

# 分散クラスター（dask.distributed）
from dask.distributed import Client
client = Client("scheduler:8786")
result.compute()  # 自動でクラスターを使う
```

---

## 5. dask.distributed ローカルクラスター（Pi 3B 向け）

```python
from dask.distributed import Client, LocalCluster

cluster = LocalCluster(
    n_workers=2,
    threads_per_worker=2,
    memory_limit="256MB",   # ワーカーあたりのメモリ上限
)
client = Client(cluster)

# Dashboard: http://localhost:8787
print(client.dashboard_link)
```

---

## 6. Dask グラフの可視化

```python
result = df.groupby("sensor_id")["value"].mean()

# テキスト形式で確認
print(dict(result.__dask_graph__()))

# graphviz で画像出力（要 pip install graphviz）
result.visualize("graph.png")
```

---

## 7. 実装

```bash
# delayed の学習
python3 python/stage4/04_dask_delayed.py

# DataFrame の学習
python3 python/stage4/05_dask_dataframe.py
```

### 期待する出力（DataFrame）

```
[dask] CSV ファイル読み込み: data/*.csv
[dask] パーティション数: 4  合計行数: 10000

=== センサーごとの集計 ===
sensor_id
pi-cpu       39.8
pi-memory    60.2
pi-temp      51.1
Name: value, dtype: float64

=== 異常値（3σ以上）のフィルタリング ===
  23 件検出
  最大値: pi-cpu  91.3 (z=10.4)

[dask] compute 時間: 0.47s
```

---

## 8. まとめ

| API | 用途 |
|-----|------|
| `dask.delayed(fn)` | 任意関数の遅延化 |
| `dd.read_csv("*.csv")` | 複数 CSV を自動パーティション化 |
| `.compute()` | 遅延グラフを実際に実行 |
| `LocalCluster(...)` | ローカルに Dask クラスターを作る |
| `.visualize()` | 実行グラフを PNG で確認 |

次は Ray と Dask を組み合わせた **分散パイプライン** を構築する。
