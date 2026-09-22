# 02 ZeroMQ

## 学習目標

- ZeroMQ の 3 ソケット型（REQ/REP、PUB/SUB、PUSH/PULL）を動かせる
- ブローカーレスで TCP 通信するコードを書ける
- `pyzmq` の基本 API（`socket.send`、`socket.recv`）を使える
- 複数プロセスをターミナルで同時に起動して通信を確認できる

---

## 1. 概念説明

### ZeroMQ の特徴

ZeroMQ（ØMQ）はブローカー不要のメッセージングライブラリです。
ソケットのように使えますが、接続管理・再接続・バッファリングが自動で行われます。

```
【通常の TCP ソケット】
  送信側: bind → accept → send
  受信側: connect → recv
  → プログラマが順序・再接続を管理

【ZeroMQ】
  送信側: socket(PUSH) → bind → send
  受信側: socket(PULL) → connect → recv
  → ZeroMQ が接続管理・バッファリングを自動で行う
```

### 3 ソケット型の対応

```
REQ ──────► REP    (リクエスト・応答)
PUB ──────► SUB    (発行・購読)
PUSH ─────► PULL   (タスク配布)
```

---

## 2. インストールと事前確認

> 📦 仮想環境が有効か確認してください（`(.venv)` がプロンプトに出ているか）。
> まだの場合は [`docs/python-setup.md`](../python-setup.md) を先に実施します。

```bash
source .venv/bin/activate
pip install -r requirements/stage2.txt

# 動作確認
python3 -c "import zmq; print(zmq.zmq_version())"
# 4.x.x
```

---

## 3. REQ/REP でエコーサーバーを作る

2 つのターミナルで実行します。

**ターミナル 1（サーバー側）:**

```bash
python3 python/stage2/01_zmq_reqrep.py server
```

**ターミナル 2（クライアント側）:**

```bash
python3 python/stage2/01_zmq_reqrep.py client
```

期待する出力：

```
# サーバー側
[server] 起動中... port=5555
[server] 受信: "hello 0"  → 返信: "ECHO: hello 0"
[server] 受信: "hello 1"  → 返信: "ECHO: hello 1"

# クライアント側
[client] 送信: "hello 0"  → 応答: "ECHO: hello 0"
[client] 送信: "hello 1"  → 応答: "ECHO: hello 1"
```

### REQ/REP のコードポイント

```python
import zmq

# サーバー（REP = 応答側）
ctx = zmq.Context()
sock = ctx.socket(zmq.REP)
sock.bind("tcp://*:5555")       # ← すべての NIC でリッスン
while True:
    msg = sock.recv_string()
    sock.send_string(f"ECHO: {msg}")

# クライアント（REQ = 要求側）
sock = ctx.socket(zmq.REQ)
sock.connect("tcp://localhost:5555")
sock.send_string("hello")
reply = sock.recv_string()
```

> **注意**: REQ と REP は必ず交互に send/recv します。
> 2 回連続で send するとブロックします。

---

## 4. PUB/SUB でセンサーデータを配信する

**ターミナル 1（パブリッシャー）:**

```bash
python3 python/stage2/02_zmq_pubsub.py publisher
```

**ターミナル 2, 3（サブスクライバー）:**

```bash
# ターミナル 2: CPU トピックを購読
python3 python/stage2/02_zmq_pubsub.py subscriber cpu

# ターミナル 3: temperature トピックを購読
python3 python/stage2/02_zmq_pubsub.py subscriber temperature
```

期待する出力：

```
# パブリッシャー
[pub] cpu 42.5%
[pub] temperature 55.2°C
[pub] cpu 43.1%

# サブスクライバー（cpu）
[sub:cpu] 42.5%
[sub:cpu] 43.1%     ← temperature は来ない

# サブスクライバー（temperature）
[sub:temperature] 55.2°C
```

### PUB/SUB のコードポイント

```python
# パブリッシャー（PUB）
sock = ctx.socket(zmq.PUB)
sock.bind("tcp://*:5556")
sock.send_string(f"cpu {value}")    # "トピック データ" の形式

# サブスクライバー（SUB）
sock = ctx.socket(zmq.SUB)
sock.connect("tcp://localhost:5556")
sock.setsockopt_string(zmq.SUBSCRIBE, "cpu")   # フィルター設定
msg = sock.recv_string()
```

> **注意**: PUB/SUB には起動順序の問題があります。
> サブスクライバーが先に起動していないと最初のメッセージを逃します（slow joiner）。
> 本番では ZeroMQ の XPUB/XSUB を使って解決します。

---

## 5. PUSH/PULL でワーカープールを作る

**ターミナル 1（ベンチラーター/プロデューサー）:**

```bash
python3 python/stage2/03_zmq_pushpull.py producer 20
```

**ターミナル 2, 3, 4（ワーカー）:**

```bash
python3 python/stage2/03_zmq_pushpull.py worker 1
python3 python/stage2/03_zmq_pushpull.py worker 2
python3 python/stage2/03_zmq_pushpull.py worker 3
```

**ターミナル 5（コレクター/結果集約）:**

```bash
python3 python/stage2/03_zmq_pushpull.py collector 20
```

期待する出力：

```
# コレクター
[collector] 受信: タスク0の結果=0
[collector] 受信: タスク2の結果=4
[collector] 受信: タスク1の結果=1
...（順番は不定）
[collector] 全 20 件受信完了
```

---

## 6. よくあるエラーと対処法

### `Address already in use`

```python
# 前回のプロセスが残っている
sock.bind("tcp://*:5555")
# zmq.error.ZMQError: Address already in use
```

```bash
# ポートを使っているプロセスを確認・終了
ss -tlnp | grep 5555
kill <PID>
```

### REQ/REP でブロックする

REQ ソケットは send → recv の順序を強制します。
`recv` の前に `send` を 2 回呼ぶとブロックします。

```python
# ✓ 必ず交互に
sock.send_string("request")
reply = sock.recv_string()     # ← これを省くと次の send でブロック
```

### PUB/SUB でメッセージが届かない

- サブスクライバーを先に起動する（slow joiner 問題）
- `SUBSCRIBE` フィルターを正確に設定する（前方一致）

```python
sock.setsockopt_string(zmq.SUBSCRIBE, "")   # "" = 全トピックを受信
sock.setsockopt_string(zmq.SUBSCRIBE, "cpu")  # "cpu" で始まるもの
```

---

## 7. まとめと次のステップ

### 今回の学習内容

| ソケット型 | パターン | 使いどころ |
|---|---|---|
| REQ/REP | 同期リクエスト | API 呼び出し、計算依頼 |
| PUB/SUB | 非同期配信 | センサーデータ、イベント通知 |
| PUSH/PULL | 負荷分散 | バッチ処理、ワーカープール |

### 次のステップ

`03-mqtt.md` では Docker で Mosquitto ブローカーを立ち上げ、
MQTT の Pub/Sub を体験します。

```bash
cat docs/stage2/03-mqtt.md
```
