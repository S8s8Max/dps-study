# 03 スライディング窓と異常検知

## 学習目標

- スライディング窓で移動平均・移動標準偏差を計算できる
- 3σ ルールで異常値を検知できる
- `collections.deque` で効率的な窓バッファを実装できる

---

## 1. スライディング窓のデータ構造

### deque（両端キュー）を使う

```python
from collections import deque

# 最大 N 件を保持するバッファ
buffer = deque(maxlen=N)

buffer.append(10)
buffer.append(20)
buffer.append(30)
# maxlen=2 なら → deque([20, 30])  古いものが自動で削除される
```

`maxlen` を指定すると追加時に古い要素が自動で削除される。
O(1) で追加・削除できるため、窓バッファに最適。

### 時刻ベースの窓

件数ではなく時間で窓を定義する場合：

```python
from collections import deque
import time

class TimeWindow:
    def __init__(self, window_sec: float):
        self._window = window_sec
        self._buf = deque()   # (timestamp, value) のリスト

    def add(self, value: float):
        now = time.time()
        self._buf.append((now, value))
        # 古いものを削除
        cutoff = now - self._window
        while self._buf and self._buf[0][0] < cutoff:
            self._buf.popleft()

    def values(self):
        return [v for _, v in self._buf]
```

---

## 2. 移動平均と移動標準偏差

```python
import statistics

vals = window.values()
if len(vals) >= 2:
    mean = statistics.mean(vals)
    stdev = statistics.stdev(vals)
```

### Welford のオンライン算法（高速版）

都度 `statistics.mean()` を呼ぶと O(n)。
大量データの場合はオンライン更新で O(1) にできる。

```python
class OnlineStats:
    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self._M2 = 0.0   # 分散の分子

    def update(self, x: float):
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self._M2 += delta * (x - self.mean)

    @property
    def variance(self) -> float:
        return self._M2 / (self.n - 1) if self.n >= 2 else 0.0

    @property
    def stdev(self) -> float:
        return self.variance ** 0.5
```

ただし deque でデータを削除するときはリセットが必要。
Stage 3 では `statistics.mean/stdev` で十分（Pi 3B でも OK）。

---

## 3. 3σ ルールによる異常検知

```
正常範囲: mean - 3σ ≤ x ≤ mean + 3σ

正規分布を仮定すると:
  ±1σ 以内: 約 68.3%
  ±2σ 以内: 約 95.4%
  ±3σ 以内: 約 99.7%
  → ±3σ 外は約 0.3% = 異常とみなす
```

```python
def is_anomaly(value: float, mean: float, stdev: float,
               threshold: float = 3.0) -> bool:
    if stdev == 0:
        return False
    z_score = abs(value - mean) / stdev
    return z_score > threshold
```

---

## 4. 実装：スライディング窓異常検知器

`python/stage3/03_sliding_window.py` を実行する。

### 起動手順

```bash
# NATS が起動済みであること
python3 python/stage3/03_sliding_window.py
```

### 期待する出力

```
[sliding] NATS 接続: nats://localhost:4222
[sliding] 窓: 30 秒  更新: 2 秒ごと

2026-09-21 10:00:10
  pi-cpu    : 平均=39.2  σ=4.8  最新=41.3  [正常]
  pi-memory : 平均=60.1  σ=1.2  最新=60.5  [正常]
  pi-temp   : 平均=51.0  σ=1.5  最新=50.8  [正常]

2026-09-21 10:00:12
  pi-cpu    : 平均=39.4  σ=4.9  最新=82.7  [*** 異常 z=8.84 ***]
  pi-memory : 平均=60.2  σ=1.2  最新=61.0  [正常]
  pi-temp   : 平均=51.1  σ=1.5  最新=51.3  [正常]
```

---

## 5. 異常検知のチューニング

| パラメーター | 小さくすると | 大きくすると |
|------------|------------|------------|
| 窓サイズ（秒） | 最近のデータを重視。急な変化に敏感 | 長期トレンドを反映。ノイズに強い |
| 閾値（σ） | 誤検知（False Positive）が増える | 見逃し（False Negative）が増える |

実運用では ROC 曲線でチューニングするが、学習段階では σ=2〜3 が出発点としてよい。

---

## 6. まとめ

| 手法 | 実装コスト | 精度 | 向いているデータ |
|------|-----------|------|----------------|
| 3σ ルール | 低 | 正規分布を仮定 | CPU 使用率・温度など |
| IQR 法 | 低 | 外れ値に強い | スパイクが多いデータ |
| 移動平均との差分 | 中 | トレンド変化を検知 | 緩やかなドリフト |
| 機械学習（Isolation Forest） | 高 | 高精度 | 複合的な異常 |

次は **Redpanda**（Kafka 互換）を使って、ストリームデータを永続化する。
