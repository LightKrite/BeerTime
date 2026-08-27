"""Заводит компанию заранее заданными графиками.

Идемпотентен: человек с таким именем не дублируется, а его график
обновляется до значений отсюда. Ручные правки (override) не трогает —
seed() их не читает и не пишет.

Запуск: .venv/bin/python seed.py
"""

from __future__ import annotations

from datetime import date

from app import add_person, init_db, list_people, update_person
from schedule import ALTERNATE, DAY

PEOPLE: list[tuple[str, int, int, date, str]] = [
    ("Егор", 2, 2, date(2026, 9, 1), DAY),
    ("Толя", 2, 2, date(2026, 9, 1), ALTERNATE),
    ("Саша", 2, 2, date(2026, 9, 1), DAY),
    ("Федор", 2, 2, date(2026, 9, 3), ALTERNATE),
    ("Наташа", 2, 2, date(2026, 9, 3), DAY),
    ("Паша", 2, 2, date(2026, 9, 3), ALTERNATE),
]


def seed() -> None:
    init_db()
    existing = {p.name: p.id for p in list_people()}
    for name, cycle_on, cycle_off, anchor, mode in PEOPLE:
        person_id = existing.get(name) or add_person(name)
        update_person(person_id, cycle_on, cycle_off, anchor, mode)


if __name__ == "__main__":
    seed()
    print(f"Готово: {len(PEOPLE)} человек.")
