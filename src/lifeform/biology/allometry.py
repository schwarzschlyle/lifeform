from __future__ import annotations

import math

KLEIBER_EXPONENT = 0.75
QUARTER_POWER = 0.25
SPEED_EXPONENT = 0.17
LOCOMOTION_EXPONENT = 0.68
MUSCLE_EXPONENT = 0.66
WATER_TURNOVER_EXPONENT = 0.80
CONDUCTANCE_EXPONENT = 0.5
THERMAL_INERTIA_EXPONENT = -0.33
HEALING_EXPONENT = -0.25


def kleiber(mass_kg: float, coefficient: float) -> float:
    return coefficient * math.pow(mass_kg, KLEIBER_EXPONENT)


def quarter_power(mass_kg: float, coefficient: float) -> float:
    return coefficient * math.pow(mass_kg, QUARTER_POWER)


def locomotion_cost(mass_kg: float, coefficient: float) -> float:
    return coefficient * math.pow(mass_kg, LOCOMOTION_EXPONENT)


def muscle_scale(mass_kg: float) -> float:
    return math.pow(mass_kg, MUSCLE_EXPONENT)


def water_turnover(mass_kg: float, coefficient: float) -> float:
    return coefficient * math.pow(mass_kg, WATER_TURNOVER_EXPONENT)


def thermal_conductance(mass_kg: float, coefficient: float) -> float:
    return coefficient * math.pow(mass_kg, CONDUCTANCE_EXPONENT)


def thermal_relaxation(mass_kg: float, coefficient: float) -> float:
    return min(1.0, coefficient * math.pow(mass_kg, THERMAL_INERTIA_EXPONENT))


def healing_scale(mass_kg: float) -> float:
    return math.pow(mass_kg, HEALING_EXPONENT)


def speed_scale(mass_kg: float) -> float:
    return math.pow(mass_kg, SPEED_EXPONENT)


def ontogenetic_growth(mass_kg: float, adult_mass_kg: float, coefficient: float) -> float:
    if mass_kg >= adult_mass_kg:
        return 0.0
    return coefficient * math.pow(mass_kg, KLEIBER_EXPONENT) * (1.0 - math.pow(mass_kg / adult_mass_kg, QUARTER_POWER))
