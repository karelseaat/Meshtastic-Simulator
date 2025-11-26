from meshtastic.protobuf import channel_pb2

print("Values in Channel.Role:")
try:
    # Try to access PRIMARY directly on Role
    print(f"PRIMARY: {channel_pb2.Channel.Role.PRIMARY}")
except AttributeError:
    print("Not on Role")

try:
    # Try to access PRIMARY directly on Channel
    print(f"PRIMARY: {channel_pb2.Channel.PRIMARY}")
except AttributeError:
    print("Not on Channel")

print("All attributes of Channel.Role:")
for x in dir(channel_pb2.Channel.Role):
   print(x)
