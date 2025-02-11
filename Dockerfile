FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY .env .

COPY . .

EXPOSE 8080

CMD streamlit run app.py --server.port 8080 --server.address 0.0.0.0

# CMD streamlit run app.py --server.port=8080 --server.address localhost