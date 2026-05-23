from __future__ import annotations

import math
import re


def decimal_to_dms(angle_deg: float) -> str:
    """Convert a decimal degree angle to a DMS string (ddd°mm'ss").

    The input is normalised to [0, 360) so the output never shows 360°00'00",
    which is an invalid azimuth value.  Carry propagation is handled in
    seconds → minutes → degrees order before the normalisation guard.
    """
    if not math.isfinite(float(angle_deg)):
        raise ValueError("Angulo invalido: valor deve ser numerico e finito.")

    angle_deg = float(angle_deg) % 360.0
    deg = int(angle_deg)
    rem = (angle_deg - deg) * 60
    minutes = int(rem)
    seconds = int(round((rem - minutes) * 60))
    # Carry propagation: rounding can push seconds/minutes past their limit.
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        deg += 1
    # Guard: after carry, degrees must stay in [0, 360).
    # Use modulo rather than a single subtraction so multiples of 360 (e.g.
    # decimal_to_dms(720.0)) are also handled correctly.
    deg = deg % 360
    return f"{deg:03d}°{minutes:02d}'{seconds:02d}\""


def parse_azimuth(value: str) -> float:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Azimute vazio.")

    normalized = cleaned.replace(",", ".")
    try:
        decimal = float(normalized)
        if not math.isfinite(decimal):
            raise ValueError
        return decimal % 360
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
        raise ValueError(
            f"Azimute invalido: '{value}'. Use decimal ou GMS (graus minutos segundos)."
        )

    deg = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2]) if len(parts) == 3 else 0.0

    if not all(math.isfinite(v) for v in (deg, minutes, seconds)):
        raise ValueError(
            f"Azimute invalido: '{value}'. Valores devem ser numericos e finitos."
        )

    if not (0 <= minutes < 60) or not (0 <= seconds < 60):
        raise ValueError(
            f"Azimute invalido: '{value}'. Minutos/segundos devem estar entre 0 e 59."
        )

    # Preserve sign: -90°30'00" means 270.5° (not 90.5°).
    # We build the absolute DMS magnitude and then restore the sign before
    # normalising to [0, 360).
    sign = -1 if deg < 0 else 1
    decimal = sign * (abs(deg) + (minutes / 60.0) + (seconds / 3600.0))
    return decimal % 360
