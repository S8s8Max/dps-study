# 05 パイプライン構築

## 学習目標

- ZeroMQ Push/Pull と NATS を組み合わせたパイプラインを構築できる
- プロデューサー → ワーカー → コレクターの 3 層構成を実装できる
- 処理スループット（件/秒）を計測できる
- Docker Compose で全コンポーネントを管理できる

---

## 1. 概念説明

### Stage 2 パイプラインのアーキテクチャ

```
【データの流れ】

  プロデューサー         ワーカープール              コレクター
  (ZeroMQ PUSH)      (ZeroMQ PULL → NATS PUB)    (NATS SUB)

  ┌──────────┐         ┌──────────┐
  │ producer │─ PUSH ─►│ worker 1 │─ NATS ─►┌────────────┐
  │          │         ├──────────┤  PUB     │ collector  │
  │  タスクを │─ PUSH ─►│ worker 2 │─ NATS ─►│            │
  │  生成    │         ├──────────┤          │ 結果を集約 │
  │          │─ PUSH ─►│ worker 3 │─ NATS ─►│ 統計を表示 │
  └──────────┘         └──────────┘          └────────────┘

ZeroMQ: タスク配布（ブローカーレスで低レイテンシ）
NATS:   結果収集（複数コレクターへのファンアウトが可能）
```

### なぜ 2 つのメッセージングを組み合わせるか

```
ZeroMQ PUSH/PULL の長所:
  - ブローカー不要 → 低レイテンシ
  - ラウンドロビンで自動負荷分散
  ZeroMQ の短所:
  - 宛先 IP/ポートを静的に指定が必要

NATS Pub/Sub の長所:
  - 複数のサブスクライバーに配送
  - サブスクライバーが動的に増減できる
  NATS の短所:
  - サーバー（ブローカー）が必要

→ 入力側（タスク配布）は ZeroMQ、出力側（結果収集）は NATS が合理的
```

---

## 2. パイプラインの起動手順

### 2.1 ブローカーを起動する

```bash
cd ~/dps-study/docker/messaging
docker compose up -d
docker ps | grep -E "mosquitto|nats"
```

### 2.2 コレクターを最初に起動する（NATS サブスクライバー）

**ターミナル 1:**

```bash
python3 python/stage2/06_pipeline_collector.py
```

### 2.3 ワーカーを起動する（ZeroMQ PULL + NATS PUB）

**ターミナル 2, 3, 4（3 ワーカー）:**

```bash
python3 python/stage2/06_pipeline_worker.py 1
python3 python/stage2/06_pipeline_worker.py 2
python3 python/stage2/06_pipeline_worker.py 3
```

### 2.4 プロデューサーでタスクを投入する

**ターミナル 5:**

```bash
python3 python/stage2/06_pipeline_producer.py 30
```

### 2.5 期待する出力

```
# コレクター
[collector] 接続: NATS nats://localhost:4222
[collector] 購読: pipeline.results
[collector] #1  worker=2  入力=1   結果=1    (0.05s)
[collector] #2  worker=1  入力=2   結果=4    (0.05s)
[collector] #3  worker=3  入力=3   結果=9    (0.05s)
...
[collector] === 完了 ===
[collector] 合計: 30 件  スループット: 19.4 件/秒

# ワーカー 1
[worker1] タスク 1  → 結果 1   (0.050s)
[worker1] タスク 4  → 結果 16  (0.050s)

# プロデューサー
[producer] 30 件送信完了
```

---

## 3. スループットを計測する

プロセス数を変えてスループットの変化を観察します：

```bash
# ワーカー 1 台
python3 python/stage2/06_pipeline_worker.py 1 &
python3 python/stage2/06_pipeline_producer.py 30
# → ~10 件/秒

# ワーカー 3 台
python3 python/stage2/06_pipeline_worker.py 1 &
python3 python/stage2/06_pipeline_worker.py 2 &
python3 python/stage2/06_pipeline_worker.py 3 &
python3 python/stage2/06_pipeline_producer.py 30
# → ~30 件/秒（ほぼ線形スケール）
```

---

## 4. Stage 2 完了チェックリスト

- [ ] ZeroMQ Req/Rep でエコーサーバーが動いた
- [ ] ZeroMQ Pub/Sub でトピックフィルターが機能した
- [ ] ZeroMQ Push/Pull で 3 ワーカーに均等分散された
- [ ] Mosquitto に MQTT で Pub/Sub できた
- [ ] NATS で Request/Reply が動いた
- [ ] NATS Queue Subscribe で負荷分散が確認できた
- [ ] ZeroMQ + NATS のパイプラインでスループットを計測した

---

## 5. まとめと次のステップ

### Stage 2 で習得したこと

| 項目 | 習得内容 |
|---|---|
| Req/Rep | 同期リクエスト・ZeroMQ REQ/REP・NATS Request |
| Pub/Sub | 非同期配信・ZeroMQ PUB/SUB・MQTT・NATS |
| Push/Pull | 負荷分散キュー・ZeroMQ・NATS Queue Group |
| パイプライン | 複数ツールの組み合わせ・スループット計測 |

### Stage 3 へ

Stage 3 では「状態を持つストリーム処理」を学びます。
Stage 2 で学んだメッセージングの上に、**時間窓**・**パーティショニング**・**Redpanda** を重ねます。

```
Stage 2: ステートレス（各メッセージを独立に処理）
  ↓
Stage 3: ステートフル（過去のメッセージを参照・集計）
  例: 直近 1 分間の CPU 平均、異常検知、集計
```

```bash
cat docs/stage3-study-guide.md
```
