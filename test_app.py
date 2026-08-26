import os
from datetime import date

os.environ.setdefault("SECRET", "test-secret")
os.environ.setdefault("TZ", "Europe/Moscow")

import pytest

import app as app_module
from schedule import ALTERNATE, BUSY, DAY, OFF


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "test.db"))
    app_module.init_db()
    yield


def test_добавить_и_прочитать_человека():
    person_id = app_module.add_person("Егор")
    people = app_module.list_people()
    assert [p.name for p in people] == ["Егор"]
    assert people[0].id == person_id
    assert people[0].cycle_on == 2 and people[0].cycle_off == 2
    assert people[0].mode == DAY


def test_обновить_настройки_цикла():
    person_id = app_module.add_person("Макс")
    app_module.update_person(person_id, 3, 3, date(2026, 8, 12), ALTERNATE)
    person = app_module.list_people()[0]
    assert (person.cycle_on, person.cycle_off, person.mode) == (3, 3, ALTERNATE)
    assert person.anchor == date(2026, 8, 12)


def test_правки_записываются_перезаписываются_и_удаляются():
    person_id = app_module.add_person("Ден")
    d = date(2026, 8, 20)
    app_module.set_override(person_id, d, OFF)
    assert app_module.overrides_for(person_id) == {d: OFF}
    app_module.set_override(person_id, d, BUSY)
    assert app_module.overrides_for(person_id) == {d: BUSY}
    app_module.set_override(person_id, d, None)
    assert app_module.overrides_for(person_id) == {}


def test_правки_не_протекают_между_людьми():
    a = app_module.add_person("Саня")
    b = app_module.add_person("Витя")
    app_module.set_override(a, date(2026, 8, 20), BUSY)
    assert app_module.overrides_for(b) == {}
