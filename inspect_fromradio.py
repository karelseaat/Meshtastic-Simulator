from meshtastic.protobuf import mesh_pb2

print("Fields in FromRadio:")
for field in mesh_pb2.FromRadio.DESCRIPTOR.fields:
    print(f"  {field.name}")
