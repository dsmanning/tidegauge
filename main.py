from tidegauge.main import run_main


TRIGGER_PIN_ID = 6
ECHO_PIN_ID = 5
CALIBRATION_PATH = "/calibration.json"
MEASUREMENT_INTERVAL_S = 60
MAX_SEND_ATTEMPTS = 3


def create_lora_client(
    *,
    driver_factory=None,
    credentials_loader=None,
):
    """Return configured LoRaWAN client for the board."""
    from tidegauge.adapters.lorawan_client import LoRaWanClientAdapter

    if driver_factory is None:
        from tidegauge.adapters.feather_lorawan import create_feather_lorawan_driver

        driver_factory = create_feather_lorawan_driver

    if credentials_loader is None:
        from tidegauge.ttn_credentials import load_ttn_credentials

        credentials_loader = load_ttn_credentials

    credentials = credentials_loader()
    return LoRaWanClientAdapter(driver=driver_factory(credentials=credentials))


def main() -> int:
    import board
    import digitalio
    import time
    from tidegauge.adapters.circuitpython_compat import (
        CircuitPythonTimeModule,
        create_machine_compat_module,
    )

    machine_module = create_machine_compat_module(
        board_module=board,
        digitalio_module=digitalio,
    )
    time_module = CircuitPythonTimeModule(time_module=time)

    return run_main(
        machine_module=machine_module,
        time_module=time_module,
        lora_client=create_lora_client(),
        trigger_pin_id=TRIGGER_PIN_ID,
        echo_pin_id=ECHO_PIN_ID,
        calibration_path=CALIBRATION_PATH,
        measurement_interval_s=MEASUREMENT_INTERVAL_S,
        max_send_attempts=MAX_SEND_ATTEMPTS,
    )


if __name__ == "__main__":
    main()
