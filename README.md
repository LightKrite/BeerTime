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

Пример для чистого сервера на Debian/Ubuntu.

    sudo apt update
    sudo apt install -y git python3-venv nginx certbot python3-certbot-nginx

    sudo useradd -r -m -d /opt/beertime beertime
    sudo -u beertime git clone <repo> /opt/beertime
    cd /opt/beertime
    sudo -u beertime python -m venv .venv
    sudo -u beertime .venv/bin/pip install -r requirements.txt
    sudo -u beertime cp .env.example .env
    sudo -u beertime sed -i "s/^SECRET=.*/SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')/" .env
    sudo chmod 600 .env

    sudo cp deploy/beertime.service /etc/systemd/system/
    sudo systemctl enable --now beertime

    sudo certbot certonly --nginx -d beertime.example.com   # домен уже должен указывать на этот сервер

    sudo cp deploy/nginx.conf /etc/nginx/sites-available/beertime
    sudo ln -s /etc/nginx/sites-available/beertime /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx

Бэкап базы: `sqlite3 /opt/beertime/beertime.db ".backup /var/backups/beertime-$(date +%F).db"`.

Обновление: `git pull && sudo systemctl restart beertime`.

Перед использованием замените `beertime.example.com` — в `deploy/nginx.conf` (`server_name` и оба пути сертификата) и в команде `certbot` — на настоящий домен, а `<repo>` в `git clone` — на настоящий URL репозитория.
