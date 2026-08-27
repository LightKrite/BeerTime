# BeerTime UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Клетка доски показывает род дня словом и редактируется выпадающим списком вместо тыка по кругу; под каждым днём — списки имён, кто гуляет и кто может, но завтра рано; компания заводится сразу шестью людьми с готовыми графиками.

**Architecture:** `schedule.py` (домен) не меняется по правилам — только теряет неиспользуемый `next_override`/`OVERRIDE_CYCLE`. Вся работа в `app.py` (форма данных `build_matrix()`, маршрут правки клетки) и в шаблонах/CSS. Заведение компании — отдельный идемпотентный скрипт `seed.py` поверх уже существующих `add_person`/`update_person`.

**Tech Stack:** Тот же, что у проекта: FastAPI, Jinja2, `sqlite3` из стандартной библиотеки, HTMX, pytest.

## Global Constraints

- Предыдущая спека `docs/superpowers/specs/2026-08-27-beertime-design.md` и новая `docs/superpowers/specs/2026-08-27-beertime-ui-design.md` — при расхождении новая спека главнее для того, что она переопределяет; всё остальное берётся из старой.
- Никакого JS-файла и инлайн-скриптов — правка клеткой достигается атрибутами HTMX прямо на `<select>` (`hx-post`, `hx-trigger="change"`), без обёрточной `<form>` и без `onchange`.
- `schedule.py` остаётся чистым: только стандартная библиотека, ни FastAPI, ни `sqlite3`.
- Интерфейсные тексты и имена тестов — на русском. Коммиты — на русском, формат `тип: описание`.
- Секретный путь, куки, идентичность (`current_person`, `check_secret`) не меняются.
- Тесты гоняются как `.venv/bin/pytest -q`. Перед началом на ветке 47 тестов, все зелёные.

---

### Task 1: Заведение компании — `seed.py`

**Files:**
- Create: `seed.py`
- Test: `test_seed.py`

**Interfaces:**
- Consumes: `app.init_db`, `app.list_people`, `app.add_person`, `app.update_person` (все уже существуют, сигнатуры не меняются)
- Produces: `PEOPLE: list[tuple[str, int, int, date, str]]`, `seed() -> None` в модуле `seed.py`

- [ ] **Step 1: Написать падающий тест**

Создать `test_seed.py`:

```python
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
```

- [ ] **Step 2: Запустить тест, убедиться что падает**

Run: `.venv/bin/pytest test_seed.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'seed'`

- [ ] **Step 3: Написать минимальную реализацию**

Создать `seed.py`:

```python
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
```

- [ ] **Step 4: Запустить тесты, убедиться что проходят**

Run: `.venv/bin/pytest -q`
Expected: PASS, 51 тест (47 прежних + 4 новых).

- [ ] **Step 5: Коммит**

```bash
git add seed.py test_seed.py
git commit -m "feat: заведение компании заранее заданными графиками"
```

---

### Task 2: Понятная клетка — род дня словом, правка списком, кто доступен

Самая крупная задача плана: форма данных, маршрут и шаблоны меняются согласованно — разнести их по отдельным задачам означало бы на промежуточном шаге ломать рендер страницы. Делаем одним куском, TDD по каждому срезу.

**Files:**
- Modify: `app.py` (`build_matrix()`, маршрут `POST /b/{secret}/cell/{iso_date}`)
- Modify: `templates/cell.html`, `templates/board.html`
- Modify: `static/style.css`
- Test: `test_app.py`

