# Use a lightweight Python image as the base
FROM python:3.10.12-slim

# Set the working directory inside the container
WORKDIR /app

# Create a non-root user
RUN adduser --disabled-password --gecos "" streamlit_user

# Copy the requirements file and install dependencies first for layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code and set ownership to the new user
COPY --chown=streamlit_user:streamlit_user . .

# Switch to the non-root user
USER streamlit_user

# Expose the port Streamlit runs on (default is 8501)
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
