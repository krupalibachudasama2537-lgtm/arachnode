FROM python:3.11-slim

WORKDIR /app

# System deps for Playwright's Chromium
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    fonts-liberation libappindicator3-1 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install only Chromium — skip Firefox and WebKit to keep the image slim
RUN playwright install chromium

COPY . .

# Default command: run the Remotive spider (safest starting point)
# Override at runtime: docker run ... scrapy crawl wellfound
CMD ["scrapy", "crawl", "remotive"]
