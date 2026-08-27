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

## Развёртывание на VPS

    sudo useradd -r -m -d /opt/beertime beertime
    sudo -u beertime git clone <repo> /opt/beertime
    cd /opt/beertime
    sudo -u beertime python -m venv .venv
    sudo -u beertime .venv/bin/pip install -r requirements.txt
    sudo -u beertime cp .env.example .env   # вписать настоящий SECRET

    sudo cp deploy/beertime.service /etc/systemd/system/
    sudo systemctl enable --now beertime

    sudo cp deploy/nginx.conf /etc/nginx/sites-available/beertime
    sudo ln -s /etc/nginx/sites-available/beertime /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx

Бэкап базы: `sqlite3 /opt/beertime/beertime.db ".backup /var/backups/beertime-$(date +%F).db"`.

Обновление: `git pull && sudo systemctl restart beertime`.

Перед использованием `deploy/nginx.conf` замените в нём placeholder `beertime.example.com` (в `server_name` и в путях `ssl_certificate`/`ssl_certificate_key`) на настоящий домен и выпустите для него сертификат Let's Encrypt — иначе nginx откажется стартовать. В команде `git clone <repo>` подставьте настоящий URL репозитория.
