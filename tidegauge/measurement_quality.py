"""Pure validation and confidence rules for distance measurements."""

from dataclasses import dataclass
from enum import Enum
import math


class MeasurementStatus(Enum):
    VALID = "valid"
    SUSPECT = "suspect"
    INVALID = "invalid"


@dataclass(frozen=True)
class MeasurementAssessment:
    status: MeasurementStatus
    value_m: float | None
    reason: str | None = None


def assess_distance(distance_m: float, *, minimum_m: float, maximum_m: float) -> MeasurementAssessment:
    if not math.isfinite(distance_m):
        return MeasurementAssessment(MeasurementStatus.INVALID, None, "distance is not finite")
    if not math.isfinite(minimum_m) or not math.isfinite(maximum_m) or minimum_m < 0 or minimum_m >= maximum_m:
        raise ValueError("distance limits must be finite, nonnegative, and ordered")
    if distance_m < minimum_m or distance_m > maximum_m:
        return MeasurementAssessment(MeasurementStatus.INVALID, distance_m, "distance is outside physical limits")
    return MeasurementAssessment(MeasurementStatus.VALID, distance_m)


def assess_tide_change(
    *, previous_m: float, current_m: float, elapsed_s: float, maximum_rate_m_per_s: float
) -> MeasurementAssessment:
    values = (previous_m, current_m, elapsed_s, maximum_rate_m_per_s)
    if not all(math.isfinite(value) for value in values):
        return MeasurementAssessment(MeasurementStatus.INVALID, current_m, "change inputs are not finite")
    if elapsed_s <= 0 or maximum_rate_m_per_s < 0:
        raise ValueError("elapsed_s must be positive and maximum_rate_m_per_s must be nonnegative")
    rate = abs(current_m - previous_m) / elapsed_s
    if rate > maximum_rate_m_per_s:
        return MeasurementAssessment(MeasurementStatus.SUSPECT, current_m, "tide change exceeds configured rate")
    return MeasurementAssessment(MeasurementStatus.VALID, current_m)


def combine_statuses(*statuses: MeasurementStatus) -> MeasurementStatus:
    if not statuses:
        raise ValueError("at least one measurement status is required")
    if MeasurementStatus.INVALID in statuses:
        return MeasurementStatus.INVALID
    if MeasurementStatus.SUSPECT in statuses:
        return MeasurementStatus.SUSPECT
    return MeasurementStatus.VALID
