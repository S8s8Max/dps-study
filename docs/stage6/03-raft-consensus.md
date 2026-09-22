# 03 Raft コンセンサスアルゴリズム

## なぜコンセンサスが必要か

分散システムでは複数のノードが**同じ状態に合意**する必要があります。

```
ノード A: "現在のリーダーは自分"
ノード B: "現在のリーダーは自分"
ノード C: "現在のリーダーは B"
```

この状態が続くと**スプリットブレイン（split brain）**が発生し、データが矛盾します。

**コンセンサスアルゴリズム**はノードが合意に達する手順を定義します。

## Raft の概要

Diego Ongaro と John Ousterhout が 2013 年に発表。Paxos より理解しやすいことを目標に設計。

k3s は **etcd** を状態ストアとして使っており、etcd は内部で Raft を実装しています。

### 3 つのサブプロブレム

1. **リーダー選出（Leader Election）**
2. **ログ複製（Log Replication）**
3. **安全性（Safety）**

## ノードの役割

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Leader    │─────│  Follower   │─────│  Follower   │
│  (1 つだけ) │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       └───────── Candidate（選出中）───────────┘
```

| 役割 | 説明 |
|------|------|
| **Leader** | クライアントのリクエストを受け、Follower にログを複製する |
| **Follower** | Leader からのログを受け取り適用する |
| **Candidate** | Leader 選出に立候補中（一時的） |

## Term（任期）

Raft はタイムを**Term（任期）**という単調増加の整数で区切る。

```
|─ Term 1 ─|─ Term 2 ─|─ Term 3 ─|─ Term 4 ─|
  Leader=A   選出中     Leader=B   Leader=B
```

- 各 Term には最大 1 人のリーダー
- ノードが古い Term のメッセージを受け取ったら無視する

## リーダー選出

### Heartbeat タイムアウト

Leader は定期的に Follower に **heartbeat**（`AppendEntries` の空メッセージ）を送る。
Follower が **election timeout**（150–300ms ランダム）の間 heartbeat を受け取らないと：

```
1. Follower → Candidate に遷移
2. Term をインクリメント
3. 自分に投票
4. 他のノードに RequestVote を送る
```

### 投票ルール

- 各ノードは 1 Term につき 1 票だけ投票できる（先着順）
- **過半数（クォーラム）**の票を得た Candidate が新しい Leader になる

```
5 ノードクラスタ: クォーラム = 3
3 ノードクラスタ: クォーラム = 2
```

### シミュレーション

```bash
python3 python/stage6/03_raft_sim.py
```

## ログ複製

リーダーが選出されたら、クライアントの書き込みを処理：

```
クライアント ──→ Leader: "set x=5"
                  │
                  ├──→ Follower A: AppendEntries(entry)
                  ├──→ Follower B: AppendEntries(entry)
                  │
                  ← 過半数が ACK したら commit
                  │
                  └──→ 全 Follower に commit を通知
```

### ログの構造

```
index: [1]    [2]    [3]    [4]
term:  [1]    [1]    [2]    [3]
cmd:   [x=1]  [y=2]  [x=5]  [z=3]
                              ↑
                              commitIndex（ここまでコミット済み）
```

### 安全性の保証

**「コミット済みのエントリは絶対に失われない」**

- Leader は最新のログを持つノードのみ（投票時に `lastLogIndex` と `lastLogTerm` を比較）
- 古いログを持つ Candidate には投票しない

## クォーラムと障害耐性

```
ノード数 N = 2f + 1 のとき、f 台まで障害を許容できる
```

| クラスタサイズ | 障害許容数 | クォーラム |
|-------------|----------|---------|
| 3 | 1 | 2 |
| 5 | 2 | 3 |
| 7 | 3 | 4 |

**k3s の推奨: 3 ノード（マスター）**
- Pi 3 × 3 台でクラスタを組むと 1 台の障害に耐えられる
- ただし Pi 3B の RAM 制限で etcd が OOMKill されるリスクあり

## k3s における Raft

```bash
# k3s の etcd（ Raft）の状態確認
kubectl get endpoints -n kube-system

# etcd メンバー一覧（k3s embedded etcd）
sudo k3s etcd-snapshot ls

# リーダーの確認（k3s のログ）
sudo journalctl -u k3s | grep "became leader"
```

## Raft と Paxos の比較

| 観点 | Raft | Paxos |
|------|------|-------|
| 理解しやすさ | ○（明確なリーダー） | △（役割が複雑） |
| パフォーマンス | 同等 | 同等 |
| リーダー変更時 | 新 Leader が全ログを持つ | 複雑な reconciliation |
| 実装例 | etcd, CockroachDB | Chubby, Spanner |

## まとめ

- Raft = **リーダーを 1 つ決めて、そこに書き込みを集中させる**
- **クォーラム（過半数）**が鍵：クォーラム以上のノードが生きていれば進歩できる
- k3s の etcd は Raft を使って Pod スケジュール情報などの一貫性を保証している
- 障害が多い環境（Pi クラスタ）では **奇数台のマスター** が重要

次のステップ → [`04-fault-models.md`](./04-fault-models.md)
