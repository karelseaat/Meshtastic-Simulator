import time
import random
import math
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from meshtastic.protobuf import mesh_pb2, config_pb2

class SimulatedNode:
    def __init__(self, node_id: int, short_name: str, long_name: str, lat: float, lon: float, persona: str = "You are a helpful mesh node."):
        self.node_id = node_id
        self.short_name = short_name
        self.long_name = long_name
        self.lat = lat
        self.lon = lon
        self.persona = persona
        self.last_seen = time.time() # This node's last activity
        self.snr = 10.0  # Default simulated SNR
        self.observed_peers = {} # {node_id: {"last_heard": timestamp, "snr": snr}}
        self.hops_away = 0 # Distance from host (0 if direct, >0 if multi-hop)

    def calculate_distance(self, other_node: 'SimulatedNode') -> float:
        """Calculate distance between two nodes using Haversine formula (km)."""
        R = 6371  # Radius of Earth in kilometers

        lat1_rad = math.radians(self.lat)
        lon1_rad = math.radians(self.lon)
        lat2_rad = math.radians(other_node.lat)
        lon2_rad = math.radians(other_node.lon)

        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance

    def get_node_info(self) -> mesh_pb2.NodeInfo:
        """Constructs and returns the NodeInfo protobuf for this node."""
        n = mesh_pb2.NodeInfo()
        n.num = self.node_id
        
        # User Info
        n.user.id = f"!{self.node_id:08x}"
        n.user.long_name = self.long_name
        n.user.short_name = self.short_name
        n.user.hw_model = mesh_pb2.HardwareModel.TLORA_V2
        n.user.role = config_pb2.Config.DeviceConfig.Role.CLIENT
        
        # Position Info
        n.position.latitude_i = int(self.lat * 1e7)
        n.position.longitude_i = int(self.lon * 1e7)
        n.position.altitude = 100
        n.position.time = int(time.time())
        
        # Metrics
        n.snr = self.snr 
        n.last_heard = int(self.last_seen)
        n.hops_away = self.hops_away
        
        return n

    def get_my_node_info(self) -> mesh_pb2.MyNodeInfo:
        """Returns MyNodeInfo for the initial handshake."""
        info = mesh_pb2.MyNodeInfo()
        info.my_node_num = self.node_id
        info.min_app_version = 30000
        return info

    def handle_message(self, message_text: str) -> str:
        """Generates a response using Ollama based on the node's persona."""
        if not OLLAMA_AVAILABLE:
            return "Error: Ollama library not installed."
        
        try:
            print(f"Node {self.short_name} thinking...")
            response = ollama.chat(model='llama3.2', messages=[
                {'role': 'system', 'content': self.persona + " Keep your answers short, under 100 characters if possible, like a text message."},
                {'role': 'user', 'content': message_text},
            ])
            reply = response['message']['content']
            print(f"Node {self.short_name} replied: {reply}")
            return reply
        except Exception as e:
            print(f"Ollama Error: {e}")
            return f"Error processing message: {str(e)}"
