FROM python:3.12-slim

WORKDIR /app

COPY cloud_run/rollmind_endpoint_manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY endpoint/ /app/endpoint/
COPY cloud_run/rollmind_endpoint_manager/main.py /app/

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
