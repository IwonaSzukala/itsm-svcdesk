# ai-generated: 80% - Claude Code wrote these boundary tests from the docstrings of slaclock.py; I chose to test every documented boundary and checked them with itsmlab mutants 5
"""Behaviour tests for slaclock.py: one test per boundary its docstrings promise (CI-SPEC.md P-29)."""

from datetime import datetime, timedelta

import pytest

import slaclock

MONDAY = datetime(2026, 11, 16)          # a Monday; the week runs to Sunday 2026-11-22
TUESDAY = MONDAY + timedelta(days=1)
FRIDAY = MONDAY + timedelta(days=4)
SATURDAY = MONDAY + timedelta(days=5)
SUNDAY = MONDAY + timedelta(days=6)
NEXT_MONDAY = MONDAY + timedelta(days=7)


def at(day, hour, minute=0, second=0):
    return day.replace(hour=hour, minute=minute, second=second)


# priority_of ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("impact, urgency, expected", [
    (1, 1, "P1"),
    (1, 2, "P2"), (2, 1, "P2"),
    (1, 3, "P3"), (2, 2, "P3"), (3, 1, "P3"),
    (2, 3, "P4"), (3, 2, "P4"), (3, 3, "P4"),
])
def test_priority_matrix(impact, urgency, expected):
    assert slaclock.priority_of(impact, urgency) == expected
    assert slaclock.priority_of(impact, urgency, False) == expected


@pytest.mark.parametrize("impact, urgency, expected", [
    (1, 1, "P1"),
    (1, 2, "P2"), (2, 1, "P2"),
    (1, 3, "P2"), (2, 2, "P2"), (3, 1, "P2"),
    (2, 3, "P2"), (3, 2, "P2"), (3, 3, "P2"),
])
def test_priority_vip_is_never_below_p2(impact, urgency, expected):
    assert slaclock.priority_of(impact, urgency, vip=True) == expected


def test_priority_default_is_not_vip():
    assert slaclock.priority_of(3, 3) == "P4"


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, True, False, "1", None])
def test_priority_rejects_bad_impact(bad):
    with pytest.raises(ValueError):
        slaclock.priority_of(bad, 1)


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, True, False, "1", None])
def test_priority_rejects_bad_urgency(bad):
    with pytest.raises(ValueError):
        slaclock.priority_of(1, bad)


# targets ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("priority, expected", [
    ("P1", (15, 240)), ("P2", (60, 480)), ("P3", (240, 1440)), ("P4", (480, 4320)),
])
def test_targets(priority, expected):
    assert slaclock.targets(priority) == expected


@pytest.mark.parametrize("bad", ["p1", " P1", "P1 ", "P5", "P0", "", "P"])
def test_targets_lookup_is_exact(bad):
    with pytest.raises(ValueError):
        slaclock.targets(bad)


# sla_state --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("elapsed, target, expected", [
    (0, 15, "ok"), (11, 15, "ok"), (12, 15, "warning"), (15, 15, "warning"), (16, 15, "breached"),
    (0, 100, "ok"), (74, 100, "ok"), (75, 100, "warning"), (99, 100, "warning"),
    (100, 100, "warning"), (101, 100, "breached"),
    (2, 4, "ok"), (3, 4, "warning"), (4, 4, "warning"), (5, 4, "breached"),
    (0, 1, "ok"), (1, 1, "warning"), (2, 1, "breached"),
    (1000, 240, "breached"),
    (101, 135, "ok"), (102, 135, "warning"),     # 75 % of 135 is 101.25: no rounding either way
])
def test_sla_state(elapsed, target, expected):
    assert slaclock.sla_state(elapsed, target) == expected


@pytest.mark.parametrize("elapsed, target", [(-1, 15), (0, 0), (5, 0), (5, -1), (-1, -1)])
def test_sla_state_rejects_bad_input(elapsed, target):
    with pytest.raises(ValueError):
        slaclock.sla_state(elapsed, target)


# is_business_time -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("moment, expected", [
    (at(MONDAY, 8, 0), True),
    (at(MONDAY, 7, 59), False),
    (at(MONDAY, 7, 59, 59), False),
    (at(MONDAY, 15, 59), True),
    (at(MONDAY, 15, 59, 59), True),
    (at(MONDAY, 16, 0), False),
    (at(MONDAY, 12, 0), True),
    (at(MONDAY, 8, 1), True),
    (at(MONDAY, 16, 1), False),
    (at(MONDAY, 16, 30), False),
    (at(MONDAY, 0, 0), False),
    (at(MONDAY, 23, 59), False),
    (at(TUESDAY, 9, 30), True),
    (at(FRIDAY, 8, 0), True),
    (at(FRIDAY, 15, 59), True),
    (at(FRIDAY, 16, 0), False),
    (at(SATURDAY, 10, 0), False),
    (at(SATURDAY, 8, 0), False),
    (at(SUNDAY, 12, 0), False),
])
def test_is_business_time(moment, expected):
    assert slaclock.is_business_time(moment) is expected


