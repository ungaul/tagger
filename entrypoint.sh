#!/bin/sh

if [ ! -d "./migrations" ]; then
    flask db init
    flask db migrate -m "Auto migration"
fi

flask db upgrade

python src/account.py

exec flask run --host=0.0.0.0 --port=5013