"""パイプライン プロデューサー：ZeroMQ PUSH でタスクを投入する。
使い方:
  python3 06_pipeline_producer.py 30
"""
import sys
import time
import zmq

WORKER_PORT = 5560


def main(n_tasks: int):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUSH)
    sock.bind(f"tcp://*:{WORKER_PORT}")
    print(f"[producer] ワーカーの接続を 1 秒待機...")
    time.sleep(1.0)
    print(f"[producer] {n_tasks} 件のタスクを送信")
    for i in range(1, n_tasks + 1):
        sock.send_json({"id": i, "value": i})
    print(f"[producer] {n_tasks} 件送信完了")
    time.sleep(0.5)
    sock.close()
    ctx.term()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    main(n)
