FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src ./src

ENV FLASK_APP=src/main.py
ENV FLASK_RUN_PORT=5013
ENV FLASK_RUN_HOST=0.0.0.0

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]