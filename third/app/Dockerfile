FROM python:3.11-slim

WORKDIR /app

ENV PYTHONIOENCODING=utf-8
ENV PYTHONUTF8=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py . 
COPY config.json .

RUN mkdir -p /app/logs

CMD ["python", "app.py"]