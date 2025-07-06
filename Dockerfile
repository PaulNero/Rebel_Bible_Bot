FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install poetry

RUN poetry install --no-root

ENV PYTHONUNBUFFERED=1

CMD ["poetry", "run", "python", "bot.py"]