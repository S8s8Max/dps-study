"""MPI Send/Recv によるパイプライン処理デモ。
実行: mpirun -np 3 python3 05_mpi_pipeline.py

処理フロー: フィルター(rank=0) → 変換(rank=1) → 集計(rank=2)
"""
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

if size != 3:
    if rank == 0:
        print("このスクリプトは -np 3 で実行してください")
    raise SystemExit(1)

ITEMS = 20

if rank == 0:
    # ステージ1: フィルター（偶数のみ通す）
    sent = 0
    for i in range(ITEMS):
        if i % 2 == 0:
            comm.send(i, dest=1)
            sent += 1
    comm.send(None, dest=1)
    print(f"[rank 0] フィルター: {ITEMS} 件中 {sent} 件を通過")

elif rank == 1:
    # ステージ2: 変換（2 乗）
    count = 0
    while True:
        item = comm.recv(source=0)
        if item is None:
            comm.send(None, dest=2)
            break
        comm.send(item * item, dest=2)
        count += 1
    print(f"[rank 1] 変換: {count} 件を 2 乗して転送")

elif rank == 2:
    # ステージ3: 集計
    total = 0
    count = 0
    while True:
        item = comm.recv(source=1)
        if item is None:
            break
        total += item
        count += 1
    print(f"[rank 2] 集計: {count} 件  合計={total}")
    # 0+4+16+36+64+100+144+196+256+324 = 1140
    expected = sum(i * i for i in range(0, ITEMS, 2))
    print(f"         期待値: {expected}  {'OK' if total == expected else 'NG'}")
