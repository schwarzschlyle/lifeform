from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Call(StrEnum):
    SILENT = "silent"
    ALARM = "alarm_call"
    FOOD = "food_call"
    MATING = "mating_call"
    CONTACT = "contact_call"
    DISTRESS = "distress_call"
    WARNING_GROWL = "warning_growl"
    TERRITORIAL = "territorial_call"


@dataclass(frozen=True, slots=True)
class CallSpec:
    call: Call
    description: str
    level_db: float
    min_vocal_capacity: float
    adults_only: bool
    heard_as: str


CALL_SPECS: dict[Call, CallSpec] = {
    spec.call: spec
    for spec in (
        CallSpec(Call.SILENT, "makes no sound", 0.0, 0.0, False, ""),
        CallSpec(Call.ALARM, "warns its kind that danger is near", 70.0, 0.2, False, "an alarm call"),
        CallSpec(Call.FOOD, "tells its kind it has found food", 60.0, 0.2, False, "a food call"),
        CallSpec(Call.MATING, "advertises that it is ready to mate", 75.0, 0.2, True, "a mating call"),
        CallSpec(
            Call.CONTACT, "calls softly to keep in touch with its group or young", 50.0, 0.0, False, "a contact call"
        ),
        CallSpec(Call.DISTRESS, "screams for help", 80.0, 0.0, False, "a distress scream"),
        CallSpec(Call.WARNING_GROWL, "growls a warning at a threat", 65.0, 0.2, False, "a warning growl"),
        CallSpec(Call.TERRITORIAL, "announces that this is its home area", 70.0, 0.4, True, "a territorial call"),
    )
}

CALL_ORDER: tuple[Call, ...] = tuple(Call)
CALL_CODE: dict[Call, int] = {call: index for index, call in enumerate(CALL_ORDER)}
