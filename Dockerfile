FROM python:3.8.18

RUN mkdir /app
COPY pyproject.toml /app
COPY poetry.lock /app
COPY . /app
WORKDIR /app
RUN pip install poetry
RUN poetry install
ENTRYPOINT ["/usr/local/bin/poetry", "run", "podracer"]
