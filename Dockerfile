FROM python:3.10-slim

WORKDIR /app

# Debug: Show environment
RUN echo "=== Environment Check ===" && \
    pwd && \
    ls -la && \
    whoami && \
    python --version

COPY requirements.txt .
#RUN pip install -r requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# You can EXPOSE 8080, but it's purely informational in modern Docker.
#EXPOSE 8501
EXPOSE 8080

#CMD ["streamlit", "run", "main.py"]
# Set Streamlit to listen on 0.0.0.0:$PORT
CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0", "--server.port=$PORT"]
