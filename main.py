from pathlib import Path

from tidegauge.main import run_main


TRIGGER_PIN_ID = 6
ECHO_PIN_ID = 7
CALIBRATION_PATH = Path("/calibration.json")
MEASUREMENT_INTERVAL_S = 60
MAX_SEND_ATTEMPTS = 3


def create_lora_client():
    """Return configured LoRaWAN client for the board."""
    raise NotImplementedError("Wire your board-specific LoRa client here")


def main() -> int:
    import machine
    import time

    return run_main(
        machine_module=machine,
        time_module=time,
        lora_client=create_lora_client(),
        trigger_pin_id=TRIGGER_PIN_ID,
        echo_pin_id=ECHO_PIN_ID,
        calibration_path=CALIBRATION_PATH,
        measurement_interval_s=MEASUREMENT_INTERVAL_S,
        max_send_attempts=MAX_SEND_ATTEMPTS,
    )


if __name__ == "__main__":
    main()
