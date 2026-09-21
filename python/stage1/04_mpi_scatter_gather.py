"""Scatter/Gather で配列をプロセスに分散・集約するデモ。
実行: mpirun -np 4 python3 04_mpi_scatter_gather.py
"""
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# rank=0 がデータを用意して Scatter する
if rank == 0:
    chunk_size = 5
    data = list(range(chunk_size * size))  # [0, 1, ..., 19]
    chunks = [data[i * chunk_size:(i + 1) * chunk_size] for i in range(size)]
    print(f"[rank 0] 分散前データ: {data}")
else:
    chunks = None

# 各プロセスにチャンクを配布
my_chunk = comm.scatter(chunks, root=0)
my_sum = sum(my_chunk)
print(f"[rank {rank}] 受け取ったチャンク: {my_chunk}  合計: {my_sum}")

# 各プロセスの部分合計を rank=0 に集約
all_sums = comm.gather(my_sum, root=0)

if rank == 0:
    total = sum(all_sums)
    expected = sum(range(chunk_size * size))
    print(f"\n[rank 0] 全合計（Gather 後）: {total}  期待値: {expected}")
    assert total == expected, "合計が一致しません"
