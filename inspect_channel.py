from meshtastic.protobuf import channel_pb2

print("Channel defined in channel_pb2?")
print(dir(channel_pb2))

print("\nAttributes of Channel:")
try:
    print(dir(channel_pb2.Channel))
    print("\nRole enum in Channel:")
    print(dir(channel_pb2.Channel.Role))
except Exception as e:
    print(e)
