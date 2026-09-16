import math

from tidegauge.measurement_quality import (
    MeasurementStatus,
    assess_distance,
    assess_tide_change,
    combine_statuses,
)


def test_distance_rejects_nonfinite_values_and_physical_limits() -> None:
    assert assess_distance(math.nan, minimum_m=0.2, maximum_m=4.0).status is MeasurementStatus.INVALID
    assert assess_distance(0.1, minimum_m=0.2, maximum_m=4.0).status is MeasurementStatus.INVALID
    assert assess_distance(4.1, minimum_m=0.2, maximum_m=4.0).status is MeasurementStatus.INVALID


def test_distance_within_configured_tube_limits_is_valid() -> None:
    result = assess_distance(1.5, minimum_m=0.2, maximum_m=4.0)

    assert result.status is MeasurementStatus.VALID
    assert result.value_m == 1.5


def test_tide_change_marks_a_noise_spike_suspect() -> None:
    result = assess_tide_change(previous_m=1.0, current_m=2.0, elapsed_s=60.0, maximum_rate_m_per_s=0.01)

    assert result.status is MeasurementStatus.SUSPECT


def test_tide_change_allows_a_configured_rapid_change() -> None:
    result = assess_tide_change(previous_m=1.0, current_m=1.5, elapsed_s=60.0, maximum_rate_m_per_s=0.01)

    assert result.status is MeasurementStatus.VALID


def test_invalid_status_takes_precedence_when_statuses_are_combined() -> None:
    assert combine_statuses(MeasurementStatus.SUSPECT, MeasurementStatus.INVALID) is MeasurementStatus.INVALID
    assert combine_statuses(MeasurementStatus.VALID, MeasurementStatus.SUSPECT) is MeasurementStatus.SUSPECT
