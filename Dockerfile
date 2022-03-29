FROM python:3.8.3-alpine as alpine-build
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "./src/main.py"]
