from meshtastic.protobuf import mesh_pb2

mp = mesh_pb2.MeshPacket()
setattr(mp, 'from', 123)
print(f"From via getattr: {getattr(mp, 'from')}")
try:
    print(mp.from_)
except AttributeError:
    print("mp.from_ does not exist")
