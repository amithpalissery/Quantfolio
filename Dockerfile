# Stage 1: The builder stage
FROM python:3.9 as builder

# Install build dependencies and your application's requirements
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Stage 2: The final, slim runtime image
FROM python:3.9-slim

# Copy only the installed dependencies and application from the builder stage
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /app /app

# Set the entry point for your app
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
