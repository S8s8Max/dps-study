"""MPI Scatter/Gather による行列乗算の並列化デモ。
実行: mpirun -np 4 python3 05_mpi_matmul.py
"""
import time
import numpy as np
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

N = 400  # 行列サイズ（N×N）
rows_per_proc = N // size

if rank == 0:
    A = np.random.rand(N, N)
    B = np.random.rand(N, N)
    A_chunks = [A[i * rows_per_proc:(i + 1) * rows_per_proc] for i in range(size)]
    print(f"=== 行列乗算（MPI Scatter/Gather）===")
    print(f"行列サイズ: {N}×{N}")

    # 逐次処理で時間計測
    start = time.perf_counter()
    expected = A @ B
    seq_time = time.perf_counter() - start
    print(f"逐次処理:    {seq_time:.2f} 秒")
else:
    A_chunks = None
    B = None

# B を全プロセスにブロードキャスト
B = comm.bcast(B, root=0)

# A の行チャンクを各プロセスに配布
my_rows = comm.scatter(A_chunks, root=0)

# 並列処理開始
t_start = MPI.Wtime()
my_result = my_rows @ B
t_end = MPI.Wtime()

# 結果を rank=0 に集約
all_results = comm.gather(my_result, root=0)

if rank == 0:
    result = np.vstack(all_results)
    mpi_time = t_end - t_start
    ratio = seq_time / mpi_time
    verdict = f"{ratio:.1f}x 速い" if ratio >= 1 else f"{1/ratio:.1f}x 遅い"
    print(f"MPI 並列:    {mpi_time:.2f} 秒  ← {verdict}")
    ok = np.allclose(result, expected)
    print(f"結果の正確性: {'OK' if ok else 'NG'}")

    if ratio < 1:
        print()
        print("※ 逐次のほうが速い場合があります。numpy の行列積は内部で")
        print("  BLAS がすでにマルチスレッド実行しているため、この規模では")
        print("  MPI の分割・通信コストのほうが大きくなります。")
        print("  行列サイズを大きくすると MPI が有利になります。")
