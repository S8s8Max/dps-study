"""ZeroMQ PUB/SUB センサーデータ配信デモ。
使い方:
  ターミナル1: python3 02_zmq_pubsub.py publisher
  ターミナル2: python3 02_zmq_pubsub.py subscriber cpu
  ターミナル3: python3 02_zmq_pubsub.py subscriber temperature
"""
import random
import sys
import time
import zmq

PORT = 5556


def publisher():
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUB)
    sock.bind(f"tcp://*:{PORT}")
    print(f"[pub] 起動中... port={PORT}")
    time.sleep(0.5)  # サブスクライバーの接続を待つ（slow joiner 対策）
    try:
        while True:
            cpu = round(random.uniform(10, 90), 1)
            temp = round(random.uniform(45, 70), 1)
            sock.send_string(f"cpu {cpu}")
            print(f"[pub] cpu {cpu}%")
            time.sleep(0.3)
            sock.send_string(f"temperature {temp}")
            print(f"[pub] temperature {temp}°C")
            time.sleep(0.7)
    except KeyboardInterrupt:
        print("[pub] 終了")
    finally:
        sock.close()
        ctx.term()


def subscriber(topic: str):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(f"tcp://localhost:{PORT}")
    sock.setsockopt_string(zmq.SUBSCRIBE, topic)
    print(f"[sub:{topic}] 購読開始... localhost:{PORT}")
    try:
        while True:
            msg = sock.recv_string()
            _, value = msg.split(" ", 1)
            print(f"[sub:{topic}] {value}")
    except KeyboardInterrupt:
        print(f"[sub:{topic}] 終了")
    finally:
        sock.close()
        ctx.term()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "publisher"
    if mode == "publisher":
        publisher()
    else:
        topic = sys.argv[2] if len(sys.argv) > 2 else ""
        subscriber(topic)