**Interfaces:**
- Consumes: `kind()`, `status()`, `day_summary()`, `rank()`, константы `OFF/DAY/NIGHT/BUSY/GREEN/YELLOW` из `schedule.py` (уже импортированы или добавляются в `app.py`)
- Produces:
  - `build_matrix() -> dict` новой формы:
    ```python
    {
        "dates": [date, ...],
        "rows": [
            {
                "person": Person,
                "cells": [{"date": date, "kind": str, "status": str, "manual": bool}, ...],
            },
            ...
        ],
        "summaries": [(green, yellow, blocked), ...],   # для best, не рендерится
        "available": [{"green": [str, ...], "yellow": [str, ...]}, ...],
        "best": [date, ...],
    }
    ```
  - маршрут `POST /b/{secret}/cell/{iso_date}` принимает поле формы `kind` со значениями `""` (сброс к паттерну) `"off"` `"day"` `"night"` `"busy"`, прочее — 400

- [ ] **Step 1: Переписать тесты на новую форму `build_matrix()`**

В `test_app.py` заменить четыре теста (они сейчас читают `row["statuses"]`, которого больше не будет):

```python
def test_матрица_имеет_строку_на_человека_и_колонку_на_дату():
    app_module.add_person("Егор")
    app_module.add_person("Макс")
    matrix = app_module.build_matrix()
    assert len(matrix["dates"]) == HORIZON_DAYS
    assert matrix["dates"][0] == app_module.today()
    assert [row["person"].name for row in matrix["rows"]] == ["Егор", "Макс"]
    assert all(len(row["cells"]) == HORIZON_DAYS for row in matrix["rows"])
    assert len(matrix["summaries"]) == HORIZON_DAYS
    assert len(matrix["available"]) == HORIZON_DAYS


def test_клетка_несёт_род_дня_статус_и_признак_ручной_правки():
    person_id = app_module.add_person("Егор")
    d = app_module.today() + timedelta(days=1)
    app_module.set_override(person_id, d, BUSY)
    matrix = app_module.build_matrix()
    idx = matrix["dates"].index(d)
    cell = matrix["rows"][0]["cells"][idx]
    assert cell == {"date": d, "kind": BUSY, "status": "blocked", "manual": True}

    other_idx = 0 if idx != 0 else 1
    other_cell = matrix["rows"][0]["cells"][other_idx]
    assert other_cell["manual"] is False


def test_итоги_совпадают_со_статусами_клеток_колонки():
    app_module.add_person("Егор")
    app_module.add_person("Макс")
    matrix = app_module.build_matrix()
    for i, summary in enumerate(matrix["summaries"]):
        column = [row["cells"][i]["status"] for row in matrix["rows"]]
        assert summary == app_module.day_summary(column)


def test_доступные_совпадают_со_статусами_клеток_колонки():
    a = app_module.add_person("Егор")
    b = app_module.add_person("Макс")
    d = app_module.today()
    app_module.set_override(b, d, BUSY)  # Макс занят сегодня — не должен попасть ни в один список
    matrix = app_module.build_matrix()
    idx = matrix["dates"].index(d)
    available = matrix["available"][idx]
    column = [row["cells"][idx]["status"] for row in matrix["rows"]]
    assert available["green"] == [
        row["person"].name for row in matrix["rows"] if row["cells"][idx]["status"] == GREEN
    ]
    assert available["yellow"] == [
        row["person"].name for row in matrix["rows"] if row["cells"][idx]["status"] == YELLOW
    ]
    assert "Макс" not in available["green"] and "Макс" not in available["yellow"]
    assert column.count("blocked") + column.count("red") >= 1  # Макс где-то заблокирован


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
    assert matrix["available"] == [{"green": [], "yellow": []}] * HORIZON_DAYS
```

Этот блок целиком заменяет четыре функции, стоявшие в файле до этой задачи: `test_матрица_имеет_строку_на_человека_и_колонку_на_дату`,
`test_итоги_совпадают_со_статусами_колонки`, `test_лучший_вечер_первым_в_списке_best`, `test_матрица_без_людей_не_падает`. Первая и предпоследняя
переименованы не были — их тела заменяются на новые. Функция `test_итоги_совпадают_со_статусами_колонки` **переименована** в
`test_итоги_совпадают_со_статусами_клеток_колонки` — старое имя нужно убрать из файла целиком, иначе останется дубликат, обращающийся
к `row["statuses"]`, которого в новой форме `build_matrix()` не будет. `test_лучший_вечер_первым_в_списке_best` и `test_матрица_без_людей_не_падает`
остаются под теми же именами. Сверх этих четырёх добавляются две новые функции — `test_клетка_несёт_род_дня_статус_и_признак_ручной_правки` и
`test_доступные_совпадают_со_статусами_клеток_колонки`.

