FROM python:3.10-slim

# Instal FFmpeg secara otomatis ke dalam sistem Linux server Render
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Salin file requirements dan instal seluruh pustaka Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode aplikasi ke kontainer
COPY . .

# Jalankan server web FastAPI menggunakan uvicorn di port 7860
CMD ["uvicorn", "bot:app_web", "--host", "0.0.0.0", "--port", "7860"]
