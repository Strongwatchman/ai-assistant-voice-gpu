import sounddevice as sd

print("=== INPUT DEVICES ===")
for i, device in enumerate(sd.query_devices()):
    if device['max_input_channels'] > 0:
        print(f"[{i}] {device['name']} (inputs: {device['max_input_channels']})")

print("\n=== OUTPUT DEVICES ===")
for i, device in enumerate(sd.query_devices()):
    if device['max_output_channels'] > 0:
        print(f"[{i}] {device['name']} (outputs: {device['max_output_channels']})")
