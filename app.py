"""BeerTime: база, маршруты и рендеринг."""

from __future__ import annotations

import contextlib
import os
import sqlite3
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from schedule import ALTERNATE, DAY, HORIZON_DAYS, Person, day_summary, next_override, rank, status

SECRET = os.environ.get("SECRET")
if not SECRET:
    raise RuntimeError("Не задана переменная окружения SECRET")

TZ = ZoneInfo(os.environ.get("TZ", "Europe/Moscow"))
DB_PATH = os.environ.get("DB_PATH", "beertime.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS person (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    cycle_on    INTEGER NOT NULL DEFAULT 2,
    cycle_off   INTEGER NOT NULL DEFAULT 2,
    anchor_date TEXT NOT NULL,
    mode        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS override (
    person_id INTEGER NOT NULL REFERENCES person(id),
    date      TEXT NOT NULL,
    kind      TEXT NOT NULL,
    PRIMARY KEY (person_id, date)
);
"""


@contextlib.contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def today() -> date:
    return datetime.now(TZ).date()


def list_people() -> list[Person]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM person ORDER BY id").fetchall()
    return [
        Person(
            id=row["id"],
            name=row["name"],
            cycle_on=row["cycle_on"],
            cycle_off=row["cycle_off"],
            anchor=date.fromisoformat(row["anchor_date"]),
            mode=row["mode"],
        )
        for row in rows
    ]


def add_person(name: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO person (name, anchor_date, mode) VALUES (?, ?, ?)",
            (name, today().isoformat(), DAY),
        )
        return cur.lastrowid


def update_person(person_id: int, cycle_on: int, cycle_off: int, anchor: date, mode: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE person SET cycle_on = ?, cycle_off = ?, anchor_date = ?, mode = ? WHERE id = ?",
            (cycle_on, cycle_off, anchor.isoformat(), mode, person_id),
        )


def overrides_for(person_id: int) -> dict[date, str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT date, kind FROM override WHERE person_id = ?", (person_id,)
        ).fetchall()
    return {date.fromisoformat(row["date"]): row["kind"] for row in rows}


def set_override(person_id: int, d: date, value: str | None) -> None:
    with connect() as conn:
        if value is None:
            conn.execute(
                "DELETE FROM override WHERE person_id = ? AND date = ?",
                (person_id, d.isoformat()),
            )
        else:
            conn.execute(
                "INSERT INTO override (person_id, date, kind) VALUES (?, ?, ?) "
                "ON CONFLICT (person_id, date) DO UPDATE SET kind = excluded.kind",
                (person_id, d.isoformat(), value),
            )


def build_matrix() -> dict:
    """Данные страницы: строки-люди, колонки-даты, итоги и лучшие вечера."""
    start = today()
    dates = [start + timedelta(days=i) for i in range(HORIZON_DAYS)]
    people = list_people()

    rows = []
    for person in people:
        overrides = overrides_for(person.id)
        rows.append(
            {
                "person": person,
                "statuses": [status(person, d, overrides) for d in dates],
            }
        )

    summaries = [
        day_summary([row["statuses"][i] for row in rows]) for i in range(len(dates))
    ]
    best = [d for d, _ in rank(list(zip(dates, summaries)))[:3]]
    return {"dates": dates, "rows": rows, "summaries": summaries, "best": best}


from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount(f"/b/{SECRET}/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

init_db()


def check_secret(secret: str) -> None:
    if secret != SECRET:
        raise HTTPException(status_code=404)


def me_id(request: Request) -> int | None:
    raw = request.cookies.get("bt_person")
    return int(raw) if raw and raw.isdigit() else None


@app.get("/b/{secret}/")
def index(request: Request, secret: str):
    check_secret(secret)
    if me_id(request) is None:
        return RedirectResponse(f"/b/{secret}/join", status_code=303)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"secret": secret, "matrix": build_matrix(), "me_id": me_id(request)},
    )


@app.get("/b/{secret}/join")
def join_form(request: Request, secret: str):
    check_secret(secret)
    return templates.TemplateResponse(
        request, "join.html", {"secret": secret, "people": list_people()}
    )


@app.post("/b/{secret}/join")
def join(secret: str, person_id: str = Form(""), name: str = Form("")):
    check_secret(secret)
    if person_id.isdigit():
        chosen = int(person_id)
    elif name.strip():
        chosen = add_person(name.strip())
    else:
        return RedirectResponse(f"/b/{secret}/join", status_code=303)
    response = RedirectResponse(f"/b/{secret}/", status_code=303)
    response.set_cookie("bt_person", str(chosen), max_age=60 * 60 * 24 * 365, httponly=True)
    return response


@app.post("/b/{secret}/cell/{iso_date}")
def toggle_cell(request: Request, secret: str, iso_date: str):
    check_secret(secret)
    person_id = me_id(request)
    if person_id is None:
        raise HTTPException(status_code=403)

    d = date.fromisoformat(iso_date)
    overrides = overrides_for(person_id)
    set_override(person_id, d, next_override(overrides.get(d)))

    person = next(p for p in list_people() if p.id == person_id)
    overrides = overrides_for(person_id)
    return templates.TemplateResponse(
        request,
        "cell.html",
        {
            "secret": secret,
            "row": {"person": person},
            "d": d,
            "st": status(person, d, overrides),
            "me_id": person_id,
        },
    )
