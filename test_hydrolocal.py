"""Run with:  python -m pytest -q"""
from datetime import datetime, timedelta

import hydration as hy

D = datetime(2026, 10, 3)


def t(h, m=0):
    return D.replace(hour=h, minute=m)


def test_hot_work_matches_niosh_range():
    """NIOSH: 24-32 oz per hour (about 710-950 ml) for hot work."""
    assert hy.hourly_need_ml(70, "Hot", "Light") == 710
    assert hy.hourly_need_ml(70, "Hot", "Heavy") <= 950
    assert hy.MAX_ML_PER_HOUR <= 950


def test_hot_work_reminders_every_20_minutes():
    p = hy.shift_plan(t(8), t(12), [], 70, "Hot", "Moderate", True)
    sips = [e for e in p.events if e.label == "Sip at your station"]
    gaps = {(b.when - a.when).seconds // 60 for a, b in zip(sips, sips[1:])}
    assert gaps == {20}


def test_cool_work_stays_inside_daily_adequate_intake():
    """A cool 8-hour shift should not by itself exceed the NASEM drinks range (2.96 L)."""
    p = hy.shift_plan(t(8), t(16), [], 70, "Cool", "Moderate", True)
    need = int(p.headline["Estimated need for the whole shift"].split()[0].replace(".", "")) * 100
    assert need <= 3000


def test_everyday_target_is_inside_nasem_drinks_range_for_typical_weights():
    for kg in (63, 70, 84):
        total = kg * hy.EVERYDAY_ML_PER_KG
        assert 2160 <= total <= 2960


def test_hourly_need_scales_with_heat():
    cool = hy.hourly_need_ml(70, "Cool", "Moderate")
    hot = hy.hourly_need_ml(70, "Hot", "Moderate")
    assert hot > cool
    assert hot <= hy.MAX_ML_PER_HOUR


def test_shift_with_station_has_pre_post_and_breaks():
    p = hy.shift_plan(t(8), t(16, 30), [t(10), t(12, 30), t(14, 30)], 70, "Warm", "Moderate", True)
    labels = [e.label for e in p.events]
    assert labels[0] == "Before you clock in"
    assert labels[-1] == "After your shift"
    assert labels.count("Break top-up") == 3
    assert [e.when for e in p.events] == sorted(e.when for e in p.events)


def test_shift_without_station_uses_breaks_only():
    p = hy.shift_plan(t(8), t(16, 30), [t(10), t(12, 30), t(14, 30)], 70, "Warm", "Moderate", False)
    mid = [e for e in p.events if e.label == "Drink at your break"]
    assert len(mid) == 3
    assert all(e.ml <= hy.MAX_ML_PER_SITTING for e in mid)


def test_shift_without_station_or_breaks_warns():
    p = hy.shift_plan(t(8), t(16), [], 70, "Warm", "Moderate", False)
    assert any("no breaks" in w.lower() or "break times" in w.lower() for w in p.warnings)


def test_night_shift_crosses_midnight():
    p = hy.shift_plan(t(22), t(6), [t(2)], 70, "Warm", "Light", True)
    assert p.events[-1].when > p.events[0].when
    assert p.events[-1].when.date() == (D + timedelta(days=1)).date()


def test_everyday_has_no_reminder_in_last_two_hours():
    p = hy.everyday_plan(D, t(7), t(23), 70, 2.0)
    assert p.events and p.events[-1].when <= t(21)


def test_trek_keeps_reserve_and_warns_when_short():
    p = hy.trek_plan(t(7), 6, 1000, 70, "Hot")
    assert any("covers well under" in w for w in p.warnings)
    ok = hy.trek_plan(t(7), 3, 3000, 70, "Cool")
    assert not any("covers well under" in w for w in ok.warnings)
    total = sum(e.ml for e in ok.events if "sip" in e.label.lower())
    assert total <= 3000 * (1 - hy.TREK_RESERVE_FRACTION) + 60  # rounding slack


def test_trek_rejects_empty_input():
    assert hy.trek_plan(t(7), 0, 0, 70, "Warm").events == []


def test_ics_is_wellformed():
    p = hy.shift_plan(t(8), t(16), [t(12)], 70, "Warm", "Moderate", True)
    ics = hy.build_ics(p.events)
    assert ics.startswith("BEGIN:VCALENDAR") and ics.rstrip().endswith("END:VCALENDAR")
    assert ics.count("BEGIN:VEVENT") == len(p.events) == ics.count("END:VEVENT")
    assert "\r\n" in ics
