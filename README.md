# BeerTime

Находит вечера, когда вся компания может собраться, исходя из сменных графиков 2/2.

## Запуск

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # и вписать свой SECRET
    set -a && source .env && set +a
    uvicorn app:app --reload

Страница открывается на `http://localhost:8000/b/<SECRET>/`.

## Тесты

    pytest -q