Добавить `YELLOW` в импорт из `schedule` в начале `test_app.py` (сейчас там `GREEN`, но не `YELLOW`):

```python
from schedule import ALTERNATE, BUSY, DAY, GREEN, HORIZON_DAYS, NIGHT, OFF, YELLOW
```

- [ ] **Step 2: Переписать тесты на новый маршрут правки клетки**

Заменить `test_тык_по_клетке_крутит_правку_по_кругу` на:

```python
def test_выбор_в_списке_сохраняет_правку_а_сброс_убирает_её():
    person_id = app_module.add_person("Егор")
    d = app_module.today() + timedelta(days=1)
    c = client()
    c.cookies.set("bt_person", str(person_id))
    url = f"/b/test-secret/cell/{d.isoformat()}"

    c.post(url, data={"kind": NIGHT})
    assert app_module.overrides_for(person_id) == {d: NIGHT}

    c.post(url, data={"kind": ""})
    assert app_module.overrides_for(person_id) == {}


def test_некорректное_значение_kind_отклоняется():
    person_id = app_module.add_person("Егор")
    d = app_module.today() + timedelta(days=1)
    c = client()
    c.cookies.set("bt_person", str(person_id))
    response = c.post(f"/b/test-secret/cell/{d.isoformat()}", data={"kind": "не-род"})
    assert response.status_code == 400
    assert app_module.overrides_for(person_id) == {}
```

Заменить `test_тык_до_занят_обновляет_итог_блокирующих_в_ответе` — счётчика `class="summary"` в вёрстке больше не будет, вместо него списки доступных:

```python
def test_выбор_занят_убирает_человека_из_списков_доступных_в_ответе():
    a = app_module.add_person("Егор")
    app_module.add_person("Макс")
    d = app_module.today() + timedelta(days=1)
    c = client()
    c.cookies.set("bt_person", str(a))
    url = f"/b/test-secret/cell/{d.isoformat()}"

    idx = app_module.build_matrix()["dates"].index(d)
    assert "Егор" in app_module.build_matrix()["available"][idx]["green"]

    response = c.post(url, data={"kind": BUSY})

    assert "Егор" not in app_module.build_matrix()["available"][idx]["green"]

    # доска перерисована целиком: колонка idx в ответе больше не содержит Егора
    # ни в списке "гуляют", ни в "могут, завтра смена"
    available_cells = re.findall(r'<td class="available">(.*?)</td>', response.text, re.S)
    green_column = available_cells[idx]
    yellow_column = available_cells[HORIZON_DAYS + idx]
    assert "Егор" not in green_column
    assert "Егор" not in yellow_column
```

`test_тык_возвращает_html_всей_доски` оставить как есть — она проверяет обёртку `<div id="board">` и `hx-post`/`hx-target`/`hx-swap`, это не зависит от того, что именно внутри клетки.

Переписать `test_занятая_клетка_рисуется_как_запрещающий_знак` — раньше проверяла эмодзи, теперь клетка своя (редактируемая) и рисуется как `<select>`:

```python
def test_занятая_клетка_рисуется_как_выбранный_пункт_занят():
    person_id = app_module.add_person("Егор")
    app_module.set_override(person_id, app_module.today(), BUSY)
    c = client()
    c.cookies.set("bt_person", str(person_id))
    body = c.get("/b/test-secret/").text
    assert f'id="cell-{person_id}-{app_module.today().isoformat()}"' in body
    assert 'class="cell blocked editable"' in body
    assert '<option value="busy" selected>занят</option>' in body
```

