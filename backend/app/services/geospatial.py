from math import asin, cos, radians, sin, sqrt


def haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Calculate great-circle distance between two coordinates."""
    lat1, lon1, lat2, lon2 = map(
        radians,
        [latitude_a, longitude_a, latitude_b, longitude_b],
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * asin(sqrt(min(1.0, a)))
