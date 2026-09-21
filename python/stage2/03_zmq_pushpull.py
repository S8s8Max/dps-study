"""ZeroMQ PUSH/PULL ワーカープールデモ。
使い方:
  ターミナル1: python3 03_zmq_pushpull.py producer 20
  ターミナル2: python3 03_zmq_pushpull.py worker 1
  ターミナル3: python3 03_zmq_pushpull.py worker 2
  ターミナル4: python3 03_zmq_pushpull.py worker 3
  ターミナル5: python3 03_zmq_pushpull.py collector 20
"""
import sys
import time
import zmq

PRODUCER_PORT = 5557   # producer → workers
COLLECTOR_PORT = 5558  # workers → collector


def producer(n_tasks: int):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUSH)
    sock.bind(f"tcp://*:{PRODUCER_PORT}")
    print(f"[producer] ワーカーの接続を 1 秒待機...")
    time.sleep(1.0)
    print(f"[producer] {n_tasks} 件のタスクを送信")
    for i in range(n_tasks):
        sock.send_json({"id": i, "value": i})
        print(f"[producer] タスク{i} 送信")
        time.sleep(0.1)
    sock.close()
    ctx.term()


def worker(worker_id: int):
    ctx = zmq.Context()
    pull = ctx.socket(zmq.PULL)
    pull.connect(f"tcp://localhost:{PRODUCER_PORT}")
    push = ctx.socket(zmq.PUSH)
    push.connect(f"tcp://localhost:{COLLECTOR_PORT}")
    print(f"[worker{worker_id}] 起動: タスク待機中")
    try:
        while True:
            task = pull.recv_json()
            result = task["value"] ** 2
            time.sleep(0.05)  # 処理時間をシミュレート
            push.send_json({"id": task["id"], "result": result, "worker": worker_id})
            print(f"[worker{worker_id}] タスク{task['id']} → 結果={result}")
    except KeyboardInterrupt:
        print(f"[worker{worker_id}] 終了")
    finally:
        pull.close()
        push.close()
        ctx.term()


def collector(n_tasks: int):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PULL)
    sock.bind(f"tcp://*:{COLLECTOR_PORT}")
    print(f"[collector] {n_tasks} 件の結果を待機中")
    received = 0
    while received < n_tasks:
        data = sock.recv_json()
        print(f"[collector] タスク{data['id']} (worker{data['worker']}) 結果={data['result']}")
        received += 1
    print(f"[collector] 全 {n_tasks} 件受信完了")
    sock.close()
    ctx.term()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "worker"
    arg = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if mode == "producer":
        producer(arg)
    elif mode == "collector":
        collector(arg)
    else:
        worker(arg)
