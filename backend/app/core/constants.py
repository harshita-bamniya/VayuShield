from dataclasses import dataclass


@dataclass(frozen=True)
class AQIBand:
    label: str
    min: int
    max: int
    color: str
    pattern: str  # for color-blind-safe redundancy


AQI_BANDS = [
    AQIBand("Good", 0, 50, "#00B050", "circle"),
    AQIBand("Satisfactory", 51, 100, "#92D050", "square"),
    AQIBand("Moderate", 101, 200, "#FFFF00", "triangle"),
    AQIBand("Poor", 201, 300, "#FF0000", "diamond"),
    AQIBand("Very Poor", 301, 400, "#C00000", "cross"),
    AQIBand("Severe", 401, 500, "#7030A0", "star"),
]

SUPPORTED_LANGUAGES = ["hi", "mr", "kn", "ta", "bn", "gu"]

SOURCE_CATEGORIES = ["vehicular", "industrial", "construction", "agricultural"]

STALENESS_THRESHOLD_HOURS = 2
ADVISORY_LEAD_TIME_HOURS = 18
FORECAST_HORIZON_HOURS = 72
GRID_RESOLUTION_KM = 1
