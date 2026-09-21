"""ZeroMQ REQ/REP エコーサーバー。
使い方:
  ターミナル1: python3 01_zmq_reqrep.py server
  ターミナル2: python3 01_zmq_reqrep.py client
"""
import sys
import time
import zmq

PORT = 5555


def server():
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(f"tcp://*:{PORT}")
    print(f"[server] 起動中... port={PORT}")
    try:
        while True:
            msg = sock.recv_string()
            reply = f"ECHO: {msg}"
            print(f"[server] 受信: {msg!r}  → 返信: {reply!r}")
            sock.send_string(reply)
    except KeyboardInterrupt:
        print("[server] 終了")
    finally:
        sock.close()
        ctx.term()


def client(n: int = 5):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.connect(f"tcp://localhost:{PORT}")
    print(f"[client] 接続: localhost:{PORT}")
    try:
        for i in range(n):
            msg = f"hello {i}"
            sock.send_string(msg)
            reply = sock.recv_string()
            print(f"[client] 送信: {msg!r}  → 応答: {reply!r}")
            time.sleep(0.5)
    finally:
        sock.close()
        ctx.term()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "client"
    if mode == "server":
        server()
    else:
        client()
