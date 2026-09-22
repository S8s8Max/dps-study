# 05 理論と実装の対応

## ステージ 0–5 を理論で読み直す

このドキュメントでは、ここまで構築してきたシステムを**分散システム理論の視点**で再解釈します。

## 論理時計の実装

### Redpanda（Stage 3）のオフセット = Lamport クロック

```
パーティション 0: offset [0, 1, 2, 3, ...]  ← 単調増加
パーティション 1: offset [0, 1, 2, 3, ...]  ← 別の単調増加

→ パーティション内は Lamport クロック的に順序保証
→ パーティション間は順序保証なし（ベクタークロックが必要）
```

**実務への応用**：センサーデータを複数パーティションに分散させるとき、
パーティションをまたぐイベントの順序が重要な場合はベクタークロックをメッセージに付ける。

### NATS JetStream（Stage 2）のシーケンス番号

```python
# NATS メッセージのシーケンス番号 = Lamport クロック
msg.metadata.sequence.stream   # ストリーム内の連番
msg.metadata.sequence.consumer # コンシューマーごとの連番
```

### etcd（k3s / Stage 5）の revision

```bash
# etcd の全操作に単調増加の revision が付く
kubectl get cm my-config -o json | jq '.metadata.resourceVersion'
# → "12345" ← これが Lamport クロック
```

## CAP トレードオフの実装

### k3s etcd = CP システム

```bash
# マスターノードを 2 台停止（5 ノード構成で）
# → クォーラム喪失 → 書き込み不可
kubectl apply -f pod.yaml
# Error: etcdserver: leader is unavailable

# → 「可用性」を犠牲にして「一貫性」を保った
```

**実装上の意味**: Pod のスケジューリング情報が矛盾してはいけない → CP が正しい選択。

### Redpanda = AP システム（デフォルト設定）

```python
# acks=1（リーダーだけ確認）→ AP: 速いが分断時に消える可能性
producer = AIOKafkaProducer(acks=1)

# acks="all" → CP に近い: 全レプリカ確認後に応答
producer = AIOKafkaProducer(acks="all")
```

`acks="all"` + `min.insync.replicas=2` で強い一貫性を選択できる。

## Raft の実装例：k3s etcd

### リーダー確認

```bash
# k3s のリーダーノードを確認
sudo k3s etcd-snapshot ls
sudo journalctl -u k3s | grep "became leader" | tail -5

# Pod のスケジューリングはリーダーの etcd だけが受け付ける
kubectl get lease -n kube-system kube-scheduler
# → リーダーの Pod 名が表示される
```

### ノード障害時の Raft 動作

```bash
# ワーカーノードを停止
ssh pi-worker01 "sudo systemctl stop k3s-agent"

# マスターノードで確認
kubectl get nodes
# NAME          STATUS     ROLES    AGE
# pi-master01   Ready      master   5d
# pi-worker01   NotReady   worker   5d  ← 障害検知
# pi-worker02   Ready      worker   5d

# Pod は自動的に他のノードに再スケジュール（約 5 分後）
kubectl get pods -o wide  # NODE 列が変わる
```

5 分のデフォルト待機は `pod-eviction-timeout` の設定値。

## 障害モデルと k3s の動作

### クラッシュ障害（OOMKilled）

```bash
# メモリ不足で Pod が殺される
kubectl describe pod <name> | grep -A5 "OOMKilled"
# → Containers: ...  Reason: OOMKilled
# → k3s は自動再起動（restartPolicy: Always）
```

対策（Stage 5 で設定済み）：

```yaml
resources:
  limits:
    memory: "128Mi"   # OOMKill の閾値
  requests:
    memory: "64Mi"    # スケジュール時の確保量
```

### ネットワーク分断の模擬

```bash
# Pi ノード間のネットワークを切断
sudo iptables -A INPUT -s <pi-worker01-ip> -j DROP
sudo iptables -A OUTPUT -d <pi-worker01-ip> -j DROP

# 分断後の状態を確認
kubectl get nodes --watch  # NotReady になるまで待つ

# 回復
sudo iptables -D INPUT -s <pi-worker01-ip> -j DROP
sudo iptables -D OUTPUT -d <pi-worker01-ip> -j DROP
```

**観察ポイント**：
- etcd のクォーラムを保っている限り（3 ノード中 2 ノード生存）、マスターは動き続ける
- 分断されたワーカーの Pod は「失われた」とみなされ、再スケジュールされる

## NATS の at-least-once と冪等処理

2 将軍問題の実用的解：「確認できるまで何度も送る」

```python
# Stage 2 の NATS パブリッシャー
await nc.publish("sensor.data", data)
# → ネットワーク障害で Ack が来ない場合、再送される

# コンシューマーは冪等に処理する必要がある
async def handle(msg):
    msg_id = msg.headers.get("Nats-Msg-Id")  # 重複排除用 ID
    if already_processed(msg_id):
        await msg.ack()
        return
    process(msg)
    mark_processed(msg_id)
    await msg.ack()
```

JetStream の `Nats-Msg-Id` ヘッダーを使うと、サーバー側で重複排除してくれる。

## 整合性モデルと実装の選択指針

```
質問: このデータの「古さ」はどの程度許容できるか？

許容できない（金融取引・設定変更など）
  → 強一貫性 (linearizability)
  → etcd / PostgreSQL with serializable isolation

数秒なら許容できる（センサーデータ・ログ）
  → 結果整合性 (eventual consistency)
  → Redpanda / Cassandra / NATS

因果関係だけ保証したい（ユーザーアクション・イベントソーシング）
  → 因果一貫性 (causal consistency)
  → ベクタークロック付きメッセージ + Redpanda
```

## 学習の振り返り

| Stage | 実装 | 理論 |
|-------|------|------|
| 0 | クラスタ構築 | 分散システムの前提環境 |
| 1 | multiprocessing / mpi4py | 並列計算の基本 |
| 2 | ZeroMQ / NATS | at-least-once・2将軍問題 |
| 3 | Redpanda・時間窓 | オフセット＝論理時計・パーティション分散 |
| 4 | Ray / Dask | ObjectRef の因果性・スケジューリング |
| 5 | k3s / etcd | Raft コンセンサス・CP システム・liveness probe |
| **6** | **理論** | **論理時計・CAP・Raft・障害モデル** |

## 次のステップ（Stage 6 以降）

Stage 6 で理論基盤が揃いました。応用として：

- **分散トランザクション**: 2-Phase Commit (2PC)、Sagas パターン
- **CRDT（Conflict-free Replicated Data Type）**: 結果整合性を保証するデータ構造
- **サービスメッシュ**: Istio / Linkerd による mTLS・トラフィック制御
- **オブザーバビリティ**: 分散トレーシング（Jaeger）、メトリクス（Prometheus）の理論的背景
