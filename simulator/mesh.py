import time
import random
import math
from typing import List, Optional
from .node import SimulatedNode

class MeshSimulation:
    def __init__(self):
        self.nodes: List[SimulatedNode] = []
        self.host_node: Optional[SimulatedNode] = None
        self.snr_threshold = -10.0 # dB, below this, node is not 'seen'
        self.max_snr = 30.0 # dB, max possible SNR at close range
        self.snr_drop_per_log_distance = 20.0 # dB per decade (factor of 10 distance increase)

    def add_node(self, node: SimulatedNode):
        self.nodes.append(node)

    def set_host_node(self, node: SimulatedNode):
        """The node that the TCP interface 'connects' to."""
        self.host_node = node
        if node not in self.nodes:
            self.nodes.append(node)
    
    def update_routing(self):
        """
        Calculates routing tables (hops and next-hop SNR) from the Host Node to all other nodes.
        Uses BFS to find shortest path.
        """
        if not self.host_node:
            return

        # 1. Reset all nodes to unreachable
        for node in self.nodes:
            if node != self.host_node:
                node.hops_away = -1 # Unreachable
                node.snr = 0.0

        # 2. BFS
        # We initialize with the host node.
        self.host_node.hops_away = 0
        self.host_node.snr = 0.0 # Host sees itself perfectly/irrelevant
        
        queue = [self.host_node] 
        visited = {self.host_node.node_id}
        
        # We need to track what the Host "sees" for each node.
        # If direct (hops=0), SNR is the direct link.
        # If indirect (hops>0), SNR is the link of the *first hop* from Host.
        
        # Direct neighbors of host
        for peer_id, metrics in self.host_node.observed_peers.items():
             peer = self._find_node_by_id(peer_id)
             if peer:
                 peer.hops_away = 0
                 peer.snr = metrics['snr']
                 visited.add(peer_id)
                 queue.append(peer)

        # Now traverse deeper (starting from the direct neighbors we just added)
        # We skip the host node (index 0) because we already processed its neighbors manually above
        current_index = 1 
        
        while current_index < len(queue):
            current_node = queue[current_index]
            current_index += 1
            
            current_hops = current_node.hops_away
            
            # Check neighbors of this node
            for peer_id in current_node.observed_peers.keys():
                if peer_id not in visited:
                    peer = self._find_node_by_id(peer_id)
                    if peer:
                        peer.hops_away = current_hops + 1
                        # For indirect nodes, the SNR reported to the host is typically
                        # the SNR of the packet arriving at the host.
                        # Which means it's the SNR of the 'root' neighbor in this branch.
                        # But for simplicity here, we might just leave the SNR as 
                        # whatever the last 'hop' link was, or copy the parent's effective SNR.
                        # Let's copy the parent's SNR as that's the link quality 'towards' this node from Host perspective.
                        peer.snr = current_node.snr 
                        
                        visited.add(peer_id)
                        queue.append(peer)

    def _find_node_by_id(self, node_id) -> Optional[SimulatedNode]:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_peers(self) -> List[SimulatedNode]:
        """Returns all nodes that are reachable by the host node (hops >= 0)."""
        if not self.host_node:
            return []
        
        reachable_nodes = []
        for node in self.nodes:
            if node != self.host_node and node.hops_away >= 0:
                reachable_nodes.append(node)
        return reachable_nodes

    def simulate_radio_environment(self):
        """
        Simulates the radio environment, updating each node's observed peers and SNRs.
        This runs for each node as a potential receiver to determine what it 'hears'.
        """
        for source_node in self.nodes:
            source_node.observed_peers = {} # Reset observed peers for this source node
            for target_node in self.nodes:
                if source_node.node_id == target_node.node_id:
                    continue # A node doesn't 'observe' itself as a peer

                distance = source_node.calculate_distance(target_node) # in km
                
                # Simplified propagation model
                # FSPL = 20*log10(d) + 20*log10(f) + 20*log10(4*pi/c)
                # Let's simplify to SNR = K - 20*log10(distance) + noise
                # Where K includes tx power, rx sensitivity, antenna gains, and frequency effects.
                # We want SNR in dB.
                if distance < 0.05: # Very close (e.g., 50m), assume max SNR
                    calculated_snr = self.max_snr + random.uniform(-1.0, 1.0)
                else:
                    snr_loss = self.snr_drop_per_log_distance * math.log10(distance)
                    calculated_snr = self.max_snr - snr_loss + random.uniform(-2.0, 2.0) # Add some random noise

                # Apply threshold and update observed peers
                if calculated_snr >= self.snr_threshold:
                    source_node.observed_peers[target_node.node_id] = {
                        "last_heard": int(time.time()),
                        "snr": calculated_snr
                    }
        
        # After simulating physical links, calculate the mesh routing
        self.update_routing()
