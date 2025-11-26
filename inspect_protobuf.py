from meshtastic.protobuf import mesh_pb2

print("Fields in MyNodeInfo:")
for field in mesh_pb2.MyNodeInfo.DESCRIPTOR.fields:
    print(f"  {field.name}")
