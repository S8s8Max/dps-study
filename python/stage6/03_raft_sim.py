"""Raft リーダー選出のシミュレーション。

実際の RPC を使わず、メッセージキューで Raft の
リーダー選出ロジックを模擬する。観察できること：
- Term（任期）の進み方
- 過半数投票によるリーダー決定
- リーダー障害後の再選出

使い方:
  python3 03_raft_sim.py
"""
import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum, auto


class Role(Enum):
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()


@dataclass
class VoteRequest:
    candidate_id: int
    term: int
    last_log_index: int
    last_log_term: int


@dataclass
class VoteResponse:
    voter_id: int
    term: int
    granted: bool


@dataclass
class Heartbeat:
    leader_id: int
    term: int


class RaftNode:
    def __init__(self, node_id: int, n_nodes: int):
        self.node_id = node_id
        self.n_nodes = n_nodes
        self.role = Role.FOLLOWER
        self.current_term = 0
        self.voted_for: int | None = None
        self.votes_received: set[int] = set()
        self.leader_id: int | None = None
        self.alive = True

        # メッセージキュー
        self.inbox: asyncio.Queue = asyncio.Queue()
        # 全ノードへの参照（シミュレーション用）
        self.peers: list["RaftNode"] = []

        # election timeout（150–300ms をシミュレート）
        self.election_timeout = random.uniform(0.15, 0.30)
        self._reset_timeout()

    def _reset_timeout(self):
        self.timeout_at = asyncio.get_event_loop().time() + self.election_timeout

    def log(self, msg: str):
        role_label = {Role.FOLLOWER: "F", Role.CANDIDATE: "C", Role.LEADER: "L"}
        print(f"  N{self.node_id}[T{self.current_term} {role_label[self.role]}]: {msg}")

    async def send_to(self, target_id: int, msg):
        if self.peers[target_id].alive:
            await self.peers[target_id].inbox.put(msg)

    async def broadcast(self, msg):
        for peer in self.peers:
            if peer.node_id != self.node_id and peer.alive:
                await peer.inbox.put(msg)

    async def start_election(self):
        self.current_term += 1
        self.role = Role.CANDIDATE
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}
        self.log(f"選出開始 (term={self.current_term})")

        req = VoteRequest(
            candidate_id=self.node_id,
            term=self.current_term,
            last_log_index=0,
            last_log_term=0,
        )
        await self.broadcast(req)

    async def handle_vote_request(self, req: VoteRequest):
        grant = False
        if req.term > self.current_term:
            self.current_term = req.term
            self.role = Role.FOLLOWER
            self.voted_for = None

        if (req.term >= self.current_term and
                (self.voted_for is None or self.voted_for == req.candidate_id)):
            grant = True
            self.voted_for = req.candidate_id
            self._reset_timeout()

        self.log(f"投票{'✓' if grant else '✗'} → N{req.candidate_id} (term={req.term})")
        resp = VoteResponse(voter_id=self.node_id, term=self.current_term, granted=grant)
        await self.send_to(req.candidate_id, resp)

    async def handle_vote_response(self, resp: VoteResponse):
        if resp.term > self.current_term:
            self.current_term = resp.term
            self.role = Role.FOLLOWER
            return

        if self.role != Role.CANDIDATE or resp.term != self.current_term:
            return

        if resp.granted:
            self.votes_received.add(resp.voter_id)
            quorum = self.n_nodes // 2 + 1
            self.log(f"票を受取: {len(self.votes_received)}/{self.n_nodes} (クォーラム={quorum})")
            if len(self.votes_received) >= quorum:
                self.role = Role.LEADER
                self.leader_id = self.node_id
                self.log("★ リーダーに就任!")
                await self.broadcast(Heartbeat(leader_id=self.node_id, term=self.current_term))

    async def handle_heartbeat(self, hb: Heartbeat):
        if hb.term >= self.current_term:
            self.current_term = hb.term
            self.role = Role.FOLLOWER
            self.leader_id = hb.leader_id
            self._reset_timeout()

    async def run(self, duration: float):
        loop = asyncio.get_event_loop()
        end_time = loop.time() + duration

        while loop.time() < end_time and self.alive:
            now = loop.time()
            timeout_left = max(0.001, self.timeout_at - now)

            try:
                msg = await asyncio.wait_for(self.inbox.get(), timeout=timeout_left)
            except asyncio.TimeoutError:
                if self.role != Role.LEADER:
                    await self.start_election()
                    self._reset_timeout()
                continue

            if isinstance(msg, VoteRequest):
                await self.handle_vote_request(msg)
            elif isinstance(msg, VoteResponse):
                await self.handle_vote_response(msg)
            elif isinstance(msg, Heartbeat):
                await self.handle_heartbeat(msg)

        self.log(f"終了 (leader={self.leader_id})")


async def run_election_scenario(n_nodes: int, duration: float):
    loop = asyncio.get_event_loop()
    nodes = [RaftNode(i, n_nodes) for i in range(n_nodes)]
    for node in nodes:
        node.peers = nodes

    tasks = [asyncio.create_task(node.run(duration)) for node in nodes]
    await asyncio.gather(*tasks)
    return nodes


async def main():
    print("=" * 60)
    print(" Raft リーダー選出 シミュレーション")
    print("=" * 60)
    print()

    # シナリオ 1: 正常な選出（3ノード）
    print("【シナリオ 1】3ノードクラスタの正常な選出")
    print(f"  各ノードの election timeout をランダムに設定")
    print()
    nodes = await run_election_scenario(n_nodes=3, duration=0.8)

    leaders = [n for n in nodes if n.role == Role.LEADER]
    print()
    if leaders:
        print(f"  → リーダー: N{leaders[0].node_id} (term={leaders[0].current_term})")
    else:
        print("  → リーダー未決定（timeout 内に選出できず）")

    print()
    print("【シナリオ 2】ノード障害後の再選出（5ノード）")
    print()

    async def scenario_with_failure():
        N = 5
        loop = asyncio.get_event_loop()
        nodes = [RaftNode(i, N) for i in range(N)]
        for node in nodes:
            node.peers = nodes

        # 0.4 秒後にリーダーを強制的に停止
        async def kill_leader_after_delay():
            await asyncio.sleep(0.4)
            for node in nodes:
                if node.role == Role.LEADER:
                    node.alive = False
                    print(f"\n  *** N{node.node_id} (リーダー) を停止 ***\n")
                    break

        tasks = [asyncio.create_task(node.run(1.2)) for node in nodes]
        await asyncio.gather(kill_leader_after_delay(), *tasks)
        return nodes

    nodes2 = await scenario_with_failure()
    leaders2 = [n for n in nodes2 if n.role == Role.LEADER and n.alive]
    print()
    if leaders2:
        print(f"  → 新リーダー: N{leaders2[0].node_id} (term={leaders2[0].current_term})")
        print(f"  → Term が増加: リーダー障害 → 新選出が行われた")
    else:
        print("  → リーダー未決定")

    print()
    print("【ポイント】")
    print("  1. election timeout が最も短いノードが先に立候補")
    print("  2. クォーラム（過半数）の票で当選")
    print("  3. リーダー障害後、残りのノードが election timeout で気づき再選出")
    print("  4. Term（任期）は単調増加 → 古い Term のリーダーを無視できる")


if __name__ == "__main__":
    asyncio.run(main())
