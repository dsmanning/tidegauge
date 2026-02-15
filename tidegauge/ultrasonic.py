SPEED_OF_SOUND_M_PER_S = 343.0


def echo_duration_us_to_distance_m(echo_duration_us: int) -> float:
    if echo_duration_us < 0:
        raise ValueError("echo_duration_us must be >= 0")

    round_trip_time_s = echo_duration_us / 1_000_000
    return (round_trip_time_s * SPEED_OF_SOUND_M_PER_S) / 2