Добавить тест на то, что своя клетка без правки показывает выбранным «по графику», а чужая клетка — текст без выпадающего списка:

```python
def test_своя_клетка_без_правки_показывает_по_графику_выбранным():
    person_id = app_module.add_person("Егор")
    c = client()
    c.cookies.set("bt_person", str(person_id))
    body = c.get("/b/test-secret/").text
    assert '<option value="" selected>по графику</option>' in body


def test_чужая_клетка_не_редактируется():
    me = app_module.add_person("Егор")
    other = app_module.add_person("Макс")
    d = app_module.today()
    app_module.set_override(other, d, NIGHT)
    c = client()
    c.cookies.set("bt_person", str(me))
    body = c.get("/b/test-secret/").text

    match = re.search(rf'<td id="cell-{other}-{d.isoformat()}".*?</td>', body, re.S)
    assert match is not None
    other_cell_html = match.group(0)
    assert "editable" not in other_cell_html
    assert "hx-post" not in other_cell_html
    assert "ночная смена •" in other_cell_html
```

Три старые функции этого шага удалить целиком, они больше не соответствуют вёрстке и упадут после Step 6-8:
`test_тык_по_клетке_крутит_правку_по_кругу` (заменена на `test_выбор_в_списке_сохраняет_правку_а_сброс_убирает_её` и
`test_некорректное_значение_kind_отклоняется`), `test_тык_до_занят_обновляет_итог_блокирующих_в_ответе` (заменена на
`test_выбор_занят_убирает_человека_из_списков_доступных_в_ответе` — проверяла разметку `class="summary"`, которой в доске больше нет),
`test_занятая_клетка_рисуется_как_запрещающий_знак` (заменена на `test_занятая_клетка_рисуется_как_выбранный_пункт_занят` — проверяла
эмодзи `⛔`, которого в клетке больше нет). `test_тык_возвращает_html_всей_доски` остаётся без изменений — она проверяет обёртку
`<div id="board">` и атрибуты `hx-post`/`hx-target`/`hx-swap`, это не зависит от содержимого клетки.

- [ ] **Step 3: Запустить тесты, убедиться что падают**

Run: `.venv/bin/pytest test_app.py -q`
Expected: FAIL — `KeyError: 'cells'` и/или `AssertionError` на новых проверках, `build_matrix()`/маршрут ещё старые.

- [ ] **Step 4: Переписать `build_matrix()` в `app.py`**

Изменить импорт из `schedule` (добавить `kind`, `GREEN`, `YELLOW`; `next_override` больше не нужен маршруту, но пока оставить импорт нетронутым — уберётся в Task 3):

```python
from schedule import ALTERNATE, BUSY, DAY, GREEN, HORIZON_DAYS, NIGHT, OFF, Person, YELLOW, day_summary, kind, next_override, rank, status
```

Заменить тело `build_matrix()`:

```python
def build_matrix() -> dict:
    """Данные страницы: строки-люди, колонки-даты, итоги и лучшие вечера."""
    start = today()
    dates = [start + timedelta(days=i) for i in range(HORIZON_DAYS)]
    people = list_people()

    rows = []
    for person in people:
        overrides = overrides_for(person.id)
        cells = [
            {
                "date": d,
                "kind": kind(person, d, overrides),
                "status": status(person, d, overrides),
                "manual": d in overrides,
            }
            for d in dates
        ]
        rows.append({"person": person, "cells": cells})

    summaries = []
    available = []
    for i in range(len(dates)):
        column = [row["cells"][i]["status"] for row in rows]
        summaries.append(day_summary(column))
        available.append(
            {
                "green": [row["person"].name for row in rows if row["cells"][i]["status"] == GREEN],
                "yellow": [row["person"].name for row in rows if row["cells"][i]["status"] == YELLOW],
            }
        )

    best = [d for d, s in rank(list(zip(dates, summaries))) if s[2] == 0][:3]
    return {
        "dates": dates,
        "rows": rows,
        "summaries": summaries,
        "available": available,
        "best": best,
    }
```

