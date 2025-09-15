#!/bin/bash
# Render.com Chrome 설치 스크립트

echo "🔧 Chrome 설치 시작..."

# 시스템 업데이트
apt-get update -qq

# Chrome 및 ChromeDriver 의존성 설치
apt-get install -y \
    wget \
    curl \
    unzip \
    xvfb \
    fonts-liberation \
    libnss3-dev \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2

# Chrome 다운로드 및 설치
echo "📦 Chrome 다운로드 중..."
wget -q -O chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

echo "🔨 Chrome 설치 중..."
dpkg -i chrome.deb || apt-get install -f -y
rm chrome.deb

# Chrome 설치 확인
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome 설치 완료"
    google-chrome --version
    
    # 환경변수 확인
    which google-chrome
    echo "Chrome 바이너리 위치: $(which google-chrome)"
else
    echo "❌ Chrome 설치 실패"
    exit 1
fi

echo "🐍 Python 의존성 설치..."
pip install --no-cache-dir -r requirements.txt

echo "🚀 설치 완료!"
echo "Chrome: $(which google-chrome)"
echo "Python packages installed successfully"
