try:
    import sounddevice as sd
except Exception as exc:
    print(f"sounddevice import failed: {exc}")
    raise SystemExit(1)


def main():
    devices = sd.query_devices()
    found_any = False

    for index, device in enumerate(devices):
        max_inputs = int(device.get("max_input_channels", 0))
        if max_inputs <= 0:
            continue

        found_any = True
        default_rate = device.get("default_samplerate", "unknown")
        print(
            f"[{index}] {device.get('name', 'Unknown Device')} | "
            f"inputs={max_inputs} | default_samplerate={default_rate}"
        )

    if not found_any:
        print("No input microphones were found.")


if __name__ == "__main__":
    main()
