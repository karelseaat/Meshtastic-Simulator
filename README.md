 # Meshtastic-Simulator
A Python-based simulation tool for the Meshtastic mesh radio network.

## Overview
This project provides a simulated environment to test and experiment with various aspects of the Meshtastic mesh radio network without requiring physical hardware. The simulator creates nodes, establishes a virtual radio environment, and allows for manual packet injection and monitoring.

## Contents
- **main.py**: Entry point for the simulation. Initializes the simulation, sets up the host node, and adds peer nodes.
- **inspect_channel.py**: Inspects the Channel class defined in `meshtastic.protobuf.channel_pb2`.
- **check_imports.py**: Verifies that the required Python modules for working with Meshtastic protobuf messages are successfully imported.
- **test_from_access.py**: Tests accessing and modifying the 'from' field in a `MeshPacket` object.
- **simulator/node.py**: Defines the SimulatedNode class, which represents each node in the simulated mesh network.
- **inspect_fromradio.py**: Inspects the `FromRadio` class defined in `meshtastic.protobuf.mesh_pb2`.
- **inspect_channel_role.py**: Inspects the values of the Channel.Role enum.
- **simulator/mesh.py**: Handles the creation and management of nodes, routing calculation, and other simulation-related logic.
- **requirements.txt**: Lists the required Python packages to run this project.
- **simulator/interface.py**: Implements the TCP server for client connections and packet handling.

## Usage
To use this simulator, follow these steps:

1. Install the required Python packages by running `pip install -r requirements.txt`.
2. Run the simulation script with `python main.py` to start the simulation. The console will provide information on starting the server and connecting using the Meshtastic CLI.
3. Connect to the simulator using the provided command (shown in the console) to interact with it via a Meshtastic client.
4. Type 'help' within the connected client for a list of available commands to inspect and manipulate the simulation.
5. Press `Ctrl+C` to stop the simulation.

## Further Exploration
The provided scripts demonstrate various ways to work with the simulator, from inspecting protobuf messages to testing node behavior. Feel free to modify and extend these scripts as needed for your specific use cases or experimentation.