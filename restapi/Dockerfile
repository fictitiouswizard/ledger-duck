
FROM python:3.11

ENV FASTAPI_ENV=development

WORKDIR /app

COPY . /app

RUN pip install poetry

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

RUN pip install --no-cache-dir --upgrade -r requirements.txt

CMD ["uvicorn", "api.main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "8080"]
