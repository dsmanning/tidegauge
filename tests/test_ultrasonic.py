import pytest

from tidegauge.ultrasonic import echo_duration_us_to_distance_m


def test_echo_duration_us_to_distance_m_converts_using_speed_of_sound() -> None:
    distance_m = echo_duration_us_to_distance_m(5831)
    assert distance_m == pytest.approx(1.0, rel=1e-3)


def test_echo_duration_us_to_distance_m_rejects_negative_duration() -> None:
    with pytest.raises(ValueError, match="echo_duration_us must be >= 0"):
        echo_duration_us_to_distance_m(-1)
