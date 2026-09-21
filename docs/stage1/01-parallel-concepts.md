# 01 並列処理の基礎概念

## 学習目標

- 並行性（Concurrency）と並列性（Parallelism）の違いを説明できる
- プロセスとスレッドのメモリモデルの違いを理解する
- Python の GIL（Global Interpreter Lock）が何を引き起こすかを理解する
- CPU バウンドと I/O バウンドを見分け、適切な手法を選択できる

---

## 1. 概念説明

### 並行性 vs 並列性

よく混同される 2 つの概念です。

```
【並行性 Concurrency】
複数のタスクが「交互に」進む（1 コアでも実現できる）

  時間 →
  タスクA ████░░████░░████
  タスクB ░░████░░████░░██
  コア1  ─────────────────

【並列性 Parallelism】
複数のタスクが「同時に」進む（複数コアが必須）

  時間 →
  タスクA ████████████████
  コア1  ─────────────────
  タスクB ████████████████
  コア2  ─────────────────
```

Pi 3B は **4 コア** なので、最大 4 タスクを同時実行できます。

---

### プロセス vs スレッド

| | プロセス | スレッド |
|---|---|---|
| メモリ空間 | 独立（コピー） | 共有 |
| 起動コスト | 重い（数十 ms） | 軽い（数 µs） |
| 通信方法 | IPC（Queue、Pipe） | 共有メモリ（競合に注意）|
| クラッシュ影響 | 他プロセスに影響なし | 同プロセス全体がクラッシュ |
| Python での使用 | `multiprocessing` | `threading` |

```
【プロセスのメモリモデル】

  プロセス A         プロセス B
  ┌──────────┐      ┌──────────┐
  │ コード   │      │ コード   │
  │ ヒープ   │      │ ヒープ   │  ← 完全に独立
  │ スタック │      │ スタック │
  └──────────┘      └──────────┘

【スレッドのメモリモデル】

  プロセス A
  ┌────────────────────────┐
  │ コード                 │
  │ ヒープ（共有）         │  ← スレッドで共有
  │ ┌──────┐ ┌──────┐     │
  │ │スタック│ │スタック│   │  ← 各スレッドが持つ
  │ └──────┘ └──────┘     │
  └────────────────────────┘
```

---

### Python の GIL（Global Interpreter Lock）

Python（CPython）には **GIL** という制約があります。

> **GIL**: 同時に実行できる Python バイトコードは 1 スレッドだけ

```
【GIL の影響】

  スレッド1 ████░░░░████░░░░    ← GIL 待ちで止まる
  スレッド2 ░░░░████░░░░████    ← 実質シングルコア
  GIL      ┌──┐  ┌──┐  ┌──┐

  → CPU バウンド処理に threading を使っても速くならない！
```

**GIL を回避する方法：**

```
CPU バウンド（計算処理）
  → multiprocessing（プロセスは GIL を持たない）
  → mpi4py（MPI プロセスは独立）
  → NumPy（C 拡張内は GIL 解放）

I/O バウンド（ネットワーク・ファイル）
  → threading（GIL は I/O 待ち中に解放される）
  → asyncio（非同期 I/O）
```

---

### CPU バウンド vs I/O バウンド

| 種類 | 特徴 | 例 | 適切な手法 |
|---|---|---|---|
| **CPU バウンド** | CPU が常にフル稼働 | 計算・画像処理・暗号化 | multiprocessing |
| **I/O バウンド** | CPU が待っている時間が多い | ネットワーク・ファイル読書 | threading / asyncio |

**見分け方：**

```bash
# htop で CPU 使用率を確認
htop

# %CPU が高い → CPU バウンド
# %CPU が低いのに遅い → I/O バウンド
```

---

## 2. 事前確認

```bash
# Pi 3B のコア数確認（4 が返るはず）
python3 -c "import os; print(os.cpu_count())"
# 4

# CPU 情報の確認
lscpu | grep -E "^CPU\(s\)|^Core|Architecture"
# Architecture: aarch64
# CPU(s): 4
# Core(s) per socket: 4

# Python バージョン確認（3.11 以上推奨）
python3 --version
# Python 3.11.x
```

---

## 3. GIL の影響を実際に確認する

### 3.1 スレッドでは CPU バウンド処理が速くならないことを確認

```python
# python/stage1/01_gil_demo.py を実行
python3 python/stage1/01_gil_demo.py
```

期待する出力：

```
=== GIL デモ ===
逐次処理 (1スレッド): 2.34 秒
スレッド並列 (4スレッド): 2.31 秒  ← ほぼ変わらない（GIL の影響）
プロセス並列 (4プロセス): 0.68 秒  ← 約 3.4 倍速い（GIL なし）
```

### 3.2 htop でプロセスの挙動を観察する

別の SSH セッションで `htop` を開きながら、上記スクリプトを実行します。
- スレッド並列時: CPU 使用率が 1 コア分（約 100%）しか上がらない
- プロセス並列時: 4 コア全てが使用される（約 400%）

---

## 4. I/O バウンドでは threading が有効なことを確認する

```bash
# ネットワークリクエストを逐次 vs 並列で比較
python3 - <<'EOF'
import time
import threading
import urllib.request

urls = ["http://example.com"] * 8

def fetch(url):
    urllib.request.urlopen(url, timeout=5)

# 逐次
start = time.perf_counter()
for url in urls:
    fetch(url)
print(f"逐次: {time.perf_counter() - start:.2f} 秒")

# スレッド並列
start = time.perf_counter()
threads = [threading.Thread(target=fetch, args=(url,)) for url in urls]
[t.start() for t in threads]
[t.join() for t in threads]
print(f"スレッド並列: {time.perf_counter() - start:.2f} 秒")
EOF
```

I/O バウンドでは threading でも明確に速くなることを確認します。

---

## 5. よくある誤解と対処法

### 「スレッドを使えば並列になる」は誤り

```python
# ✗ CPU バウンド処理に threading を使っても速くならない
import threading
threads = [threading.Thread(target=cpu_heavy_func) for _ in range(4)]

# ✓ CPU バウンドには multiprocessing を使う
from multiprocessing import Pool
with Pool(4) as p:
    p.map(cpu_heavy_func, data)
```

### 「プロセスを増やせば増やすほど速くなる」は誤り

コア数（Pi 3B は 4）を超えてプロセスを増やしても速くなりません。
コンテキストスイッチのオーバーヘッドで逆に遅くなることもあります。

```python
# ✓ コア数に合わせる
from multiprocessing import Pool, cpu_count
with Pool(cpu_count()) as p:   # Pi 3B では 4
    ...
```

---

## 6. まとめと次のステップ

### 今回の学習内容

| 概念 | 要点 |
|---|---|
| 並行性 vs 並列性 | 並行 = 交互、並列 = 同時 |
| プロセス vs スレッド | プロセスは独立メモリ、スレッドは共有メモリ |
| GIL | Python スレッドは CPU バウンドで並列化できない |
| CPU/I/O バウンド | CPU → multiprocessing、I/O → threading/asyncio |

### 次のステップ

`02-multiprocessing.md` では、Pi 3B の 4 コアを `multiprocessing` モジュールで実際に使い、速度向上を数値で確認します。

```bash
# 次のドキュメントへ
cat docs/stage1/02-multiprocessing.md
```
