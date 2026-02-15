from dataclasses import dataclass
from typing import Any

from tidegauge.adapters.hcsr04 import Hcsr04PulseReader
from tidegauge.adapters.radio import Rfm95RadioAdapter
from tidegauge.adapters.runtime import SystemClockAdapter, SystemSleepAdapter
from tidegauge.adapters.ultrasonic import UltrasonicDurationAdapter
from tidegauge.scheduler import MinuteScheduler


@dataclass(frozen=True)
class HardwareConfig:
    trigger_pin_id: int
    echo_pin_id: int
    measurement_interval_s: int = 60
    max_send_attempts: int = 3


@dataclass(frozen=True)
class RuntimeDependencies:
    sensor: Any
    radio: Any
    scheduler: MinuteScheduler
    clock: SystemClockAdapter
    sleeper: SystemSleepAdapter
    max_send_attempts: int


def build_runtime_dependencies(
    *,
    machine_module: Any,
    time_module: Any,
    lora_client: Any,
    config: HardwareConfig,
) -> RuntimeDependencies:
    trigger_pin = machine_module.Pin(config.trigger_pin_id, machine_module.Pin.OUT)
    echo_pin = machine_module.Pin(config.echo_pin_id, machine_module.Pin.IN)

    pulse_reader = Hcsr04PulseReader(
        trigger_pin=trigger_pin,
        echo_pin=echo_pin,
        time_module=time_module,
    )
    sensor = UltrasonicDurationAdapter(echo_reader=pulse_reader)
    radio = Rfm95RadioAdapter(client=lora_client)

    clock = SystemClockAdapter(time_module=time_module)
    sleeper = SystemSleepAdapter(time_module=time_module)
    scheduler = MinuteScheduler(
        now_s=clock.now_s,
        interval_s=config.measurement_interval_s,
    )

    return RuntimeDependencies(
        sensor=sensor,
        radio=radio,
        scheduler=scheduler,
        clock=clock,
        sleeper=sleeper,
        max_send_attempts=config.max_send_attempts,
    )
