FROM python:3.10-slim

ENV CHROME_VERSION=114.0.5735.90

RUN apt-get update && apt-get install -y \
    wget unzip xvfb libxi6 libgconf-2-4 libnss3 libxss1 libappindicator3-1 fonts-liberation \
    libatk-bridge2.0-0 libatk1.0-0 libgtk-3-0 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 libxrandr2 \
    libasound2 libpangocairo-1.0-0 libpango-1.0-0 libgbm1 libnspr4 libxshmfence1 libgl1-mesa-glx libgl1-mesa-dri \
    python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*

# تحميل وتثبيت Google Chrome for Testing
RUN wget https://storage.googleapis.com/chrome-for-testing-public/114.0.5735.90/linux64/chrome-linux64.zip \
    && unzip chrome-linux64.zip -d /usr/local/ \
    && rm chrome-linux64.zip \
    && mv /usr/local/chrome-linux64 /usr/local/chrome-linux

ENV PATH="/usr/local/chrome-linux:${PATH}"
ENV CHROME_BIN="/usr/local/chrome-linux/chrome"

# تحميل وتثبيت ChromeDriver
RUN wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm chromedriver_linux64.zip \
    && chmod +x /usr/local/bin/chromedriver

WORKDIR /app
COPY . /app

# تثبيت مكتبات Python من ملف المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
