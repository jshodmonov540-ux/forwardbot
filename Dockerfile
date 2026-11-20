FROM python:3.12-slim

# Tizim paketlarini yangilash va xavfsizlik
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user yaratish
RUN groupadd -r botgroup && useradd -r -g botgroup -d /app -s /sbin/nologin botuser

WORKDIR /app

# Bog'liqliklarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini ko'chirish
COPY . .

# Huquqlarni non-root foydalanuvchiga berish
RUN chown -R botuser:botgroup /app

# Non-root foydalanuvchiga o'tish
USER botuser

# Python buferini o'chirish (real-time loglar)
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
