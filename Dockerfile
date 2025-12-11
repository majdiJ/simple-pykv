# Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/home/simple-pykv/.local/bin:${PATH}" \
    PYTHONPATH="/opt/simple-pykv"

# Install small build deps for some packages (psutil may need a compiler)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential gcc libffi-dev \
 && rm -rf /var/lib/apt/lists/*

# Create a user for running the app
RUN useradd -m -d /home/simple-pykv simple-pykv

# Copy only requirements first (better layer caching)
WORKDIR /opt/simple-pykv
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project files to /opt/simple-pykv
COPY . /opt/simple-pykv

# Create data directory that will be mounted for persistence
RUN mkdir -p /data && chown -R simple-pykv:simple-pykv /data

# Ensure code directory is readable by the runtime user
RUN chown -R simple-pykv:simple-pykv /opt/simple-pykv

# Run as non-root user
USER simple-pykv

# The container process will run with CWD=/data so config.json and storage_data are created there.
WORKDIR /data

EXPOSE 23849

# Run with Gunicorn binding all interfaces
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:23849", "main:app"]