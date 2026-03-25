import random
import math
import numpy as np
import matplotlib.pyplot as plt
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Dict, Tuple, Callable

class Direction(Enum):
    OUTBOUND = auto()
    INBOUND = auto()

class Port(Enum):
    LEFT = auto()
    RIGHT = auto()
    
    def opposite(self) -> 'Port':
        return Port.RIGHT if self == Port.LEFT else Port.LEFT

@dataclass(frozen=True)
class Message:
    origin_uid: int
    direction: Direction
    hop_count: int

class Node:
    def __init__(self, uid: int, log_func: Callable[[str], None] = None):
        self.uid = uid
        self.phase = 0
        self.is_leader = False
        
        self.inbox: Dict[Port, List[Message]] = {Port.LEFT: [], Port.RIGHT: []}
        self.outbox: List[Tuple[Port, Message]] = []
        self.replies_received = 0
        
        self.log = log_func if log_func else lambda msg: None

    def start_phase(self):
        hop_limit = 2 ** self.phase
        self.log(f"Node {self.uid} starts phase {self.phase}. Sending token to left and right for {hop_limit} steps.")
        
        msg = Message(origin_uid=self.uid, direction=Direction.OUTBOUND, hop_count=hop_limit)
        self.outbox.append((Port.LEFT, msg))
        self.outbox.append((Port.RIGHT, msg))
        self.replies_received = 0

    def step(self):
        messages_to_process = []
        for port, msgs in self.inbox.items():
            for msg in msgs:
                messages_to_process.append((port, msg))
            self.inbox[port].clear()

        for incoming_port, msg in messages_to_process:
            self._process_message(msg, incoming_port)

    def _process_message(self, msg: Message, received_from: Port):
        if msg.direction == Direction.OUTBOUND:
            if msg.origin_uid > self.uid:
                if msg.hop_count > 1:
                    self.log(f"Node {self.uid} sends token {msg.origin_uid} forward (hop={msg.hop_count-1}).")
                    forward_msg = Message(msg.origin_uid, Direction.OUTBOUND, msg.hop_count - 1)
                    self.outbox.append((received_from.opposite(), forward_msg))
                else:
                    self.log(f"Node {self.uid} returns token {msg.origin_uid} back (INBOUND).")
                    reply_msg = Message(msg.origin_uid, Direction.INBOUND, 1)
                    self.outbox.append((received_from, reply_msg))
            elif msg.origin_uid == self.uid:
                self.log(f"Node {self.uid} received its token back. Became a leader.")
                self.is_leader = True
            else:
                self.log(f"Node {self.uid} eliminated token {msg.origin_uid}.")

        elif msg.direction == Direction.INBOUND:
            if msg.origin_uid != self.uid:
                self.outbox.append((received_from.opposite(), msg))
            else:
                self.replies_received += 1
                self.log(f"Node {self.uid} received an approval ({self.replies_received}/2).")
                if self.replies_received == 2:
                    self.phase += 1
                    self.start_phase()

class RingSimulator:
    def __init__(self, num_nodes: int, verbose: bool = False):
        self.verbose = verbose
        uids = random.sample(range(1, num_nodes * 10), num_nodes)
        self.nodes = [Node(uid, self._log) for uid in uids]
        
        self.total_messages_sent = 0
        self.rounds_passed = 0

    def _log(self, message: str):
        if self.verbose:
            print(f"[Round {self.rounds_passed}] {message}")

    def run(self) -> Tuple[int, int, int]:
        n = len(self.nodes)
        
        if self.verbose:
            print(f"Start of the simulation. Node ids: {[node.uid for node in self.nodes]}.")

        for node in self.nodes:
            node.start_phase()

        while True:
            self.rounds_passed += 1
            messages_in_transit = []

            for i, node in enumerate(self.nodes):
                while node.outbox:
                    target_port, msg = node.outbox.pop(0)
                    self.total_messages_sent += 1
                    
                    if target_port == Port.LEFT:
                        neighbor_idx = (i - 1) % n
                        arrival_port = Port.RIGHT
                    else:
                        neighbor_idx = (i + 1) % n
                        arrival_port = Port.LEFT
                        
                    messages_in_transit.append((neighbor_idx, arrival_port, msg))

            for neighbor_idx, arrival_port, msg in messages_in_transit:
                self.nodes[neighbor_idx].inbox[arrival_port].append(msg)

            for node in self.nodes:
                node.step()
                if node.is_leader:
                    if self.verbose:
                        print(f"The end of the simulation. Winner is {node.uid}.")
                    return node.uid, self.rounds_passed, self.total_messages_sent

            if self.rounds_passed > n * 20:
                raise RuntimeError("Simulation timeout.")


def run_experiments_and_plot():
    print("Start the series of experiments...")
    node_counts = list(range(10, 201, 10))
    avg_messages = []
    
    runs_per_n = 5
    for n in node_counts:
        msgs_runs = []
        for _ in range(runs_per_n):
            sim = RingSimulator(n, verbose=False)
            _, _, total_msgs = sim.run()
            msgs_runs.append(total_msgs)
        
        mean_msgs = int(np.mean(msgs_runs))
        avg_messages.append(mean_msgs)
        print(f"N={n}: Average number of messages: {mean_msgs}")

    theoretical_upper_bound = [8 * n * (math.ceil(math.log2(n)) + 1) for n in node_counts]

    plt.figure(figsize=(10, 6))
    plt.plot(node_counts, avg_messages, label='Empirical number of messages', marker='o', linewidth=2)
    plt.plot(node_counts, theoretical_upper_bound, label=r'Theoretical limit $8n(\lceil \log_2 n \rceil + 1)$', linestyle='--', color='red')
    
    plt.title('Dependence of the number of messages on the number of nodes (HS algorithm)')
    plt.xlabel('Number of nodes (n)')
    plt.ylabel('Total number of messages')
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    print("Single run...")
    sim = RingSimulator(num_nodes=5, verbose=True)
    winner_uid, total_rounds, total_msgs = sim.run()
    print(f"Winner: {winner_uid}, total rounds: {total_rounds}, number of messages: {total_msgs}\n")

    print("Complexity analysis...")
    run_experiments_and_plot()