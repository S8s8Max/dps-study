# 05 ステートフルパイプライン

## 学習目標

- Redpanda + タンブリング窓集計のパイプラインを構築できる
- コンシューマーグループで負荷分散できる
- スループット・レイテンシを計測できる
- Stage 3 全体の学習チェックリストを確認できる

---

## 1. パイプライン全体図

```
【データの流れ】

  ジェネレーター               Redpanda                    プロセッサー
  (センサーデータ生成)          (永続化)                   (窓集計 + 出力)

  ┌──────────────┐          ┌──────────────────┐          ┌──────────────┐
  │  generator   │─ Produce ►│  sensor-events   │─ Consume ►│  processor   │
  │              │          │  (3パーティション) │          │              │
  │ pi-cpu:42.5  │          │  P0: pi-cpu       │          │ タンブリング窓│
  │ pi-memory:60 │          │  P1: pi-memory    │          │ 5秒ごと集計  │
  │ pi-temp:52.1 │          │  P2: pi-temp      │          │ 異常検知     │
  └──────────────┘          └──────────────────┘          └──────────────┘

aiokafka AIOKafkaProducer        Redpanda                aiokafka AIOKafkaConsumer
（キー付き送信）           （パーティション分割）         （コンシューマーグループ）
```

---

## 2. 起動手順

### 2.1 Redpanda を起動する

```bash
cd ~/dps-study/docker/redpanda
docker compose up -d
docker ps | grep redpanda
```

### 2.2 トピックを作成する

```bash
docker exec redpanda rpk topic create sensor-events \
  --partitions 3 \
  --replicas 1
docker exec redpanda rpk topic list
```

### 2.3 プロセッサーを起動する（先に起動）

**ターミナル 1:**

```bash
python3 python/stage3/05_stream_processor.py consumer
```

### 2.4 ジェネレーターでデータを投入する

**ターミナル 2:**

```bash
python3 python/stage3/05_stream_processor.py producer
```

### 2.5 期待する出力

```
# ジェネレーター（ターミナル 2）
[producer] Redpanda 接続: localhost:19092
[producer] トピック: sensor-events
[producer] 送信中... (Ctrl-C で停止)
[producer] #10  pi-cpu=41.3  pi-memory=61.0  pi-temp=52.1
[producer] #20  pi-cpu=38.7  pi-memory=59.8  pi-temp=51.5

# プロセッサー（ターミナル 1）
[processor] Redpanda 接続: localhost:19092
[processor] グループ: stream-processors
[processor] パーティション割り当て: [0, 1, 2]

=== 窓 #1  2026-09-21 10:00:05 ===
  pi-cpu    : 件数=5  平均=39.8  最大=52.4  σ=4.7  [正常]
  pi-memory : 件数=5  平均=60.3  最大=63.1  σ=1.3  [正常]
  pi-temp   : 件数=5  平均=51.2  最大=53.5  σ=1.0  [正常]

=== 窓 #2  2026-09-21 10:00:10 ===
  pi-cpu    : 件数=5  平均=39.5  最大=87.2  σ=19.1  [*** 異常 z=2.50 ***]
  ...
```

---

## 3. 複数プロセッサーで負荷分散

3 つのコンシューマーを起動すると各 1 パーティションを担当する。

**ターミナル 1, 2, 3:**

```bash
python3 python/stage3/05_stream_processor.py consumer  # → パーティション 0
python3 python/stage3/05_stream_processor.py consumer  # → パーティション 1
python3 python/stage3/05_stream_processor.py consumer  # → パーティション 2
```

```bash
# 割り当てを確認
docker exec redpanda rpk group describe stream-processors
```

---

## 4. 再処理の確認

```bash
# グループのオフセットをリセット
docker exec redpanda rpk group seek stream-processors --to earliest

# プロセッサーを再起動すると最初から再処理
python3 python/stage3/05_stream_processor.py consumer
```

過去のデータを再処理できるのが Redpanda（Kafka）の強み。

---

## 5. メッセージ保持とディスク使用量

```bash
# トピックのサイズ確認
docker exec redpanda rpk topic describe sensor-events

# 保持期間を 1 時間に設定（Pi 3B のディスク節約）
docker exec redpanda rpk topic alter-config sensor-events \
  --set retention.ms=3600000
```

---

## 6. Stage 3 完了チェックリスト

- [ ] ステートレスとステートフルの違いを説明できる
- [ ] キーごとの in-memory 状態管理を実装できた（`01_stateful_counter.py`）
- [ ] タンブリング窓で 5 秒ごとの集計を実装できた（`02_tumbling_window.py`）
- [ ] スライディング窓で移動平均・異常検知を実装できた（`03_sliding_window.py`）
- [ ] Redpanda を Docker で起動してトピックを作成できた
- [ ] aiokafka でプロデューサー・コンシューマーを実装できた（`04_redpanda_*.py`）
- [ ] ステートフルパイプラインでスループットを計測できた（`05_stream_processor.py`）
- [ ] コンシューマーグループで 3 並列処理を確認できた
- [ ] オフセットリセットで再処理できた

---

## 7. まとめと次のステップ

### Stage 3 で習得したこと

| 項目 | 習得内容 |
|------|---------|
| ステートフル処理 | キー付き状態管理・時間窓集計 |
| タンブリング窓 | 固定間隔の非重複集計 |
| スライディング窓 | 移動平均・3σ 異常検知 |
| Redpanda | トピック・パーティション・コンシューマーグループ |
| 再処理 | オフセットリセットによる過去データの再集計 |

### Stage 4 へ

Stage 4 では **分散フレームワーク**（Ray・Dask）を学ぶ。
Stage 3 で学んだ「状態管理」と「パーティション」の考え方が基礎になる。

```
Stage 3: 自前でストリーム処理を実装（Redpanda + Python）
  ↓
Stage 4: フレームワークが状態管理・スケジューリングを担う（Ray / Dask）
  例: Ray Streaming、Dask DataFrame のリアルタイム更新
```

```bash
cat docs/stage4-study-guide.md
```
