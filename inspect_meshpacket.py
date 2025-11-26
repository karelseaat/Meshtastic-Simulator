from meshtastic.protobuf import mesh_pb2

print("Fields in MeshPacket:")
for field in mesh_pb2.MeshPacket.DESCRIPTOR.fields:
    print(f"  {field.name}")
