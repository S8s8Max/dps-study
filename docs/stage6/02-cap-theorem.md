# 02 CAP 定理と整合性モデル

## CAP 定理とは

Eric Brewer が 2000 年に提唱し、Gilbert と Lynch が 2002 年に証明した定理：

> **ネットワーク分断（P）が発生したとき、一貫性（C）と可用性（A）を同時に保証することはできない。**

3 つの性質：

| 記号 | 名前 | 意味 |
|------|------|------|
| **C** | Consistency（一貫性） | 全ノードが同じデータを返す（線形一貫性） |
| **A** | Availability（可用性） | 応答が返ってくる（タイムアウトしない） |
| **P** | Partition Tolerance（分断耐性） | ネットワーク分断があっても動作する |

実際の分散システムは必ず P が必要（ネットワークは分断しうる）なので、選択は **CP か AP** のどちらか。

```
      C
     / \
    /   \
  CP    CA ← 現実には存在しない
    \   /
     \ /
      P ── AP
```

## CP vs AP の代表システム

### CP（一貫性を優先、分断時は可用性を犠牲）

```
ノード A ─╳─ ノード B   ← 分断
    ↓
エラーを返す（正確なデータを返せないなら返さない）
```

| システム | 説明 |
|---------|------|
| **etcd**（k3s の状態ストア） | Raft で一貫性保証。マスターノードが死ぬと書き込み不可 |
| **ZooKeeper** | Raft 類似の ZAB プロトコル |
| HBase | 強一貫性の分散 KV |

### AP（可用性を優先、分断時は一貫性を犠牲）

```
ノード A ─╳─ ノード B   ← 分断
    ↓
古いデータでも返す（結果整合性）
```

| システム | 説明 |
|---------|------|
| **Redpanda / Kafka** | パーティションリーダーが応答。分断時に古いデータの可能性 |
| **NATS** | クラスターが分断しても各ノードはメッセージ受付 |
| Cassandra | Eventual Consistency（`CONSISTENCY ONE` 設定時） |
| DynamoDB | デフォルトは結果整合性 |

## 整合性モデルの階層

強い ←──────────────────────→ 弱い

```
線形一貫性（Linearizability）
    │ 全操作に全体順序があり、リアルタイム順序と一致
    │ 例: etcd の単一キー操作
    ▼
逐次一貫性（Sequential Consistency）
    │ 全体順序はあるが、リアルタイム順序と一致しなくてよい
    │ 例: CPU のメモリモデル（x86 TSO）
    ▼
因果一貫性（Causal Consistency）
    │ 因果関係のある操作だけ順序を保証
    │ 例: ベクタークロックで管理された分散 KV
    ▼
結果整合性（Eventual Consistency）
    │ いずれ全ノードが同じ値になる（いつかは不明）
    │ 例: Cassandra, NATS Streaming のレプリケーション
    ▼
最弱: 保証なし
```

## PACELC モデル（CAP の拡張）

CAP は分断時のみを議論するが、**分断がない平常時**のトレードオフも重要：

```
if Partition:
    Availability vs Consistency
else:
    Latency vs Consistency
```

| システム | P 時 | 平常時 |
|---------|------|--------|
| etcd | CP（一貫性） | EC（高レイテンシ、強一貫性） |
| Redpanda | AP（可用性） | EL（低レイテンシ、結果整合性） |
| Cassandra | AP | EL |
| MySQL レプリケーション | CP | EC |

## デモ: AP vs CP の挙動確認

```bash
python3 python/stage6/04_cap_demo.py
```

シミュレーションで以下を確認：
1. **CP モード**: 分断中は書き込みを拒否（`QuorumError`）
2. **AP モード**: 分断中も書き込み成功、分断回復後に競合解決（Last-Write-Wins）

## ステージ 0–5 での CAP

| 実装 | モード | 理由 |
|------|--------|------|
| k3s (etcd) | CP | クラスター状態は矛盾してはいけない |
| Redpanda | AP | ストリームは一時的な古いデータより可用性が重要 |
| NATS (JetStream) | AP | メッセージングは繋がっている方が価値がある |
| Ray オブジェクトストア | CP | タスクの依存関係は正確でなければならない |

## まとめ

- **CAP は P が前提**：現実のネットワークは分断するので CP か AP を選ぶ
- **CP**: etcd・ZooKeeper → 設定・メタデータ・トランザクション
- **AP**: Redpanda・NATS・Cassandra → センサーデータ・ログ・メッセージ
- **PACELC** で平常時のレイテンシ vs 一貫性トレードオフも把握する

次のステップ → [`03-raft-consensus.md`](./03-raft-consensus.md)