# add_business_minutes ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("start, minutes, expected", [
    (at(MONDAY, 9, 0), 0, at(MONDAY, 9, 0)),
    (at(MONDAY, 8, 0), 0, at(MONDAY, 8, 0)),
    (at(MONDAY, 7, 0), 0, at(MONDAY, 8, 0)),
    (at(MONDAY, 16, 0), 0, at(TUESDAY, 8, 0)),
    (at(MONDAY, 20, 0), 0, at(TUESDAY, 8, 0)),
    (at(SATURDAY, 10, 0), 0, at(NEXT_MONDAY, 8, 0)),
    (at(MONDAY, 9, 0), 1, at(MONDAY, 9, 1)),
    (at(MONDAY, 9, 0), 30, at(MONDAY, 9, 30)),
    (at(MONDAY, 7, 0), 30, at(MONDAY, 8, 30)),
    (at(MONDAY, 15, 0), 60, at(MONDAY, 16, 0)),
    (at(MONDAY, 15, 0), 59, at(MONDAY, 15, 59)),
    (at(MONDAY, 15, 0), 61, at(TUESDAY, 8, 1)),
    (at(MONDAY, 15, 59), 1, at(MONDAY, 16, 0)),
    (at(MONDAY, 15, 59), 2, at(TUESDAY, 8, 1)),
    (at(MONDAY, 8, 0), 480, at(MONDAY, 16, 0)),
    (at(MONDAY, 8, 0), 481, at(TUESDAY, 8, 1)),
    (at(MONDAY, 8, 0), 960, at(TUESDAY, 16, 0)),
    (at(MONDAY, 8, 0), 961, at(MONDAY + timedelta(days=2), 8, 1)),
    (at(FRIDAY, 15, 30), 30, at(FRIDAY, 16, 0)),
    (at(FRIDAY, 15, 30), 60, at(NEXT_MONDAY, 8, 30)),
    (at(FRIDAY, 18, 0), 15, at(NEXT_MONDAY, 8, 15)),
    (at(SUNDAY, 23, 0), 1, at(NEXT_MONDAY, 8, 1)),
    (at(SATURDAY, 8, 0), 240, at(NEXT_MONDAY, 12, 0)),
    (at(MONDAY, 9, 0), 2400, at(NEXT_MONDAY, 9, 0)),
    (at(MONDAY, 9, 0, 59), 1, at(MONDAY, 9, 1)),
    (at(MONDAY, 7, 59, 59), 0, at(MONDAY, 8, 0)),
])
def test_add_business_minutes(start, minutes, expected):
    assert slaclock.add_business_minutes(start, minutes) == expected


def test_add_business_minutes_result_has_no_seconds():
    due = slaclock.add_business_minutes(at(MONDAY, 10, 0, 45).replace(microsecond=123), 5)
    assert (due.second, due.microsecond) == (0, 0)
    assert due == at(MONDAY, 10, 5)


def test_add_business_minutes_rejects_negative():
    with pytest.raises(ValueError):
        slaclock.add_business_minutes(at(MONDAY, 9), -1)


def test_add_business_minutes_limit_of_max_days():
    # 367 calendar days (offsets 0..366) from a Monday: 52 weeks and Mon, Tue, Wed = 263 business days
    start = at(MONDAY, 8, 0)
    most = 263 * 480
    assert slaclock.add_business_minutes(start, most) == datetime(2027, 11, 17, 16, 0)
    with pytest.raises(ValueError):
        slaclock.add_business_minutes(start, most + 1)


def test_add_business_minutes_far_target_raises():
    with pytest.raises(ValueError):
        slaclock.add_business_minutes(at(MONDAY, 9), 10_000_000)


