import socket
import threading
import time
from meshtastic.protobuf import mesh_pb2, config_pb2, module_config_pb2, channel_pb2, portnums_pb2

START1 = 0x94
START2 = 0xC3

class TCPServer:
    def __init__(self, simulation, port=4403):
        self.simulation = simulation
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', port))
        self.server_socket.listen(1)
        self.running = True
        self.clients = []
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        print(f"Server listening on port {self.port}")

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                print(f"Client connected from {addr}")
                client = ClientHandler(conn, self.simulation)
                self.clients.append(client)
                client.start()
            except OSError:
                break

    def stop(self):
        self.running = False
        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        self.server_socket.close()

class ClientHandler(threading.Thread):
    def __init__(self, conn, simulation):
        super().__init__(daemon=True)
        self.conn = conn
        self.simulation = simulation
        self.connected = True

    def run(self):
        try:
            self.send_handshake()
            buffer = b''
            while self.connected:
                data = self.conn.recv(1024)
                if not data:
                    break
                buffer += data
                
                while len(buffer) >= 4:
                    # Check header
                    if buffer[0] != START1 or buffer[1] != START2:
                        # Skip one byte if invalid header (resync)
                        buffer = buffer[1:]
                        continue
                    
                    length = (buffer[2] << 8) | buffer[3]
                    if len(buffer) < 4 + length:
                        break # Wait for more data
                    
                    packet_data = buffer[4:4+length]
                    buffer = buffer[4+length:]
                    self.handle_packet(packet_data)
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            print("Client disconnected")
            self.conn.close()

    def send_packet(self, protobuf_obj):
        data = protobuf_obj.SerializeToString()
        length = len(data)
        header = bytes([START1, START2, (length >> 8) & 0xFF, length & 0xFF])
        try:
            self.conn.sendall(header + data)
            print(f"  Sent FromRadio: {protobuf_obj.WhichOneof('payload_variant')}")
        except Exception as e:
            print(f"  Failed to send packet: {e}")
            self.connected = False

    def send_handshake(self):
        host = self.simulation.host_node
        if not host:
            return

        print("Sending handshake...")

        # 1. Send MyInfo
        fr = mesh_pb2.FromRadio()
        fr.my_info.CopyFrom(host.get_my_node_info())
        self.send_packet(fr)
        time.sleep(0.1)

        # 2. Send NodeInfo for self
        fr = mesh_pb2.FromRadio()
        fr.node_info.CopyFrom(host.get_node_info())
        self.send_packet(fr)
        time.sleep(0.1)
        
        # 3. Send NodeInfo for peers
        for peer in self.simulation.get_peers():
            fr = mesh_pb2.FromRadio()
            fr.node_info.CopyFrom(peer.get_node_info())
            self.send_packet(fr)
            time.sleep(0.05)
        
        # 4. Send Config Complete to signal end of initial sync
        fr = mesh_pb2.FromRadio()
        fr.config_complete_id = 42 
        self.send_packet(fr)
        
        print("Handshake complete.")

    def handle_packet(self, data):
        tr = mesh_pb2.ToRadio()
        try:
            tr.ParseFromString(data)
            print(f"Received ToRadio: {tr.WhichOneof('payload_variant')}")
            
            if tr.HasField("packet"):
                 mesh_packet = tr.packet
                 # 'to' field is the destination, 'from' is reserved so it becomes 'from_'
                 print(f"  Received Mesh Packet. Dest: {mesh_packet.to}, Port: {mesh_packet.decoded.portnum}")
                 
                 # Check if it's a text message
                 if mesh_packet.decoded.portnum == portnums_pb2.TEXT_MESSAGE_APP:
                     try:
                         message_text = mesh_packet.decoded.payload.decode('utf-8')
                         print(f"    Text Message: {message_text}")
                         
                         # Handle the message if it's for one of our simulated nodes
                         # 'from' is a reserved keyword, so we use getattr
                         sender_id = getattr(mesh_packet, 'from')
                         self.process_text_message(mesh_packet.to, sender_id, message_text)
                     except Exception as e:
                         print(f"    Error decoding text payload: {e}")

            elif tr.HasField("want_config_id"):
                config_id = tr.want_config_id
                print(f"  Client requested config: {config_id}")
                self.send_config(config_id)
        except Exception as e:
            print(f"Error parsing ToRadio: {e}")
            import traceback
            traceback.print_exc()

    def process_text_message(self, dest_node_id, from_node_id, text):
        # Find the target node
        target_node = None
        for node in self.simulation.nodes:
            if node.node_id == dest_node_id:
                target_node = node
                break
        
        # Also handle broadcast (0xFFFFFFFF) - maybe pick a random node to reply?
        # For now, only handle direct messages to simulated nodes
        if target_node and target_node != self.simulation.host_node:
            # Run in a separate thread to not block the receive loop while Ollama thinks
            threading.Thread(target=self._generate_and_send_reply, args=(target_node, from_node_id, text), daemon=True).start()

    def _generate_and_send_reply(self, target_node, original_sender_id, text):
        response_text = target_node.handle_message(text)
        
        if response_text:
            # Create a response MeshPacket
            mp = mesh_pb2.MeshPacket()
            # 'from' is a reserved keyword
            setattr(mp, 'from', target_node.node_id)
            mp.to = original_sender_id
            mp.id = int(time.time()) # Random packet ID
            mp.hop_limit = 3
            
            # Set payload
            mp.decoded.portnum = portnums_pb2.TEXT_MESSAGE_APP
            mp.decoded.payload = response_text.encode('utf-8')
            
            # Wrap in FromRadio
            fr = mesh_pb2.FromRadio()
            fr.packet.CopyFrom(mp)
            
            print(f"  Sending Reply from {target_node.short_name}: {response_text}")
            self.send_packet(fr)

    def send_config(self, config_id):
        # The client sends a random ID and expects us to echo it back in the config responses
        # so it knows which request we are answering.
        
        # 1. Device Config
        fr = mesh_pb2.FromRadio()
        fr.config.device.role = config_pb2.Config.DeviceConfig.Role.CLIENT
        fr.config.device.serial_enabled = True
        fr.config.device.node_info_broadcast_secs = 300
        self.send_packet(fr)
        print("    Sent Device Config")
        time.sleep(0.05)

        # 2. Position Config
        fr = mesh_pb2.FromRadio()
        fr.config.position.gps_enabled = True
        fr.config.position.gps_update_interval = 30
        self.send_packet(fr)
        print("    Sent Position Config")
        time.sleep(0.05)

        # 3. Power Config
        fr = mesh_pb2.FromRadio()
        fr.config.power.is_power_saving = False
        self.send_packet(fr)
        print("    Sent Power Config")
        time.sleep(0.05)

        # 4. Network Config
        fr = mesh_pb2.FromRadio()
        fr.config.network.wifi_enabled = False
        self.send_packet(fr)
        print("    Sent Network Config")
        time.sleep(0.05)

        # 5. Display Config
        fr = mesh_pb2.FromRadio()
        fr.config.display.screen_on_secs = 30
        self.send_packet(fr)
        print("    Sent Display Config")
        time.sleep(0.05)

        # 6. LoRa Config
        fr = mesh_pb2.FromRadio()
        fr.config.lora.use_preset = True
        fr.config.lora.modem_preset = config_pb2.Config.LoRaConfig.ModemPreset.LONG_FAST
        fr.config.lora.region = config_pb2.Config.LoRaConfig.RegionCode.US
        fr.config.lora.hop_limit = 3
        self.send_packet(fr)
        print("    Sent LoRa Config")
        time.sleep(0.05)

        # 7. Bluetooth Config
        fr = mesh_pb2.FromRadio()
        fr.config.bluetooth.enabled = True
        self.send_packet(fr)
        print("    Sent Bluetooth Config")
        time.sleep(0.05)

        # 8. Module Configs (MQTT, etc)
        fr = mesh_pb2.FromRadio()
        fr.moduleConfig.mqtt.enabled = False
        self.send_packet(fr)
        print("    Sent Module Config")
        time.sleep(0.05)

        # 9. Channels (Send a default primary channel)
        fr = mesh_pb2.FromRadio()
        c = fr.channel
        c.index = 0
        c.role = channel_pb2.Channel.Role.PRIMARY
        c.settings.psk = b'\x01' # Default PSK
        c.settings.name = "LongFast"
        self.send_packet(fr)
        print("    Sent Channel Config")
        time.sleep(0.05)

        # 10. Config Complete (Echo the ID back)
        fr = mesh_pb2.FromRadio()
        fr.config_complete_id = config_id
        self.send_packet(fr)
        print(f"Sent config responses for ID {config_id}")