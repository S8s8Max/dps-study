# 04 NATS

## 学習目標

- NATS の特徴（軽量・高スループット・クラウドネイティブ）を理解する
- Pub/Sub・Request/Reply・Queue Subscribe の 3 パターンを動かせる
- `nats-py` の基本 API を使える
- MQTT との違いを実体験で理解する

---

## 1. 概念説明

### NATS とは

NATS は Go で書かれた軽量・高スループットなメッセージングシステムです。
単一バイナリで動き、設定ファイルなしで起動できます。

### MQTT との比較

| 特徴 | MQTT | NATS |
|---|---|---|
| 設計思想 | IoT・省帯域 | クラウドネイティブ・高スループット |
| プロトコル | TCP ベースの独自 | TCP ベースの独自 |
| メッセージ永続化 | QoS 1/2 で保証 | JetStream（オプション）|
| Request/Reply | なし（アドホックに実装）| 組み込みサポート |
| クラスタリング | なし（Mosquitto）| 組み込みサポート |
| メモリ使用量 | 〜10MB | 〜10MB |

### NATS の 3 パターン

```
【Pub/Sub】
  Publisher ── subject: sensor.cpu ──► NATS ──► Subscriber

【Request/Reply】
  Client ── request: calc.double ──► NATS ──► Service
          ◄── reply: 84 ──────────────────────

【Queue Subscribe（負荷分散）】
  Publisher ── subject: tasks ──► NATS ──► Worker1  ← どちらか一方に配送
                                       ──► Worker2
```

### サブジェクトのワイルドカード

```
sensor.pi-master.cpu       ← 完全一致
sensor.*.cpu               ← * は 1 トークン（sensor.XXX.cpu）
sensor.>                   ← > は複数トークン（sensor. 以下すべて）
```

---

## 2. NATS サーバーの起動確認

```bash
# Stage 2 の Docker Compose で起動済みのはず
docker ps | grep nats
# CONTAINER ID   IMAGE               STATUS
# xxx            nats:2.10.20-alpine Up X seconds

# HTTP モニタリングで状態確認
curl http://localhost:8222/varz | python3 -m json.tool | head -20
# {
#   "server_id": "...",
#   "version": "2.10.20",
#   ...
# }
```

---

## 3. nats-py のインストール

```bash
pip install nats-py

python3 -c "import nats; print('OK')"
# OK
```

---

## 4. Pub/Sub を動かす

**ターミナル 1（サブスクライバー）:**

```bash
python3 python/stage2/05_nats_pubsub.py subscriber
```

**ターミナル 2（パブリッシャー）:**

```bash
python3 python/stage2/05_nats_pubsub.py publisher
```

期待する出力：

```
# サブスクライバー
[sub] 接続: nats://localhost:4222
[sub] 購読: sensor.>
[sub] sensor.pi-master.cpu: 42.5
[sub] sensor.pi-master.memory: 61.3

# パブリッシャー
[pub] sensor.pi-master.cpu = 42.5
[pub] sensor.pi-master.memory = 61.3
```

---

## 5. Request/Reply を動かす

NATS の Request/Reply はクライアントが一時的なレスポンス用サブジェクトを自動で作ります。

**ターミナル 1（サービス側）:**

```bash
python3 python/stage2/05_nats_reqrep.py service
```

**ターミナル 2（クライアント側）:**

```bash
python3 python/stage2/05_nats_reqrep.py client
```

期待する出力：

```
# サービス
[service] 待機中: calc.double
[service] 要求: 21  → 応答: 42
[service] 要求: 7   → 応答: 14

# クライアント
[client] 要求: 21  → 応答: 42
[client] 要求: 7   → 応答: 14
```

### コードポイント

```python
import asyncio
import nats

async def service():
    nc = await nats.connect("nats://localhost:4222")
    sub = await nc.subscribe("calc.double")
    async for msg in sub.messages:
        n = int(msg.data.decode())
        await msg.respond(str(n * 2).encode())

async def client():
    nc = await nats.connect("nats://localhost:4222")
    reply = await nc.request("calc.double", b"21", timeout=5)
    print(reply.data.decode())   # "42"
```

> **注意**: `nats-py` は asyncio ベースです。`asyncio.run()` で実行します。

---

## 6. Queue Subscribe で負荷分散する

**ターミナル 1, 2（ワーカー）:**

```bash
python3 python/stage2/05_nats_pubsub.py worker 1
python3 python/stage2/05_nats_pubsub.py worker 2
```

**ターミナル 3（プロデューサー）:**

```bash
python3 python/stage2/05_nats_pubsub.py producer 10
```

各ワーカーが約半数ずつタスクを受け取ることを確認します。

---

## 7. よくあるエラーと対処法

### タイムアウトエラー（Request/Reply）

```
nats.errors.NoRespondersError
```

→ サービス側が起動していない。先にサービスを起動してから Request を送る。

### サブジェクトのドット区切りを忘れる

NATS はドット `.` 区切り（MQTT はスラッシュ `/` 区切り）です。

```python
# ✓ NATS: ドット区切り
await nc.publish("sensor.pi-master.cpu", b"42.5")

# ✗ MQTT 風に書かない
await nc.publish("sensor/pi-master/cpu", b"42.5")
```

---

## 8. まとめと次のステップ

### 今回の学習内容

| パターン | 操作 | 特徴 |
|---|---|---|
| Pub/Sub | `publish` / `subscribe` | 1 対多・非同期 |
| Request/Reply | `request` / `respond` | 同期的・組み込みサポート |
| Queue Subscribe | `subscribe` with queue group | 負荷分散 |

### MQTT vs NATS の選択基準

- **IoT センサー・省帯域環境** → MQTT（QoS による配送保証が重要）
- **マイクロサービス間通信・高スループット** → NATS（低レイテンシ・柔軟なパターン）

### 次のステップ

`05-pipeline.md` でこれらを組み合わせた本格的なパイプラインを構築します。

```bash
cat docs/stage2/05-pipeline.md
```
