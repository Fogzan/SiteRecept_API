FROM python:3.9

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 4523

CMD ["uvicorn", "main:app", "--host", "192.168.0.6", "--port", "4523"]