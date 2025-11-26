import meshtastic.protobuf.mesh_pb2 as mesh_pb2
import meshtastic.protobuf.telemetry_pb2 as telemetry_pb2
import meshtastic.protobuf.portnums_pb2 as portnums_pb2

print("Imports successful")
print(f"Mesh Packet type: {type(mesh_pb2.MeshPacket())}")
