"""MPI Hello World: rank と size の基本確認。
実行: mpirun -np 4 python3 04_mpi_hello.py
"""
import socket
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
host = socket.gethostname()

role = "マスタープロセスです" if rank == 0 else "ワーカープロセスです"
print(f"[rank {rank}/{size}] {role}（{host}）")

# バリア：全プロセスがここに到達してから次へ進む
comm.Barrier()
if rank == 0:
    print(f"\n全 {size} プロセスが起動しました")
