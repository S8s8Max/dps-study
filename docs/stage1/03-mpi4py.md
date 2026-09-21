# 03 mpi4py

## 学習目標

- MPI（Message Passing Interface）の基本概念（rank、size、communicator）を理解する
- `mpirun` でマルチプロセスの Python プログラムを起動できる
- `Send` / `Recv` で点対点通信を実装できる
- `Bcast` / `Scatter` / `Gather` で集団通信を実装できる

---

## 1. 概念説明

### MPI とは

MPI は分散メモリ環境でプロセス間通信を行う業界標準インターフェースです。
HPC（高性能計算）の世界で広く使われており、後の Stage でノードを増やした場合も同じコードが動きます。

```
mpirun -np 4 python3 script.py
        ↓
  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
  │ rank=0    │  │ rank=1    │  │ rank=2    │  │ rank=3    │
  │ (マスター) │  │ (ワーカー) │  │ (ワーカー) │  │ (ワーカー) │
  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
        └───────────────┴───────────────┴───────────────┘
                        MPI_COMM_WORLD（全プロセスが参加）
```

### 主要な概念

| 概念 | 説明 |
|---|---|
| **rank** | プロセスの識別番号（0 から始まる） |
| **size** | 起動したプロセスの総数 |
| **communicator** | 通信するプロセスグループ（`MPI.COMM_WORLD` が全体） |

### 通信の種類

```
【点対点通信（Point-to-Point）】
  rank=0 ──Send(data)──► rank=1

【ブロードキャスト（Broadcast）】
  rank=0 ──Bcast(data)──► rank=0,1,2,3 全員

【スキャッター（Scatter）】
  rank=0 [a, b, c, d] ──Scatter──►
    rank=0:[a], rank=1:[b], rank=2:[c], rank=3:[d]

【ギャザー（Gather）】
  rank=0:[a], rank=1:[b], rank=2:[c], rank=3:[d]
    ──Gather──► rank=0 [a, b, c, d]
```

---

## 2. インストールと事前確認

### mpi4py のインストール

```bash
# OpenMPI と mpi4py をインストール
sudo apt-get install -y libopenmpi-dev openmpi-bin
pip install mpi4py

# インストール確認
mpirun --version
# Open MPI x.x.x

python3 -c "from mpi4py import MPI; print('OK')"
# OK
```

### 動作確認

```bash
# 4 プロセスで Hello World
mpirun -np 4 python3 -c "
from mpi4py import MPI
comm = MPI.COMM_WORLD
print(f'Hello from rank {comm.Get_rank()} of {comm.Get_size()}')
"
# Hello from rank 0 of 4
# Hello from rank 2 of 4
# Hello from rank 1 of 4
# Hello from rank 3 of 4
# （順番は不定）
```

---

## 3. Hello MPI を動かす

```bash
python3 python/stage1/04_mpi_hello.py   # ← 直接実行では 1 プロセス
mpirun -np 4 python3 python/stage1/04_mpi_hello.py
```

期待する出力：

```
[rank 0/4] マスタープロセスです（pi-master）
[rank 1/4] ワーカープロセスです（pi-master）
[rank 2/4] ワーカープロセスです（pi-master）
[rank 3/4] ワーカープロセスです（pi-master）
```

コードの骨格：

```python
from mpi4py import MPI
import socket

comm = MPI.COMM_WORLD
rank = comm.Get_rank()   # 自分の番号
size = comm.Get_size()   # 全プロセス数
host = socket.gethostname()

if rank == 0:
    print(f"[rank {rank}/{size}] マスタープロセスです（{host}）")
else:
    print(f"[rank {rank}/{size}] ワーカープロセスです（{host}）")
```

---

## 4. Send / Recv で点対点通信する

### rank=0 がデータを送り、rank=1 が受け取る

```python
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

if rank == 0:
    data = {"message": "こんにちは", "value": 42}
    comm.send(data, dest=1, tag=0)   # rank=1 に送る
    print(f"rank=0: 送信完了 {data}")

elif rank == 1:
    data = comm.recv(source=0, tag=0)  # rank=0 から受け取る
    print(f"rank=1: 受信完了 {data}")
```

```bash
mpirun -np 2 python3 -c "<上記コード>"
```

> **注意**: `send` / `recv` は **ブロッキング**です。
> `send` した側は相手が `recv` するまで、`recv` した側は相手が `send` するまで待機します。

---

## 5. Scatter / Gather でデータを分散・収集する

```bash
mpirun -np 4 python3 python/stage1/04_mpi_scatter_gather.py
```

期待する出力：

```
[rank 0] 受け取ったチャンク: [0, 1, 2, 3, 4]  合計: 10
[rank 1] 受け取ったチャンク: [5, 6, 7, 8, 9]  合計: 35
[rank 2] 受け取ったチャンク: [10, 11, 12, 13, 14]  合計: 60
[rank 3] 受け取ったチャンク: [15, 16, 17, 18, 19]  合計: 85
[rank 0] 全合計（Gather 後）: 190  期待値: 190
```

---

## 6. よくあるエラーと対処法

### `mpirun` でプロセス数がコア数を超えている

```
There are not enough slots available in the system to satisfy the 8 slots
that were requested by the application
```

→ `-np` の値をコア数以下にする（Pi 3B では最大 4）

```bash
# ✓ Pi 3B では最大 4
mpirun -np 4 python3 script.py

# コア数を超えたい場合（推奨しない）
mpirun --oversubscribe -np 8 python3 script.py
```

### デッドロック

`Send` と `Recv` の順序を間違えると両プロセスが永遠に待ち続けます。

```python
# ✗ デッドロック（両者が Send を先にしている）
if rank == 0:
    comm.send(data_0, dest=1)
    data_1 = comm.recv(source=1)

if rank == 1:
    comm.send(data_1, dest=0)  # ← 0 が recv を待っているのに send する
    data_0 = comm.recv(source=0)

# ✓ 片方が先に recv する
if rank == 0:
    comm.send(data_0, dest=1)
    data_1 = comm.recv(source=1)

if rank == 1:
    data_0 = comm.recv(source=0)  # ← 先に recv
    comm.send(data_1, dest=0)
```

---

## 7. まとめと次のステップ

### 今回の学習内容

| 概念・操作 | 習得内容 |
|---|---|
| rank / size | プロセスの識別と総数 |
| `send` / `recv` | 点対点ブロッキング通信 |
| `bcast` | マスターから全員へブロードキャスト |
| `scatter` / `gather` | データ分散・収集パターン |

### 次のステップ

`04-parallel-patterns.md` では multiprocessing と mpi4py を組み合わせた実践的な並列パターンを学びます。
Map/Reduce、パイプラインなど実際のデータ処理で使われる設計を実装します。

```bash
cat docs/stage1/04-parallel-patterns.md
```
