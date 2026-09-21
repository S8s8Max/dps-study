# 04 Redpanda 入門

## 学習目標

- Redpanda（Kafka 互換）のトピック・パーティション・コンシューマーグループを理解する
- Docker で Redpanda を起動できる
- aiokafka でプロデューサー・コンシューマーを実装できる
- オフセット管理と「再処理」の概念を理解する

---

## 1. Redpanda とは

**Redpanda** は Kafka 互換のストリーミングプラットフォーム。

```
Apache Kafka:
  - JVM ベース（Java）
  - ZooKeeper / KRaft が必要
  - Pi 3B では動作が重い（JVM = 512MB+ 起動時）

Redpanda:
  - C++ ベース（軽量）
  - ZooKeeper 不要（シングルバイナリ）
  - arm64 対応
  - Pi 3B でも動作可能（512MB 指定）
  - Kafka クライアント（aiokafka, confluent-kafka）がそのまま使える
```

---

## 2. 主要な概念

### トピック（Topic）

メッセージを分類するキュー。Pub/Sub の「チャンネル」に相当。

```
トピック: sensor-events
  └── パーティション 0: [msg1, msg4, msg7, ...]
  └── パーティション 1: [msg2, msg5, msg8, ...]
  └── パーティション 2: [msg3, msg6, msg9, ...]
```

### パーティション（Partition）

トピックを分割した単位。**同じキー → 同じパーティション** に送られる。

```
プロデューサー:
  key="pi-cpu"    → hash("pi-cpu")    % 3 = 0 → パーティション 0
  key="pi-memory" → hash("pi-memory") % 3 = 1 → パーティション 1
  key="pi-temp"   → hash("pi-temp")   % 3 = 2 → パーティション 2
```

同じキーのメッセージが同じパーティションに集まる → **状態をパーティション単位で管理できる**

### オフセット（Offset）

パーティション内のメッセージ位置（0, 1, 2, ...）。コンシューマーはどこまで読んだかを記録する。

```
パーティション 0:  [msg1][msg4][msg7][msg10]
オフセット:          0     1     2     3

コンシューマーが offset=2 まで読んだ → 次は offset=3 から再開
```

### コンシューマーグループ（Consumer Group）

複数のコンシューマーが協調してトピックを分担処理する仕組み。

```
トピック: sensor-events (3パーティション)

グループ "processors":
  コンシューマー A → パーティション 0
  コンシューマー B → パーティション 1
  コンシューマー C → パーティション 2

→ 3台並列で処理（スループット3倍）
→ 1台が落ちると残りに自動で再割り当て（リバランス）
```

---

## 3. Docker で起動

```bash
cd ~/dps-study/docker/redpanda
docker compose up -d
```

起動確認：

```bash
# ブローカー状態確認
docker exec redpanda rpk cluster info

# トピック一覧
docker exec redpanda rpk topic list

# トピック作成（コードから自動作成もできる）
docker exec redpanda rpk topic create sensor-events --partitions 3
```

---

## 4. aiokafka でプロデューサー

```python
from aiokafka import AIOKafkaProducer
import asyncio, json

BOOTSTRAP = "localhost:19092"

async def produce():
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode(),
        key_serializer=lambda k: k.encode() if k else None,
    )
    await producer.start()
    try:
        await producer.send(
            "sensor-events",
            key="pi-cpu",           # 同じキー → 同じパーティション
            value={"sensor": "pi-cpu", "value": 42.5, "ts": 1700000000},
        )
    finally:
        await producer.stop()
```

### キーの重要性

```python
# キーなし → ラウンドロビンで各パーティションに分散
await producer.send("topic", value=data)

# キーあり → 同じキーは常に同じパーティションへ
await producer.send("topic", key="pi-cpu", value=data)
```

状態を持つ処理では **必ずキーを指定** する。

---

## 5. aiokafka でコンシューマー

```python
from aiokafka import AIOKafkaConsumer

async def consume():
    consumer = AIOKafkaConsumer(
        "sensor-events",
        bootstrap_servers="localhost:19092",
        group_id="my-processors",        # コンシューマーグループ
        auto_offset_reset="earliest",    # 最初から読む / "latest" = 新着のみ
        value_deserializer=lambda v: json.loads(v.decode()),
        key_deserializer=lambda k: k.decode() if k else None,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            print(f"partition={msg.partition} offset={msg.offset} "
                  f"key={msg.key} value={msg.value}")
    finally:
        await consumer.stop()
```

### auto_offset_reset の選択

| 設定 | 動作 | 用途 |
|------|------|------|
| `"earliest"` | トピックの先頭から読む | テスト・全データ再処理 |
| `"latest"` | 起動後の新着のみ読む | 本番のリアルタイム処理 |

---

## 6. オフセットと再処理

Redpanda はメッセージを **保持期間が来るまで削除しない**（デフォルト 7 日）。
コンシューマーグループのオフセットをリセットすれば再処理できる。

```bash
# グループのオフセットをリセット（先頭から再処理）
docker exec redpanda rpk group seek my-processors --to earliest

# 特定オフセットに戻す
docker exec redpanda rpk group seek my-processors --to 100
```

これが NATS/ZeroMQ との大きな違い：**メッセージが残っている**。

---

## 7. メッセージ保持の設定

```bash
# Pi 3B のディスク節約のため保持期間を短くする
docker exec redpanda rpk topic alter-config sensor-events \
  --set retention.ms=3600000  # 1 時間
```

---

## 8. NATS との比較

| 項目 | NATS | Redpanda |
|------|------|---------|
| メッセージ保持 | デフォルト保持なし（JetStream で追加可） | デフォルト 7 日 |
| 再処理 | 難しい | オフセットを戻すだけ |
| セットアップ | 単純（1 コマンド） | やや複雑（パーティション設計が必要） |
| スループット | 高い | 高い（Redpanda は特に高スループット） |
| 向いている用途 | マイクロサービス間の通知 | ストリームデータの永続化・再処理 |

---

## 9. まとめ

| 概念 | 意味 |
|------|------|
| トピック | メッセージを分類するキュー |
| パーティション | トピックの分割単位。同キー→同パーティション |
| オフセット | パーティション内の位置。再処理に使う |
| コンシューマーグループ | 複数コンシューマーが協調して分担処理 |
| `auto_offset_reset` | グループ初参加時の開始位置 |

次は **ステートフルパイプライン** で Redpanda + 時間窓集計を組み合わせる。
