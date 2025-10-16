#!/bin/sh

if [ ! -d "./migrations" ] || [ ! -f "/app/data/data.db" ]; then
    echo "Initializing migrations and DB..."
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
else
    echo "Upgrading existing DB..."
    flask db upgrade
fi

python src/auth.py

exec flask run --host=0.0.0.0 --port=5013