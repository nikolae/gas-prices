FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5050
ENV CACHE_TTL_SECONDS=900
ENV DB_PATH=/data/gas_prices.db

VOLUME ["/data"]

EXPOSE ${PORT}

CMD ["python", "app.py"]
