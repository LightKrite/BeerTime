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


from fastapi.testclient import TestClient


def client():
    return TestClient(app_module.app)


def test_неверный_секрет_даёт_404():
    assert client().get("/b/wrong-secret/").status_code == 404


def test_без_куки_редирект_на_вход():
    response = client().get("/b/test-secret/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/b/test-secret/join"


def test_вход_новым_именем_ставит_куку():
    c = client()
    response = c.post("/b/test-secret/join", data={"person_id": "", "name": "Егор"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/b/test-secret/"
    assert c.cookies["bt_person"] == str(app_module.list_people()[0].id)


def test_вход_выбором_существующего_человека():
    person_id = app_module.add_person("Макс")
    c = client()
    c.post("/b/test-secret/join", data={"person_id": str(person_id), "name": ""}, follow_redirects=False)
    assert c.cookies["bt_person"] == str(person_id)
    assert len(app_module.list_people()) == 1  # дубликат не создан


def test_матрица_показывает_имена_и_даты():
    person_id = app_module.add_person("Егор")
    c = client()
    c.cookies.set("bt_person", str(person_id))
    body = c.get("/b/test-secret/").text
    assert "Егор" in body
    assert app_module.today().strftime("%d") in body


def test_тык_по_клетке_крутит_правку_по_кругу():
    person_id = app_module.add_person("Егор")
    d = app_module.today() + timedelta(days=1)
    c = client()
    c.cookies.set("bt_person", str(person_id))
    url = f"/b/test-secret/cell/{d.isoformat()}"

    c.post(url)
    assert app_module.overrides_for(person_id) == {d: OFF}
    c.post(url)
    assert app_module.overrides_for(person_id) == {d: DAY}
    c.post(url)
    assert app_module.overrides_for(person_id) == {d: NIGHT}
    c.post(url)
    assert app_module.overrides_for(person_id) == {d: BUSY}
    c.post(url)
    assert app_module.overrides_for(person_id) == {}  # сброс к графику


def test_тык_возвращает_html_одной_клетки():
    person_id = app_module.add_person("Егор")
    d = app_module.today() + timedelta(days=1)
    c = client()
    c.cookies.set("bt_person", str(person_id))
    url = f"/b/test-secret/cell/{d.isoformat()}"
    body = c.post(url).text
    assert body.strip().startswith("<td")
    assert f"cell-{person_id}-{d.isoformat()}" in body
    # клетка должна остаться "тыкабельной": повторный POST на тот же адрес
    assert f'hx-post="{url}"' in body
    assert "hx-target=" in body
    assert "hx-swap=" in body


def test_без_куки_править_нельзя():
    app_module.add_person("Егор")
    d = app_module.today().isoformat()
    assert client().post(f"/b/test-secret/cell/{d}").status_code == 403


def test_кривая_дата_в_адресе_даёт_400():
    person_id = app_module.add_person("Егор")
    c = client()
    c.cookies.set("bt_person", str(person_id))
    assert c.post("/b/test-secret/cell/не-дата").status_code == 400


def test_вход_с_пустыми_person_id_и_именем_не_создаёт_человека():
    c = client()
    response = c.post("/b/test-secret/join", data={"person_id": "", "name": ""}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/b/test-secret/join"
    assert app_module.list_people() == []


def test_протухшая_кука_редиректит_на_вход():
    c = client()
    c.cookies.set("bt_person", "999999")
    response = c.get("/b/test-secret/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/b/test-secret/join"


def test_форма_настроек_показывает_текущие_значения():
    person_id = app_module.add_person("Егор")
    app_module.update_person(person_id, 4, 6, date(2026, 8, 12), ALTERNATE)
    c = client()
    c.cookies.set("bt_person", str(person_id))
    body = c.get("/b/test-secret/me").text
    assert 'name="cycle_on" min="1" max="14" value="4"' in body
    assert 'name="cycle_off" min="1" max="14" value="6"' in body
    assert "2026-08-12" in body
    assert 'value="alternate" selected' in body
    assert 'value="day" selected' not in body
    assert 'value="night" selected' not in body


def test_сохранение_настроек():
    person_id = app_module.add_person("Егор")
    c = client()
    c.cookies.set("bt_person", str(person_id))
    response = c.post(
        "/b/test-secret/me",
        data={"cycle_on": "2", "cycle_off": "2", "anchor": "2026-08-12", "mode": ALTERNATE},
        follow_redirects=False,
    )
    assert response.status_code == 303
    person = app_module.list_people()[0]
    assert person.mode == ALTERNATE
    assert person.anchor == date(2026, 8, 12)


def test_некорректный_цикл_отклоняется():
    person_id = app_module.add_person("Егор")
    c = client()
    c.cookies.set("bt_person", str(person_id))
    response = c.post(
        "/b/test-secret/me",
        data={"cycle_on": "0", "cycle_off": "2", "anchor": "2026-08-12", "mode": DAY},
    )
    assert response.status_code == 400
    assert app_module.list_people()[0].cycle_on == 2  # не сохранилось


def test_кривая_дата_якоря_отклоняется():
    person_id = app_module.add_person("Егор")
    app_module.update_person(person_id, 2, 2, date(2026, 8, 12), DAY)
    c = client()
    c.cookies.set("bt_person", str(person_id))
    response = c.post(
        "/b/test-secret/me",
        data={"cycle_on": "3", "cycle_off": "3", "anchor": "не-дата", "mode": ALTERNATE},
    )
    assert response.status_code == 400
    person = app_module.list_people()[0]
    assert person.anchor == date(2026, 8, 12)  # не сохранилось
    assert person.mode == DAY  # не сохранилось
