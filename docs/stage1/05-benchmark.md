# 05 ベンチマークと性能評価

## 学習目標

- `time.perf_counter()` と `timeit` で正確な実行時間を計測できる
- プロセス数と速度向上の関係（アムダールの法則）を理解する
- Pi 3B で実測した数値をもとに、並列化の限界を把握できる
- ボトルネックを特定し、改善の方針を立てられる

---

## 1. 概念説明

### アムダールの法則

並列化で得られる速度向上には理論的な上限があります。

```
速度向上 = 1 / (S + (1-S)/N)

  S: 逐次処理の割合（並列化できない部分）
  N: プロセス数

例: 並列化できる部分が 80%（S=0.2）の場合
  N=1:   1.0x
  N=2:   1.67x
  N=4:   2.5x
  N=8:   3.08x
  N=∞:  5.0x  ← 上限（逐次部分で頭打ち）
```

```
速度向上
5x  ─────────────────────── 理論上限（S=0.2）
4x           ···
3x      ···
2x   ···
1x  ·
    1   2   3   4   ∞   プロセス数
```

Pi 3B は 4 コアなので、N=4 が実質的な上限です。

### 計測の注意点

| 注意点 | 理由 |
|---|---|
| 複数回計測して平均・最小を使う | OS のスケジューリングや GC の影響 |
| ウォームアップを入れる | JIT コンパイル・キャッシュの影響 |
| `time.time()` より `perf_counter()` | `time.time()` は OS 時計で精度が低い |
| 逐次と並列を同じ環境で比較する | 他のプロセスが動いていると数値が変わる |

---

## 2. 事前確認

```bash
# numpy のインストール（行列計算に使用）
pip install numpy

# 現在の CPU 負荷確認（他のプロセスが邪魔しないか）
htop
# CPU 使用率がほぼ 0% であることを確認してから計測する

# メモリ確認（Pi 3B は 1GB）
free -h
```

---

## 3. ベンチマークを実行する

### 3.1 総合ベンチマーク

```bash
python3 python/stage1/06_benchmark.py
```

期待する出力（Pi 3B での実測値は環境により異なります）：

```
=== Stage 1 ベンチマーク（Pi 3B / 4 コア）===

【素数探索 (N=50,000)】
  逐次処理 (1 プロセス):  3.21 秒
  Pool (2 プロセス):      1.74 秒  (1.8x)
  Pool (4 プロセス):      0.89 秒  (3.6x)  ← ベスト
  Pool (8 プロセス):      0.95 秒  (3.4x)  ← 4 以上は遅くなる

【モンテカルロ π (N=10,000,000)】
  逐次処理 (1 プロセス):  4.21 秒
  Pool (2 プロセス):      2.19 秒  (1.9x)
  Pool (4 プロセス):      1.12 秒  (3.8x)  ← ベスト

【行列乗算 (400×400)】
  逐次処理 (numpy):       0.89 秒
  Pool (4 プロセス):      0.26 秒  (3.4x)
```

### 3.2 プロセス数と速度向上の関係を確認する

```bash
python3 python/stage1/06_benchmark.py --plot
```

グラフが表示できない環境では CSV で出力されます：

```
processes,speedup
1,1.00
2,1.84
3,2.61
4,3.52
6,3.41
8,3.20
```

---

## 4. ボトルネックの特定

### プロセス起動コストを測る

プロセスの起動自体にコストがかかります。小さなタスクでは起動コストが処理時間を上回ることがあります。

```bash
python3 - <<'EOF'
import time
from multiprocessing import Pool, cpu_count

def trivial(x):
    return x * 2

N = 1000

# 小さなタスクの場合
start = time.perf_counter()
results = [trivial(i) for i in range(N)]
print(f"逐次 (N={N}): {time.perf_counter()-start:.4f} 秒")

start = time.perf_counter()
with Pool(cpu_count()) as pool:
    results = pool.map(trivial, range(N))
print(f"並列 (N={N}): {time.perf_counter()-start:.4f} 秒  ← 逐次より遅い！")

# 十分大きなタスクの場合
N = 1_000_000
start = time.perf_counter()
results = [trivial(i) for i in range(N)]
print(f"逐次 (N={N}): {time.perf_counter()-start:.4f} 秒")

start = time.perf_counter()
with Pool(cpu_count()) as pool:
    results = pool.map(trivial, range(N))
print(f"並列 (N={N}): {time.perf_counter()-start:.4f} 秒")
EOF
```

**教訓**: 処理が軽すぎると並列化のオーバーヘッドが勝ります。
`chunksize` パラメータで 1 回あたりの処理量を増やすと改善します。

```python
# ✓ chunksize で効率改善
pool.map(func, data, chunksize=1000)
```

### Grafana でリソース使用状況を確認する

Stage 0 で構築したモニタリングスタックを使って、処理中の CPU・メモリ使用状況を確認します。

```bash
# SSH ポートフォワードを張る
ssh -N -L 3000:localhost:3000 pi-master &

# ブラウザで Grafana にアクセス
# http://localhost:3000 → Node Exporter Full
```

ベンチマーク実行中に Grafana を見ると：
- 逐次処理中: 1 コアが 100%、他は低い
- `Pool(4)` 実行中: 4 コア全てが 100% に近い

---

## 5. Stage 1 完了チェックリスト

- [ ] `os.cpu_count()` が `4` を返すことを確認した
- [ ] `01_gil_demo.py` でスレッド並列が速くならないことを実測した
- [ ] `02_pool_map.py` で逐次より速い結果を確認した
- [ ] `mpirun -np 4 python3 04_mpi_hello.py` が 4 プロセスで動いた
- [ ] `04_mpi_scatter_gather.py` で合計値が正しく集約された
- [ ] `06_benchmark.py` でプロセス数別の速度向上を計測した
- [ ] アムダールの法則の上限を実測値で体感した

---

## 6. まとめと次のステップ

### Stage 1 で習得したこと

| 項目 | 習得内容 |
|---|---|
| 並列処理の概念 | 並行性 vs 並列性、GIL の影響 |
| multiprocessing | Pool.map、Queue、プロセス間通信 |
| mpi4py | rank/size、Send/Recv、Scatter/Gather |
| 並列パターン | Map/Reduce、データ並列、パイプライン |
| ベンチマーク | アムダールの法則、プロセス起動コスト |

### Stage 2 へ

Stage 2 では ZeroMQ と MQTT/NATS を使った**メッセージングとパイプライン**を学びます。
Stage 1 で学んだ「プロセス間通信」の概念が、ネットワーク越しの通信に拡張されます。

```
Stage 1: プロセス間通信（同一ノード内）
  ↓
Stage 2: ネットワーク通信（ノード間）
  Queue（multiprocessing）→ ZeroMQ（ネットワーク対応）
  Send/Recv（MPI）→ Pub/Sub（MQTT/NATS）
```

```bash
# 次のドキュメントへ
cat docs/stage2-study-guide.md
```
