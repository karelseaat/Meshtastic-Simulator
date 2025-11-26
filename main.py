import time
import random
import threading
from simulator.node import SimulatedNode
from simulator.mesh import MeshSimulation
from simulator.interface import TCPServer, ClientHandler # ClientHandler is needed to manually inject packets for processing
from meshtastic.protobuf import mesh_pb2, portnums_pb2

def main():
    # Setup Simulation
    sim = MeshSimulation()
    
    # Create Host Node (the one you connect to)
    host = SimulatedNode(node_id=0x12345678, short_name="HOST", long_name="Simulator Host", lat=40.7128, lon=-74.0060, persona="You are the host Meshtastic node.")
    sim.set_host_node(host)
    
    # Create some peers
    personas = [
        "You are a helpful assistant.",
        "You are a grumpy neighbor who complains about noise.",
        "You are a weather reporter giving forecasts.",
        "You are a pirate searching for treasure.",
        "You are an alien pretending to be human."
    ]
    
    print("Creating simulated nodes...")
    for i in range(5):
        node_id = 0x20000000 + i
        persona = personas[i % len(personas)]
        peer = SimulatedNode(
            node_id=node_id, 
            short_name=f"SIM{i}", 
            long_name=f"Sim Node {i}", 
            lat=40.7128 + (random.random() - 0.5) * 0.05, 
            lon=-74.0060 + (random.random() - 0.5) * 0.05,
            persona=persona
        )
        sim.add_node(peer)
        print(f"  Added {peer.long_name} ({peer.short_name}) at {peer.lat:.4f}, {peer.lon:.4f}")
        print(f"    Persona: {persona}")

    sim.simulate_radio_environment()
    print("Initial radio environment simulated.")

    server = TCPServer(sim)
    server.start()
    
    print("\nSimulator running. Type 'help' for commands.")
    print("You can connect using the meshtastic python CLI:")
    print("  meshtastic --host localhost --port 4403 --info")
    print("\nPress Ctrl+C to stop.")
    
    try:
        last_radio_update = time.time()
        while True:
            current_time = time.time()
            if current_time - last_radio_update > 10: 
                sim.simulate_radio_environment()
                print("Radio environment updated.")
                last_radio_update = current_time

            # Use non-blocking input for console commands
            # This is a simplification; a full CLI library would be better for complex interactions
            try:
                cmd_line = input("Simulator command ('h' for help, 'n' for nodes, 's <ID> <MSG>', or Enter): ").strip()
            except EOFError: # Handles Ctrl+D
                print("\nEOF received. Stopping simulator.")
                break

            if cmd_line.lower() in ('help', 'h'):
                print("\nCommands:")
                print("  n             - Show current state of all simulated nodes.")
                print("  s <NODE_ID> <MESSAGE> - Send a text message FROM THE HOST NODE to <NODE_ID>.")
                print("  (Enter)       - Continue simulation loop.")
                print("  Ctrl+C        - Stop simulator.")
            elif cmd_line.lower() == 'n':
                print("\n--- Current Simulated Nodes State ---")
                for node in sim.nodes:
                    print(f"Node: {node.long_name} ({node.short_name}) - ID: !{node.node_id:08x} - Lat: {node.lat:.4f}, Lon: {node.lon:.4f}")
                    print(f"  Current SNR: {node.snr:.2f} dB (for its own NodeInfo)")
                    print(f"  Hops Away from Host: {node.hops_away}")
                    if node.observed_peers:
                        print("  Observed Peers:")
                        for peer_id, info in node.observed_peers.items():
                            peer_node = next((p for p in sim.nodes if p.node_id == peer_id), None)
                            peer_name = peer_node.short_name if peer_node else f"!{peer_id:08x}"
                            print(f"    - {peer_name} (ID: !{peer_id:08x}) - SNR: {info['snr']:.2f} dB - Last Heard: {time.ctime(info['last_heard'])}")
                    else:
                        print("  No Peers Observed.")
                print("-------------------------------------")
            elif cmd_line.lower().startswith('s '):
                # Use None to split on any whitespace sequence
                parts = cmd_line.split(None, 2)
                if len(parts) >= 3:
                    try:
                        target_id_str = parts[1]
                        if target_id_str.startswith('!'):
                            target_id_str = target_id_str[1:]
                        
                        # Debug print (remove later if needed, but helpful now)
                        # print(f"Debug: Parsing ID '{target_id_str}'")
                        
                        dest_node_id = int(target_id_str, 16)

                        target_node = next((n for n in sim.nodes if n.node_id == dest_node_id), None)

                        if target_node and target_node != sim.host_node:
                            message_text = parts[2]
                            # ... (rest of logic)
                            print(f"Host injecting message to {target_node.short_name} (!{dest_node_id:08x})...")
                            
                            # Manually construct a FromRadio packet as if it was sent by a peer
                            # This is to make the ClientHandler able to process it as a reply later
                            mp = mesh_pb2.MeshPacket()
                            setattr(mp, 'from', sim.host_node.node_id) # Host is sending it
                            mp.to = dest_node_id
                            # Packet ID is uint32. Use random or mask timestamp.
                            mp.id = int(time.time()) & 0xFFFFFFFF 
                            mp.hop_limit = 3
                            mp.decoded.portnum = portnums_pb2.TEXT_MESSAGE_APP
                            mp.decoded.payload = message_text.encode('utf-8')
                            
                            tr_wrapper = mesh_pb2.ToRadio()
                            tr_wrapper.packet.CopyFrom(mp)
                            
                            if server.clients:
                                active_client_handler = server.clients[0] 
                                threading.Thread(target=active_client_handler.handle_packet, args=(tr_wrapper.SerializeToString(),), daemon=True).start()
                            else:
                                print("No active meshtastic CLI client connected to send through.")
                        else:
                            print(f"Node !{dest_node_id:08x} not found or is the Host Node itself. Cannot send message.")
                    except ValueError as e:
                        print(f"Invalid NODE_ID '{target_id_str}'. Please use hexadecimal, e.g., !12345678. Error: {e}")
                    except Exception as e:
                        print(f"Error sending message from host: {e}")
                else:
                    print("Usage: s <NODE_ID> <MESSAGE>")
            
            # small sleep if no command was entered or for between commands
            if not cmd_line:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping...")
        server.stop()

if __name__ == "__main__":
    main()