- [ ] **Step 5: Переписать маршрут правки клетки**

Заменить функцию `toggle_cell`:

```python
@app.post("/b/{secret}/cell/{iso_date}")
def set_cell(
    request: Request,
    secret: str,
    iso_date: str,
    override_kind: str = Form("", alias="kind"),
):
    check_secret(secret)
    person = current_person(request)
    if person is None:
        raise HTTPException(status_code=403)

    try:
        d = date.fromisoformat(iso_date)
    except ValueError:
        raise HTTPException(status_code=400)

    if override_kind and override_kind not in {OFF, DAY, NIGHT, BUSY}:
        raise HTTPException(status_code=400)

    set_override(person.id, d, override_kind or None)

    return templates.TemplateResponse(
        request,
        "board.html",
        {"secret": secret, "matrix": build_matrix(), "me_id": person.id},
    )
```

`OFF` и `BUSY` в этой строке — новые: раньше `app.py` их не импортировал (маршрут крутил `next_override` и не называл роды дня по имени). Оба нужны для проверки `{OFF, DAY, NIGHT, BUSY}` в Step 5.

- [ ] **Step 6: Переписать `templates/cell.html`**

```html
{% set editable = row.person.id == me_id %}
{% set kind_labels = {"off": "выходной", "day": "дневная смена", "night": "ночная смена", "busy": "занят"} %}
<td id="cell-{{ row.person.id }}-{{ cell.date.isoformat() }}" class="cell {{ cell.status }}{% if editable %} editable{% endif %}">
  {% if editable %}
  <select name="kind"
          hx-post="/b/{{ secret }}/cell/{{ cell.date.isoformat() }}"
          hx-target="#board"
          hx-swap="outerHTML"
          hx-trigger="change">
    <option value=""{% if not cell.manual %} selected{% endif %}>по графику</option>
    {% for value, label in kind_labels.items() %}
    <option value="{{ value }}"{% if cell.manual and cell.kind == value %} selected{% endif %}>{{ label }}</option>
    {% endfor %}
  </select>
  {% else %}
  {{ kind_labels[cell.kind] }}{% if cell.manual %} •{% endif %}
  {% endif %}
</td>
```

- [ ] **Step 7: Переписать `templates/board.html`**

```html
<div id="board">
<p class="best">
  {% if matrix.best %}
  Ближайшие лучшие вечера:
  {% for d in matrix.best %}<b>{{ d.strftime("%d.%m") }}</b>{% if not loop.last %}, {% endif %}{% endfor %}
  {% else %}
  Вечер без блокировок на ближайшие две недели не нашёлся.
  {% endif %}
</p>

<div class="scroll">
<table class="matrix">
  <thead>
    <tr>
      <th class="sticky">кто</th>
      {% for d in matrix.dates %}
      <th class="{% if d in matrix.best %}best-col{% endif %}">
        {{ ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][d.weekday()] }}<br>{{ d.strftime("%d.%m") }}
      </th>
      {% endfor %}
    </tr>
  </thead>
  <tbody>
    {% for row in matrix.rows %}
    <tr>
      <th class="sticky">{{ row.person.name }}</th>
      {% for cell in row.cells %}
        {% include "cell.html" %}
      {% endfor %}
    </tr>
    {% endfor %}
  </tbody>
  <tfoot>
    <tr>
      <th class="sticky">гуляют</th>
      {% for a in matrix.available %}
      <td class="available">{% for name in a.green %}{{ name }}<br>{% else %}—{% endfor %}</td>
      {% endfor %}
    </tr>
    <tr>
      <th class="sticky">могут, завтра смена</th>
      {% for a in matrix.available %}
      <td class="available">{% for name in a.yellow %}{{ name }}<br>{% else %}—{% endfor %}</td>
      {% endfor %}
    </tr>
  </tfoot>
</table>
</div>

<ul class="legend">
  <li><span class="swatch green"></span> гуляем</li>
  <li><span class="swatch yellow"></span> можно, но завтра рано вставать</li>
  <li><span class="swatch red"></span> вечером на смену</li>
  <li><span class="swatch blocked"></span> занят своими делами</li>
</ul>
<p class="hint">Своя строка редактируется выпадающим списком. Точка после текста — правка руками, а не график.</p>
</div>
```

