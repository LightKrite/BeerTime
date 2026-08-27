import os
import sqlite3
from datetime import date, timedelta

os.environ.setdefault("SECRET", "test-secret")
os.environ.setdefault("TZ", "Europe/Moscow")

import pytest

import app as app_module
from schedule import ALTERNATE, BUSY, DAY, GREEN, HORIZON_DAYS, NIGHT, OFF


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


def test_connect_закрывает_соединение_после_with():
    with app_module.connect() as conn:
        conn.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_connect_откатывает_при_исключении():
    person_id = app_module.add_person("Рома")
    with pytest.raises(RuntimeError):
        with app_module.connect() as conn:
            conn.execute(
                "UPDATE person SET name = ? WHERE id = ?", ("Изменено", person_id)
            )
            raise RuntimeError("бум")
    person = app_module.list_people()[0]
    assert person.name == "Рома"


def test_матрица_имеет_строку_на_человека_и_колонку_на_дату():
    app_module.add_person("Егор")
    app_module.add_person("Макс")
    matrix = app_module.build_matrix()
    assert len(matrix["dates"]) == HORIZON_DAYS
    assert matrix["dates"][0] == app_module.today()
    assert [row["person"].name for row in matrix["rows"]] == ["Егор", "Макс"]
    assert all(len(row["statuses"]) == HORIZON_DAYS for row in matrix["rows"])
    assert len(matrix["summaries"]) == HORIZON_DAYS


def test_итоги_совпадают_со_статусами_колонки():
    app_module.add_person("Егор")
    app_module.add_person("Макс")
    matrix = app_module.build_matrix()
    for i, summary in enumerate(matrix["summaries"]):
        column = [row["statuses"][i] for row in matrix["rows"]]
        assert summary == app_module.day_summary(column)


def test_лучший_вечер_первым_в_списке_best():
    person_id = app_module.add_person("Егор")
    # всё занято, кроме послезавтра — оно и должно оказаться лучшим
    for offset in range(HORIZON_DAYS):
        if offset != 2:
            app_module.set_override(person_id, app_module.today() + timedelta(days=offset), BUSY)
    matrix = app_module.build_matrix()
    assert matrix["best"][0] == app_module.today() + timedelta(days=2)


def test_матрица_без_людей_не_падает():
    matrix = app_module.build_matrix()
    assert matrix["rows"] == []
    assert matrix["summaries"] == [(0, 0, 0)] * HORIZON_DAYS
