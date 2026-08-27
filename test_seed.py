import os
from datetime import date

os.environ.setdefault("SECRET", "test-secret")
os.environ.setdefault("TZ", "Europe/Moscow")

import pytest

import app as app_module
import seed as seed_module
from schedule import ALTERNATE, DAY


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "test.db"))
    app_module.init_db()
    yield


def test_заводит_шестерых_с_нужными_графиками():
    seed_module.seed()
    people = {p.name: p for p in app_module.list_people()}
    assert set(people) == {"Егор", "Толя", "Саша", "Федор", "Наташа", "Паша"}
    assert people["Толя"].mode == ALTERNATE
    assert people["Толя"].anchor == date(2026, 9, 1)
    assert people["Егор"].mode == DAY
    assert people["Федор"].anchor == date(2026, 9, 3)
    assert all((p.cycle_on, p.cycle_off) == (2, 2) for p in people.values())


def test_повторный_запуск_не_дублирует_людей():
    seed_module.seed()
    seed_module.seed()
    assert len(app_module.list_people()) == 6


def test_повторный_запуск_не_стирает_ручные_правки():
    seed_module.seed()
    egor = next(p for p in app_module.list_people() if p.name == "Егор")
    d = date(2026, 9, 10)
    app_module.set_override(egor.id, d, "busy")

    seed_module.seed()

    assert app_module.overrides_for(egor.id) == {d: "busy"}


def test_повторный_запуск_обновляет_график_если_он_изменился_в_коде():
    seed_module.seed()
    egor_id = next(p.id for p in app_module.list_people() if p.name == "Егор")
    app_module.update_person(egor_id, 3, 3, date(2026, 1, 1), DAY)  # сбить график руками

    seed_module.seed()

    egor = next(p for p in app_module.list_people() if p.name == "Егор")
    assert (egor.cycle_on, egor.cycle_off, egor.anchor) == (2, 2, date(2026, 9, 1))
