"""CAP 定理のデモ：CP vs AP の挙動の違いを示す。

ネットワーク分断が発生したとき：
- CP システム: 書き込みを拒否（一貫性を保つ）
- AP システム: 書き込みを受け入れ（可用性を保つ、回復後に競合解決）

使い方:
  python3 04_cap_demo.py
"""
from dataclasses import dataclass, field
import time


@dataclass
class CPStore:
    """CP ストア: クォーラムが取れないときは書き込みを拒否する。"""
    node_id: int
    data: dict = field(default_factory=dict)
    _partitioned: bool = False

    def write(self, key: str, value, quorum_ok: bool) -> bool:
        if self._partitioned or not quorum_ok:
            raise QuorumError(f"N{self.node_id}: クォーラム不足 → 書き込み拒否")
        self.data[key] = value
        return True

    def read(self, key: str):
        return self.data.get(key)


@dataclass
class APStore:
    """AP ストア: 分断中でも書き込みを受け入れ、回復後に競合解決する。"""
    node_id: int
    data: dict = field(default_factory=dict)
    # (key → (value, timestamp)) で Last-Write-Wins を実現
    timestamps: dict = field(default_factory=dict)

    def write(self, key: str, value, timestamp: float = None) -> bool:
        ts = timestamp or time.time()
        # 分断中でも書き込める（可用性優先）
        if ts >= self.timestamps.get(key, 0):
            self.data[key] = value
            self.timestamps[key] = ts
        return True

    def read(self, key: str):
        return self.data.get(key)

    def merge(self, other: "APStore"):
        """分断回復後の競合解決（Last-Write-Wins）。"""
        for key, ts in other.timestamps.items():
            if ts > self.timestamps.get(key, 0):
                self.data[key] = other.data[key]
                self.timestamps[key] = ts


class QuorumError(Exception):
    pass


def demo_cp():
    print("=" * 60)
    print(" CP システムのデモ（etcd 相当）")
    print("=" * 60)
    print()

    nodes = [CPStore(node_id=i) for i in range(3)]
    quorum = len(nodes) // 2 + 1  # = 2

    print(f"クラスタ: {len(nodes)} ノード, クォーラム: {quorum}")
    print()

    # 正常時の書き込み
    print("【正常時】全ノード生存")
    for node in nodes:
        ok = node.write("leader", "node-0", quorum_ok=True)
        print(f"  N{node.node_id}: write 成功 → leader=node-0")

    print()
    print("【ネットワーク分断】N0 と N1 が切断 → クォーラム喪失")
    print("  分断されたグループ: {N0} vs {N1, N2}")
    print()

    # N0 だけの孤立グループはクォーラム不足
    print("  N0（孤立グループ）の書き込み試行:")
    try:
        nodes[0].write("config", "new-value", quorum_ok=False)
    except QuorumError as e:
        print(f"  ✗ {e}")

    # N1, N2 のグループ（クォーラム OK = 2/3）
    print()
    print("  N1, N2 グループ（クォーラム満たす）の書き込み:")
    for node in [nodes[1], nodes[2]]:
        try:
            ok = node.write("config", "safe-value", quorum_ok=True)
            print(f"  ✓ N{node.node_id}: write 成功 → config=safe-value")
        except QuorumError as e:
            print(f"  ✗ {e}")

    print()
    print("【結果】")
    print("  - N0: 書き込み拒否 → データ一貫性を保った")
    print("  - N1, N2: 安全に書き込み成功（クォーラムがある）")
    print("  - 矛盾は発生しない（一貫性 ○、可用性は N0 で ✗）")


def demo_ap():
    print()
    print("=" * 60)
    print(" AP システムのデモ（Cassandra/NATS 相当）")
    print("=" * 60)
    print()

    node_a = APStore(node_id=0)
    node_b = APStore(node_id=1)

    print("【正常時】両ノードに同じデータ")
    t0 = 1000.0
    node_a.write("sensor_value", 42.0, timestamp=t0)
    node_b.write("sensor_value", 42.0, timestamp=t0)
    print(f"  N0: sensor_value = {node_a.read('sensor_value')}")
    print(f"  N1: sensor_value = {node_b.read('sensor_value')}")

    print()
    print("【ネットワーク分断】N0 と N1 が独立して書き込み")
    print("  N0 のクライアント: sensor_value = 100.0 (t=1001)")
    print("  N1 のクライアント: sensor_value = 200.0 (t=1002)")
    node_a.write("sensor_value", 100.0, timestamp=1001.0)
    node_b.write("sensor_value", 200.0, timestamp=1002.0)

    print()
    print("  分断中の読み取り（古いデータを返す = 結果整合性）:")
    print(f"  N0: sensor_value = {node_a.read('sensor_value')}  ← N1 の書き込みを知らない")
    print(f"  N1: sensor_value = {node_b.read('sensor_value')}  ← N0 の書き込みを知らない")
    print()
    print("  ✓ 書き込みは成功（可用性 ○）")
    print("  ✗ データが不一致（一貫性 ✗）")

    print()
    print("【分断回復】N0 と N1 の競合解決（Last-Write-Wins）")
    node_a.merge(node_b)
    node_b.merge(node_a)
    print(f"  N0: sensor_value = {node_a.read('sensor_value')}  ← N1 の t=1002 が勝った")
    print(f"  N1: sensor_value = {node_b.read('sensor_value')}  ← 同じ")
    print()
    print("  ✓ 最終的には一致（Eventual Consistency）")
    print("  △ N0 の 100.0 は失われた（Last-Write-Wins のコスト）")


def summary():
    print()
    print("=" * 60)
    print(" まとめ")
    print("=" * 60)
    print()
    print("  CP（一貫性優先）:")
    print("    + データが矛盾しない")
    print("    - 分断中は書き込めない（可用性を犠牲）")
    print("    用途: etcd、設定管理、金融取引")
    print()
    print("  AP（可用性優先）:")
    print("    + 分断中も書き込める")
    print("    - 分断中は古いデータを返す可能性（一貫性を犠牲）")
    print("    用途: Redpanda、NATS、センサーデータ")
    print()
    print("  どちらを選ぶかは「古いデータを返すコスト」vs「書き込めないコスト」で決まる")


if __name__ == "__main__":
    demo_cp()
    demo_ap()
    summary()
