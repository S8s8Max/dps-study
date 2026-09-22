"""Lamport 論理時計のシミュレーション。

3 つのプロセスがメッセージを交換しながら論理時計が進む様子を示す。

使い方:
  python3 01_lamport_clock.py
"""
from dataclasses import dataclass


@dataclass
class LamportClock:
    pid: int
    clock: int = 0

    def tick(self) -> int:
        self.clock += 1
        return self.clock

    def send(self) -> int:
        self.clock += 1
        return self.clock

    def recv(self, timestamp: int) -> int:
        self.clock = max(self.clock, timestamp) + 1
        return self.clock


@dataclass
class Message:
    sender: int
    receiver: int
    timestamp: int
    content: str


def simulate():
    processes = [LamportClock(pid=i) for i in range(3)]
    log: list[str] = []

    def local_event(pid: int, desc: str):
        t = processes[pid].tick()
        log.append(f"  P{pid} [{t:>3}] {desc}")

    def send_msg(from_pid: int, to_pid: int, content: str) -> Message:
        t_send = processes[from_pid].send()
        log.append(f"  P{from_pid} [{t_send:>3}] → P{to_pid}: '{content}'")
        return Message(sender=from_pid, receiver=to_pid,
                       timestamp=t_send, content=content)

    def recv_msg(msg: Message):
        t_recv = processes[msg.receiver].recv(msg.timestamp)
        log.append(f"  P{msg.receiver} [{t_recv:>3}] ← P{msg.sender}: "
                   f"'{msg.content}' (ts={msg.timestamp})")

    print("=" * 60)
    print(" Lamport 論理時計シミュレーション")
    print("=" * 60)
    print()

    # シナリオ 1: 単純なメッセージ送受信
    print("【シナリオ 1】単純なメッセージ送受信")
    local_event(0, "イベント A")
    local_event(1, "イベント B")
    msg1 = send_msg(0, 1, "hello")
    local_event(0, "イベント C")
    recv_msg(msg1)
    local_event(1, "イベント D")
    for line in log:
        print(line)
    log.clear()

    print()
    print("【観察】")
    print("  P0 の '→ P1 送信' の後、P1 の ← 受信時刻が合わせて進む")
    print(f"  現在の時計: {[p.clock for p in processes]}")

    # 時計リセット
    processes = [LamportClock(pid=i) for i in range(3)]

    print()
    print("【シナリオ 2】因果関係のない同時イベント")
    local_event(0, "A が何かする")
    local_event(1, "B が何かする")
    local_event(2, "C が何かする")
    for line in log:
        print(line)
    log.clear()

    print()
    print("【観察】")
    print("  3 つのイベントは因果関係がない (concurrent)")
    print("  Lamport クロックは全て t=1 → 順序を決定できない")

    # 時計リセット
    processes = [LamportClock(pid=i) for i in range(3)]

    print()
    print("【シナリオ 3】チェーン: P0 → P1 → P2")
    local_event(0, "処理開始")
    m1 = send_msg(0, 1, "データ")
    recv_msg(m1)
    local_event(1, "変換処理")
    m2 = send_msg(1, 2, "変換済みデータ")
    recv_msg(m2)
    local_event(2, "保存完了")
    for line in log:
        print(line)
    log.clear()

    print()
    print("【観察】")
    print("  メッセージが連鎖するたびに時計が大きく進む")
    print("  P2 の最終時計 > P1 > P0 → 因果順序と一致")
    print(f"  最終時計: {[p.clock for p in processes]}")

    print()
    print("【Lamport クロックの限界】")
    print("  L(a) < L(b) でも a → b とは言えない (同時かもしれない)")
    print("  この問題を解決するのがベクタークロック → 02_vector_clock.py")


if __name__ == "__main__":
    simulate()
