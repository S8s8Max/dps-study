# 01 論理時計（Lamport クロック・ベクタークロック）

## なぜ論理時計が必要か

分散システムでは**物理クロックは信頼できません**。
NTP で同期しても数ミリ秒のズレがあり、「どちらのメッセージが先か」を物理時刻だけで判断すると順序が逆転します。

```
ノード A: 10:00:00.100  "注文を作成"
ノード B: 10:00:00.098  "在庫を減らす"  ← 物理的に先だが、実は後
```

**論理時計**は「因果関係（happens-before）」を保存する仕組みです。

## happens-before 関係

Leslie Lamport が 1978 年に定義した **happens-before（→）**：

1. 同じプロセス内で a が b より前に実行された → `a → b`
2. プロセス A がメッセージを送信し、プロセス B が受信した → `send → recv`
3. 推移律：`a → b` かつ `b → c` なら `a → c`

`a → b` でも `b → a` でもない場合、**同時（concurrent）** と呼ぶ。

## Lamport 論理時計

### ルール

```
初期値: clock = 0

イベント発生時:
  clock += 1

メッセージ送信時:
  clock += 1
  メッセージに clock を付ける（タイムスタンプ = t）

メッセージ受信時（タイムスタンプ = t のメッセージ）:
  clock = max(clock, t) + 1
```

### 性質

- `a → b` ならば `L(a) < L(b)`（順方向は保証）
- `L(a) < L(b)` でも `a → b` とは限らない（逆は保証しない）

### シミュレーション

```bash
python3 python/stage6/01_lamport_clock.py
```

出力例：
```
[P0] event t=1
[P1] event t=1
[P0→P1] send t=2, recv t=3   ← P1 の時計が P0 に合わせて進む
[P1] event t=4
[P0] event t=3
```

Lamport クロックでは「P1 の event(t=4) は P0 の event(t=3) より後か？」を判断できません（4 > 3 だが因果関係は不明）。

## ベクタークロック

N ノードのシステムで各ノードが**N 要素のベクトル**を持つ。

```
ノード i の時計: V = [v0, v1, ..., vN-1]
初期値: V = [0, 0, ..., 0]

イベント発生時（ノード i）:
  V[i] += 1

メッセージ送信時（ノード i）:
  V[i] += 1
  メッセージに V を付ける

メッセージ受信時（ノード j、タイムスタンプ W）:
  V[k] = max(V[k], W[k]) for all k
  V[j] += 1
```

### 比較演算

```python
def happens_before(V, W):
    # V → W: V の全要素 ≤ W かつ少なくとも1つ <
    return all(v <= w for v, w in zip(V, W)) and V != W

def concurrent(V, W):
    return not happens_before(V, W) and not happens_before(W, V)
```

### シミュレーション

```bash
python3 python/stage6/02_vector_clock.py
```

出力例：
```
P0 event:    [1, 0, 0]
P1 event:    [0, 1, 0]
P0→P1 send:  [2, 0, 0] → recv [2, 2, 0]
P2 event:    [0, 0, 1]

P0[1,0,0] → P1[2,2,0]? True   (P0 の event は P1 の recv より前)
P1[0,1,0] ∥ P2[0,0,1]? True   (同時 = 因果関係なし)
```

## NATS/Redpanda での論理時計

| システム | 論理時計の実装 |
|---------|-------------|
| Redpanda（Kafka） | **オフセット**が Lamport クロック相当（パーティション内順序保証） |
| etcd (k3s) | **revision**（単調増加）でキーの変更順序を追跡 |
| NATS JetStream | **シーケンス番号**でメッセージ順序を保証 |

### ポイント

- Redpanda のオフセットは**パーティション内**でのみ順序を保証
- 複数パーティションをまたぐ順序は保証しない → ベクタークロックが必要
- NATS の at-least-once は「同じシーケンスが複数回届く可能性がある」= 冪等処理が必要

## まとめ

| 時計 | 保証 | 用途 |
|------|------|------|
| 物理クロック | なし（NTP ±数ms） | ログのタイムスタンプ（参考） |
| Lamport クロック | `a→b ⇒ L(a)<L(b)` | 全体順序付け（デバッグ） |
| ベクタークロック | `a→b ⟺ V(a)<V(b)` | 因果一貫性・競合検出 |

次のステップ → [`02-cap-theorem.md`](./02-cap-theorem.md)
