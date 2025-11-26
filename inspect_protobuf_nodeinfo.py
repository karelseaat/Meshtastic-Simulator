from meshtastic.protobuf import mesh_pb2

print("Fields in NodeInfo:")
for field in mesh_pb2.NodeInfo.DESCRIPTOR.fields:
    print(f"  {field.name}")