# business_minutes_between -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("start, end, expected", [
    (at(MONDAY, 9, 0), at(MONDAY, 9, 0), 0),
    (at(MONDAY, 9, 0), at(MONDAY, 9, 1), 1),
    (at(MONDAY, 8, 0), at(MONDAY, 16, 0), 480),
    (at(MONDAY, 7, 0), at(MONDAY, 9, 0), 60),
    (at(MONDAY, 15, 0), at(MONDAY, 18, 0), 60),
    (at(MONDAY, 15, 0), at(TUESDAY, 9, 0), 120),
    (at(MONDAY, 16, 0), at(TUESDAY, 8, 0), 0),
    (at(FRIDAY, 15, 0), at(NEXT_MONDAY, 9, 0), 120),
    (at(SATURDAY, 9, 0), at(SUNDAY, 15, 0), 0),
    (at(SATURDAY, 0, 0), at(NEXT_MONDAY, 8, 30), 30),
    (at(MONDAY, 0, 0), at(NEXT_MONDAY, 0, 0), 2400),
    (at(MONDAY, 9, 0, 30), at(MONDAY, 9, 1, 10), 1),
    (at(MONDAY, 9, 0, 59), at(MONDAY, 9, 0, 1), 0),
])
def test_business_minutes_between(start, end, expected):
    result = slaclock.business_minutes_between(start, end)
    assert result == expected
    assert type(result) is int      # durations are whole minutes (int), as the module's docstring says


def test_business_minutes_between_rejects_end_before_start():
    with pytest.raises(ValueError):
        slaclock.business_minutes_between(at(MONDAY, 10), at(MONDAY, 9, 59))


def test_business_minutes_between_max_days():
    start = at(MONDAY, 8, 0)
    assert slaclock.business_minutes_between(start, at(MONDAY + timedelta(days=366), 23, 59)) == 263 * 480
    with pytest.raises(ValueError):
        slaclock.business_minutes_between(start, at(MONDAY + timedelta(days=367), 0, 0))


@pytest.mark.parametrize("start, minutes", [
    (at(MONDAY, 9, 0), 0), (at(MONDAY, 9, 0), 1), (at(MONDAY, 15, 0), 60), (at(MONDAY, 15, 0), 61),
    (at(FRIDAY, 15, 30), 60), (at(SATURDAY, 10, 0), 500), (at(MONDAY, 7, 0), 1000),
])
def test_round_trip(start, minutes):
    due = slaclock.add_business_minutes(start, minutes)
    assert slaclock.business_minutes_between(start, due) == minutes


# escalation_tier --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("priority, breached, reopens, expected", [
    ("P1", False, 0, 1), ("P1", False, 1, 1), ("P1", False, 2, 2), ("P1", True, 0, 3), ("P1", True, 2, 3),
    ("P2", False, 0, 1), ("P2", False, 1, 1), ("P2", False, 2, 2), ("P2", True, 0, 2), ("P2", True, 2, 3),
    ("P2", True, 5, 3),
    ("P3", False, 0, 0), ("P3", False, 1, 0), ("P3", False, 2, 1), ("P3", False, 3, 1),
    ("P3", True, 0, 1), ("P3", True, 2, 2),
    ("P4", False, 0, 0), ("P4", False, 2, 1), ("P4", True, 0, 1), ("P4", True, 2, 2),
])
def test_escalation_tier(priority, breached, reopens, expected):
    assert slaclock.escalation_tier(priority, breached, reopens) == expected


@pytest.mark.parametrize("priority, reopens", [("P5", 0), ("p1", 0), ("", 0), ("P1", -1), ("P3", -1)])
def test_escalation_tier_rejects_bad_input(priority, reopens):
    with pytest.raises(ValueError):
        slaclock.escalation_tier(priority, False, reopens)


# parse_duration ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("90m", 90), ("4h", 240), ("1h30m", 90), ("2d", 2880), ("1d4h", 1680), ("1d0h5m", 1445),
    ("1h59m", 119), ("60m", 60), ("0h60m", 60), ("1m", 1), ("0d0h1m", 1), ("1d59m", 1499),
    ("  45m  ", 45), ("\t2h\n", 120), ("3d2h1m", 4441), ("100m", 100), ("0d1h", 60),
])
def test_parse_duration(text, expected):
    assert slaclock.parse_duration(text) == expected


@pytest.mark.parametrize("text", [
    "", "   ", "0m", "0h", "0d", "0d0h0m", "1.5h", "30m1h", "-5m", "1 h", "1H", "5", "1h60m", "1d60m",
    "1d0h60m", "m", "h1", "1h 30m", "1x", "2d2d",
])
def test_parse_duration_rejects(text):
    with pytest.raises(ValueError):
        slaclock.parse_duration(text)