- [ ] **Step 8: Дописать `static/style.css`**

Добавить в конец файла (фон клеток по статусу раньше не был задан вовсе — только эмодзи передавали цвет; теперь, когда в клетке текст, фон обязателен):

```css
.cell.green { background: #eaf7ea; }
.cell.yellow { background: #fff8e1; }
.cell.red { background: #fdecea; }
.cell.blocked { background: #eceff1; }
.cell select { width: 100%; border: none; background: transparent; font: inherit; }
.available { font-size: .8rem; text-align: left; white-space: nowrap; }
.legend { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 1rem; font-size: .9rem; color: #444; }
.legend .swatch { display: inline-block; width: .8rem; height: .8rem; border: 1px solid #ccc; vertical-align: middle; margin-right: .3rem; }
.legend .swatch.green { background: #eaf7ea; }
.legend .swatch.yellow { background: #fff8e1; }
.legend .swatch.red { background: #fdecea; }
.legend .swatch.blocked { background: #eceff1; }
```

Правило `.summary { ... }` в начале файла больше не используется (счётчик `class="summary"` из вёрстки убран этой задачей) — удалить его.

- [ ] **Step 9: Запустить полный набор тестов, убедиться что проходят**

Run: `.venv/bin/pytest -q`
Expected: PASS, 58 тестов (51 из Task 1 + новые/переписанные из этой задачи; часть старых тестов заменена, не добавлена поверх — считать по фактическому выводу pytest, а не по этому числу впритык).

- [ ] **Step 10: Коммит**

```bash
git add app.py templates/cell.html templates/board.html static/style.css test_app.py
git commit -m "feat: клетка показывает род дня и правится списком, под днём — кто доступен"
```

---

### Task 3: Убрать `next_override` — мёртвый код после перехода на список

**Files:**
- Modify: `schedule.py`, `test_schedule.py`, `app.py`

**Interfaces:**
- Consumes: ничего нового
- Produces: `schedule.py` без `OVERRIDE_CYCLE` и `next_override`

- [ ] **Step 1: Убедиться, что `next_override` больше никем не вызывается**

Run: `grep -rn "next_override" app.py templates/`
Expected: пусто — Task 2 уже убрал единственный вызов в маршруте.

- [ ] **Step 2: Удалить импорт `next_override` в `app.py`**

В строке импорта из `schedule` (см. Task 2, Step 4) убрать `next_override` из списка.

- [ ] **Step 3: Удалить тест цикла правки**

В `test_schedule.py` удалить функцию `test_цикл_правки_дня` и убрать `next_override` из строки импорта в начале файла.

- [ ] **Step 4: Удалить `OVERRIDE_CYCLE` и `next_override` из `schedule.py`**

Удалить:

```python
OVERRIDE_CYCLE: tuple[str | None, ...] = (None, OFF, DAY, NIGHT, BUSY)
```

и

```python
def next_override(current: str | None) -> str | None:
    """Следующее значение по кругу: паттерн → выходной → день → ночь → занят → паттерн."""
    return OVERRIDE_CYCLE[(OVERRIDE_CYCLE.index(current) + 1) % len(OVERRIDE_CYCLE)]
```

- [ ] **Step 5: Запустить полный набор тестов, убедиться что проходят**

Run: `.venv/bin/pytest -q`
Expected: PASS, на 1 тест меньше, чем после Task 2.

- [ ] **Step 6: Коммит**

```bash
git add schedule.py test_schedule.py app.py
git commit -m "chore: убрать next_override — мёртвый код после перехода на список"
```
