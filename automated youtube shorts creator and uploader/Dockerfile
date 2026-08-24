# Optional — only needed once you move off manual/local runs onto a VPS.
# Build:  docker build -t story-shorts-ffmpeg .
# Run:    docker run -d -p 5000:5000 story-shorts-ffmpeg
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

EXPOSE 5000
CMD ["python", "app1.py"]
