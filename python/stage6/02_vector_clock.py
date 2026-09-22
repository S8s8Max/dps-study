"""ベクタークロックのシミュレーション。

3 つのプロセス間の因果関係を正確に追跡し、
「happens-before」と「concurrent（同時）」の違いを示す。

使い方:
  python3 02_vector_clock.py
"""
from dataclasses import dataclass, field


@dataclass
class VectorClock:
    pid: int
    n: int  # プロセス数
    clock: list[int] = field(default_factory=list)

    def __post_init__(self):
        if not self.clock:
            self.clock = [0] * self.n

    def copy(self) -> list[int]:
        return self.clock.copy()

    def tick(self) -> list[int]:
        self.clock[self.pid] += 1
        return self.copy()

    def send(self) -> list[int]:
        self.clock[self.pid] += 1
        return self.copy()

    def recv(self, remote: list[int]) -> list[int]:
        self.clock = [max(a, b) for a, b in zip(self.clock, remote)]
        self.clock[self.pid] += 1
        return self.copy()

    def __str__(self) -> str:
        return str(self.clock)


def happens_before(v: list[int], w: list[int]) -> bool:
    """v → w: v の全要素 ≤ w かつ少なくとも 1 つ <"""
    return all(a <= b for a, b in zip(v, w)) and v != w


def concurrent(v: list[int], w: list[int]) -> bool:
    return not happens_before(v, w) and not happens_before(w, v)


@dataclass
class Event:
    pid: int
    clock: list[int]
    desc: str


def simulate():
    N = 3
    processes = [VectorClock(pid=i, n=N) for i in range(N)]
    events: list[Event] = []

    def local_event(pid: int, desc: str) -> Event:
        v = processes[pid].tick()
        e = Event(pid=pid, clock=v.copy(), desc=desc)
        events.append(e)
        print(f"  P{pid} {v}: {desc}")
        return e

    def send_msg(from_pid: int, to_pid: int, desc: str):
        v_send = processes[from_pid].send()
        e_send = Event(pid=from_pid, clock=v_send.copy(), desc=f"→P{to_pid}: {desc}")
        events.append(e_send)
        print(f"  P{from_pid} {v_send}: → P{to_pid} '{desc}'")

        v_recv = processes[to_pid].recv(v_send)
        e_recv = Event(pid=to_pid, clock=v_recv.copy(), desc=f"←P{from_pid}: {desc}")
        events.append(e_recv)
        print(f"  P{to_pid} {v_recv}: ← P{from_pid} '{desc}' (ts={v_send})")
        return e_send, e_recv

    print("=" * 60)
    print(" ベクタークロック シミュレーション")
    print("=" * 60)
    print()

    # シナリオ 1: Lamport との比較
    print("【シナリオ 1】Lamport クロックが判断できないケース")
    e_a = local_event(0, "イベント A")
    e_b = local_event(1, "イベント B")  # A と同時
    _, e_c = send_msg(0, 1, "メッセージ")  # A → C の因果関係
    e_d = local_event(2, "イベント D")   # 全員と同時

    print()
    print("【因果関係の判定】")
    pairs = [
        (e_a, e_c, "A → C?"),
        (e_a, e_b, "A → B? (同時のはず)"),
        (e_b, e_c, "B → C?"),
        (e_a, e_d, "A → D? (同時のはず)"),
    ]
    for ea, eb, label in pairs:
        hb = happens_before(ea.clock, eb.clock)
        conc = concurrent(ea.clock, eb.clock)
        result = "→ (happens-before)" if hb else ("∥ (concurrent)" if conc else "← (逆順)")
        print(f"  {label:20s} {ea.clock} vs {eb.clock}: {result}")

    # 時計リセット
    processes = [VectorClock(pid=i, n=N) for i in range(N)]
    events.clear()

    print()
    print("【シナリオ 2】複数パーティション（Redpanda）の模擬")
    print("  パーティション 0: P0 が書き込み")
    print("  パーティション 1: P1 が書き込み")
    print("  パーティション 2: P2 がマージ")
    print()

    e_w0 = local_event(0, "partition0: write key=A val=1")
    e_w1 = local_event(1, "partition1: write key=A val=2")  # 同時書き込み!

    # P2 が P0 のメッセージを受け取る
    _, e_r0 = send_msg(0, 2, "partition0 result")
    # P2 が P1 のメッセージを受け取る
    _, e_r1 = send_msg(1, 2, "partition1 result")
    e_merge = local_event(2, "merge: conflict detected")

    print()
    print("【競合検出】")
    print(f"  P0 の書き込み: {e_w0.clock}")
    print(f"  P1 の書き込み: {e_w1.clock}")
    conc = concurrent(e_w0.clock, e_w1.clock)
    print(f"  競合（同時書き込み）: {conc}")
    print(f"  → 競合解決が必要 (Last-Write-Wins, or CRDT など)")

    # 時計リセット
    processes = [VectorClock(pid=i, n=N) for i in range(N)]

    print()
    print("【シナリオ 3】因果一貫性の確認")
    print("  P0: ユーザーがパスワードを変更")
    print("  P0 → P1: 変更通知")
    print("  P1: ログイン試行（パスワード変更より後に起きるべき）")
    print()

    e_pwd = local_event(0, "password changed")
    _, e_notify = send_msg(0, 1, "password-changed notification")
    e_login = local_event(1, "login attempt with new password")

    print()
    hb = happens_before(e_pwd.clock, e_login.clock)
    print(f"  パスワード変更 → ログイン: {hb}")
    print(f"  → 因果一貫性が保たれている: ログイン時には変更済み状態が見える")

    print()
    print("【まとめ】")
    print("  ベクタークロック: V(a) < V(b) ⟺ a → b を完全に判定できる")
    print("  Lamport クロック: L(a) < L(b) でも a → b とは限らない")
    print("  実装コスト: N ノードで N 整数のベクトル（N が大きいとオーバーヘッド）")


if __name__ == "__main__":
    simulate()
