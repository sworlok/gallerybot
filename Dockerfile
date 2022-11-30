FROM python:3.11.0a6-alpine3.15
WORKDIR /code
COPY poetry.lock pyproject.toml /code/
run apk add --no-cache build-base
RUN pip install -U pip poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi --no-root
COPY . /code
CMD poetry run python app.py
