# 1. Use an official, lightweight Python runtime
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install necessary system dependencies (often needed for SQLite and ChromaDB)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container
COPY . .

# 6. Create a non-root user and group for security hardening
#    Running as root inside a container is a security anti-pattern.
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home appuser && \
    chown -R appuser:appgroup /app

# 7. Switch to the non-root user for all subsequent commands
USER appuser

# 8. Expose the port that Streamlit uses
EXPOSE 8501

# 9. Command to boot up the dashboard
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
