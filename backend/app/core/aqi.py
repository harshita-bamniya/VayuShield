"""CPCB AQI computation helpers — shared by ingestion, attribution, and forecasting."""


def pm25_to_aqi(pm25: float) -> int:
    """Convert PM2.5 concentration (µg/m³, 24-hr average) to CPCB AQI sub-index.

    Breakpoints from CPCB AQI Technical Document (2014, revised 2023).
    """
    breakpoints = [
        (0, 30, 0, 50),
        (30, 60, 51, 100),
        (60, 90, 101, 200),
        (90, 120, 201, 300),
        (120, 250, 301, 400),
        (250, 500, 401, 500),
    ]
    for c_lo, c_hi, i_lo, i_hi in breakpoints:
        if c_lo <= pm25 <= c_hi:
            return round(i_lo + (i_hi - i_lo) * (pm25 - c_lo) / (c_hi - c_lo))
    return 500 if pm25 > 500 else 0


def compute_aqi(pm25: float | None, pm10: float | None = None) -> int | None:
    """Return the dominant AQI value from available pollutant concentrations."""
    sub_indices = []
    if pm25 is not None and pm25 >= 0:
        sub_indices.append(pm25_to_aqi(pm25))
    if pm10 is not None and pm10 >= 0:
        # PM10 breakpoints (µg/m³): 0-50→0-50, 50-100→51-100, 100-250→101-200, etc.
        pm10_bp = [
            (0, 50, 0, 50),
            (50, 100, 51, 100),
            (100, 250, 101, 200),
            (250, 350, 201, 300),
            (350, 430, 301, 400),
            (430, 600, 401, 500),
        ]
        for c_lo, c_hi, i_lo, i_hi in pm10_bp:
            if c_lo <= pm10 <= c_hi:
                sub_indices.append(round(i_lo + (i_hi - i_lo) * (pm10 - c_lo) / (c_hi - c_lo)))
                break
    return max(sub_indices) if sub_indices else None


AQI_CATEGORY = [
    (0, 50, "Good"),
    (51, 100, "Satisfactory"),
    (101, 200, "Moderate"),
    (201, 300, "Poor"),
    (301, 400, "Very Poor"),
    (401, 500, "Severe"),
]


def aqi_category(aqi: int) -> str:
    for lo, hi, label in AQI_CATEGORY:
        if lo <= aqi <= hi:
            return label
    return "Severe"
