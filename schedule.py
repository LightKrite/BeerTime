"""Чистая логика сменных графиков. Без зависимостей и без ввода-вывода."""

from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple

OFF = "off"
DAY = "day"
NIGHT = "night"
BUSY = "busy"

ALTERNATE = "alternate"

HORIZON_DAYS = 14

GREEN = "green"    # гуляем
YELLOW = "yellow"  # можно, но завтра рано вставать
RED = "red"        # вечером на смену
BLOCKED = "blocked"  # свои дела


class Person(NamedTuple):
    id: int
    name: str
    cycle_on: int
    cycle_off: int
    anchor: date
    mode: str  # DAY | NIGHT | ALTERNATE


def kind(person: Person, d: date, overrides: dict[date, str]) -> str:
    """Род дня d: OFF | DAY | NIGHT | BUSY.

    Правка на конкретную дату перекрывает вычисленный паттерн.
    Деление в Python floor-based, поэтому даты раньше якоря разворачиваются
    назад сами: остаток неотрицателен, а номер блока уходит в минус.
    """
    if d in overrides:
        return overrides[d]
    period = person.cycle_on + person.cycle_off
    n = (d - person.anchor).days
    if n % period >= person.cycle_on:
        return OFF
    if person.mode != ALTERNATE:
        return person.mode
    return DAY if (n // period) % 2 == 0 else NIGHT


def status(person: Person, d: date, overrides: dict[date, str]) -> str:
    """Можно ли человеку пить вечером дня d."""
    today = kind(person, d, overrides)
    if today == BUSY:
        return BLOCKED
    if today == NIGHT:
        return RED
    if kind(person, d + timedelta(days=1), overrides) == DAY:
        return YELLOW
    return GREEN


def day_summary(statuses: list[str]) -> tuple[int, int, int]:
    """Сколько в этот вечер зелёных, жёлтых и блокирующих (RED и BLOCKED)."""
    return (
        statuses.count(GREEN),
        statuses.count(YELLOW),
        sum(s in (RED, BLOCKED) for s in statuses),
    )


def rank(days: list[tuple[date, tuple[int, int, int]]]) -> list[tuple[date, tuple[int, int, int]]]:
    """Лучшие вечера вперёд: сначала без блокирующих, затем больше зелёных, затем ближе дата."""
    return sorted(days, key=lambda item: (item[1][2], -item[1][0], item[0]))
