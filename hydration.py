"""HydroLocal - hydration planning logic.

Pure Python: no AI, no network. The NUMBERS come from this file so they are
predictable and checkable. The local AI model (see llm.py) only writes the
friendly explanation around them.

IMPORTANT: every constant below is a rough rule of thumb chosen for a hobby
project. They are NOT medical advice and have not been clinically validated.
Adjust them freely, and check them against a trusted source before relying
on them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

# ---------------------------------------------------------------------------
# Rule-of-thumb constants (adjustable, NOT medical advice)
# ---------------------------------------------------------------------------
HEAT_ML_PER_HOUR = {"Cool": 250, "Warm": 400, "Hot": 600}   # fluid per hour of work
ACTIVITY_FACTOR = {"Light": 1.0, "Moderate": 1.15, "Heavy": 1.3}
REFERENCE_WEIGHT_KG = 70.0        # per-hour numbers are scaled around this weight
WEIGHT_FACTOR_MIN = 0.8
WEIGHT_FACTOR_MAX = 1.3
MAX_ML_PER_HOUR = 1000            # never suggest more than this per hour
MAX_ML_PER_SITTING = 600          # don't suggest gulping more than this at once
PRE_SHIFT_ML = 400                # a drink before the shift / trek starts
POST_SHIFT_ML = 300               # a drink after the shift ends
EVERYDAY_ML_PER_KG = 30           # rough everyday daily total, per kg body weight
TREK_RESERVE_FRACTION = 0.20      # keep this share of carried water in reserve
TICK_MINUTES_SHIFT = 30           # reminder spacing when water is at the station
TICK_MINUTES_TREK = 20            # sip spacing on a trek


@dataclass
class DrinkEvent:
    when: datetime
    label: str
    ml: int


@dataclass
class Plan:
    mode: str
    events: List[DrinkEvent] = field(default_factory=list)
    headline: dict = field(default_factory=dict)   # label -> display value
    warnings: List[str] = field(default_factory=list)

    def summary_text(self) -> str:
        """Plain-text summary handed to the local model for its explanation."""
        lines = [f"Mode: {self.mode}"]
        lines += [f"{k}: {v}" for k, v in self.headline.items()]
        lines.append("Schedule:")
        lines += [f"  {e.when:%H:%M} - {e.ml} ml - {e.label}" for e in self.events]
        if self.warnings:
            lines.append("Warnings: " + " | ".join(self.warnings))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def round_to(value: float, step: int) -> int:
    """Round to the nearest `step`, never below `step`."""
    return max(step, int(round(value / step)) * step)


def hourly_need_ml(weight_kg: float, heat: str, activity: str) -> int:
    """Rule-of-thumb fluid per working hour, scaled by body weight."""
    factor = min(max(weight_kg / REFERENCE_WEIGHT_KG, WEIGHT_FACTOR_MIN), WEIGHT_FACTOR_MAX)
    raw = HEAT_ML_PER_HOUR[heat] * ACTIVITY_FACTOR[activity] * factor
    return min(round_to(raw, 10), MAX_ML_PER_HOUR)


# ---------------------------------------------------------------------------
# Mode 1: shift at work (the main use case)
# ---------------------------------------------------------------------------
def shift_plan(
    start: datetime,
    end: datetime,
    breaks: List[datetime],
    weight_kg: float,
    heat: str,
    activity: str,
    water_at_station: bool,
) -> Plan:
    if end <= start:               # night shift that crosses midnight
        end += timedelta(days=1)
    breaks = sorted(b if b >= start else b + timedelta(days=1) for b in breaks)
    breaks = [b for b in breaks if start < b < end]

    hours = (end - start).total_seconds() / 3600
    hourly = hourly_need_ml(weight_kg, heat, activity)
    need = int(round(hourly * hours, -1))

    plan = Plan(mode="Shift at work")
    plan.events.append(DrinkEvent(start - timedelta(minutes=30), "Before you clock in", PRE_SHIFT_ML))

    if water_at_station:
        tick = round_to(hourly * TICK_MINUTES_SHIFT / 60, 50)
        times = []
        t = start + timedelta(minutes=TICK_MINUTES_SHIFT)
        while t < end:
            times.append(t)
            t += timedelta(minutes=TICK_MINUTES_SHIFT)
        # snap reminders that fall near a break onto the break itself
        times = [x for x in times if all(abs((x - b).total_seconds()) > 15 * 60 for b in breaks)]
        for x in times:
            plan.events.append(DrinkEvent(x, "Sip at your station", tick))
        for b in breaks:
            plan.events.append(DrinkEvent(b, "Break top-up", tick))
    else:
        if not breaks:
            plan.warnings.append(
                "You said water is not at your station and entered no breaks, "
                "so there are no drinking times to plan. Add your break times."
            )
        else:
            per_break = round_to(min(need / len(breaks), MAX_ML_PER_SITTING), 50)
            for b in breaks:
                plan.events.append(DrinkEvent(b, "Drink at your break", per_break))
            if per_break * len(breaks) < need * 0.85:
                plan.warnings.append(
                    "Your breaks alone can't safely cover the estimated need for this "
                    "shift. If you can, ask your supervisor about keeping water nearby."
                )

    plan.events.append(DrinkEvent(end, "After your shift", POST_SHIFT_ML))
    plan.events.sort(key=lambda e: e.when)

    plan.headline = {
        "Estimated need per working hour": f"{hourly} ml",
        "Estimated need for the whole shift": f"{need / 1000:.1f} L",
        "Shift length": f"{hours:.1f} h",
    }
    if heat == "Hot":
        plan.warnings.append("Hot work: also follow your site's own heat-safety rules and break policy.")
    return plan


# ---------------------------------------------------------------------------
# Mode 2: everyday reminders (for people who forget to drink)
# ---------------------------------------------------------------------------
def everyday_plan(
    day: datetime,
    wake: datetime,
    sleep: datetime,
    weight_kg: float,
    every_hours: float,
) -> Plan:
    if sleep <= wake:
        sleep += timedelta(days=1)
    daily = int(round(weight_kg * EVERYDAY_ML_PER_KG, -2))
    # no reminders in the last 2 hours before sleep
    last = sleep - timedelta(hours=2)
    times = []
    t = wake + timedelta(minutes=30)
    while t <= last:
        times.append(t)
        t += timedelta(hours=every_hours)
    plan = Plan(mode="Everyday reminders")
    if not times:
        plan.warnings.append("Your waking hours are too short to place reminders.")
        return plan
    per = round_to(daily / len(times), 50)
    for x in times:
        plan.events.append(DrinkEvent(x, "Time for some water", per))
    plan.headline = {
        "Rough daily total": f"{daily / 1000:.1f} L",
        "Reminders": f"{len(times)} (every {every_hours:g} h)",
        "Per reminder": f"{per} ml",
    }
    plan.warnings.append(
        "The daily total is a rough rule of thumb. Food and other drinks also contribute, "
        "and individual needs vary."
    )
    return plan


# ---------------------------------------------------------------------------
# Mode 3: trek pacing (don't drink it all at the start)
# ---------------------------------------------------------------------------
def trek_plan(
    start: datetime,
    hours: float,
    carried_ml: int,
    weight_kg: float,
    heat: str,
    activity: str = "Heavy",
) -> Plan:
    plan = Plan(mode="Trek pacing")
    if hours <= 0 or carried_ml <= 0:
        plan.warnings.append("Enter a trek length and the amount of water you carry.")
        return plan
    reserve = int(carried_ml * TREK_RESERVE_FRACTION)
    usable = carried_ml - reserve
    per_hour = usable / hours
    sip = round_to(per_hour * TICK_MINUTES_TREK / 60, 10)

    plan.events.append(DrinkEvent(start - timedelta(minutes=20), "Drink BEFORE you set off (not from your bottle)", PRE_SHIFT_ML))
    n = int(hours * 60 // TICK_MINUTES_TREK)
    for i in range(1, n + 1):
        plan.events.append(
            DrinkEvent(start + timedelta(minutes=TICK_MINUTES_TREK * i), "Small sip - keep to the pace", sip)
        )
    need_hourly = hourly_need_ml(weight_kg, heat, activity)
    coverage = per_hour / need_hourly
    plan.headline = {
        "Water you carry": f"{carried_ml / 1000:.1f} L",
        "Kept in reserve": f"{reserve} ml",
        "Pace": f"about {int(round(per_hour, -1))} ml per hour",
        "Compared with the rule-of-thumb need": f"about {int(round(coverage * 100))}%",
    }
    if coverage < 0.75:
        plan.warnings.append(
            "This water supply covers well under the rule-of-thumb need for this heat. "
            "Carry more, plan a refill point, and bring a way to purify water."
        )
    plan.warnings.append("Never drink untreated stream water. Boil, filter or treat it first.")
    return plan


# ---------------------------------------------------------------------------
# Calendar export (.ics) - lets any phone remind you, fully offline
# ---------------------------------------------------------------------------
def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(events: List[DrinkEvent], now: Optional[datetime] = None) -> str:
    """Return the text of an .ics file with one alarm-bearing event per drink."""
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//HydroLocal//EN", "CALSCALE:GREGORIAN"]
    for i, e in enumerate(events):
        summary = _esc(f"Drink {e.ml} ml - {e.label}")
        out += [
            "BEGIN:VEVENT",
            f"UID:hydrolocal-{e.when:%Y%m%dT%H%M%S}-{i}@local",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{e.when:%Y%m%dT%H%M%S}",
            f"DTEND:{(e.when + timedelta(minutes=5)):%Y%m%dT%H%M%S}",
            f"SUMMARY:{summary}",
            "BEGIN:VALARM",
            "TRIGGER:PT0M",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{summary}",
            "END:VALARM",
            "END:VEVENT",
        ]
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"
