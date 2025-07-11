FROM python:3.9-slim

WORKDIR /app

COPY app.py requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/site_sources && chmod -R 777 /app/site_sources

USER user

EXPOSE 5000

CMD ["python", "app.py"]


