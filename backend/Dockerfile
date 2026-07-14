FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements /app/requirements
RUN pip install --no-cache-dir -r /app/requirements/base.txt

COPY backend /app/backend

WORKDIR /app/backend

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
