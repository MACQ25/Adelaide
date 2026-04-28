FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y fontconfig fonts-liberation && rm -rf /var/lib/apt/lists/*

ENV FONT_PATH=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "Main.py"]