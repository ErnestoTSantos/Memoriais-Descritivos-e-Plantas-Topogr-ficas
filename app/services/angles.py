from __future__ import annotations

import re


def decimal_to_dms(angle_deg: float) -> str:
    angle_deg = abs(angle_deg)
    deg = int(angle_deg)
    rem = (angle_deg - deg) * 60
    minutes = int(rem)
    seconds = int(round((rem - minutes) * 60))
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        deg += 1
    return f"{deg:03d}°{minutes:02d}'{seconds:02d}\""


def parse_azimuth(value: str) -> float:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Azimute vazio.")

    normalized = cleaned.replace(",", ".")
    try:
        return float(normalized) % 360
    except ValueError:
        pass

    # Supports formats like 12°30'15", 12 30 15 or 12:30:15
    compact = (
        normalized.replace("º", " ")
        .replace("°", " ")
        .replace("'", " ")
        .replace('"', " ")
        .replace(":", " ")
    )
    parts = [p for p in re.split(r"\s+", compact) if p]
    if len(parts) not in {2, 3}:
        raise ValueError(f"Azimute invalido: '{value}'. Use decimal ou GMS (graus minutos segundos).")

    deg = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2]) if len(parts) == 3 else 0.0

    if not (0 <= minutes < 60) or not (0 <= seconds < 60):
        raise ValueError(f"Azimute invalido: '{value}'. Minutos/segundos devem estar entre 0 e 59.")

    decimal = abs(deg) + (minutes / 60.0) + (seconds / 3600.0)
    return decimal % 360
