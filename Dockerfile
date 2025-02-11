FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
COPY .env .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD streamlit run app.py --server.port 8080 --server.address 0.0.0.0

# CMD streamlit run app.py --server.port=8080 --server.address localhost