# ✅ 使用官方 Python 基底映像
FROM python:3.10-slim

# ─── 2. 安装系统依赖：ODBC 驱动 + Playwright Chromium 运行库 ────
RUN set -eux; \
    apt-get update; \
    apt-get install -y \
      gnupg2 curl unixodbc unixodbc-dev gcc g++ \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
      libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
      libasound2 libpangocairo-1.0-0 libpango-1.0-0 \
      libgtk-3-0 libdrm2 libdbus-1-3; \
    \
    # ✅ 取代 apt-key + debian/10：使用 keyring + debian/12 (bookworm)
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/microsoft-prod.list; \
    apt-get update; \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18; \
    rm -rf /var/lib/apt/lists/*

# ✅ 設定工作目錄
WORKDIR /app

# ✅ 複製當前專案到容器中
COPY . .

# ✅ 安裝 Python 套件
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN playwright install chromium

# ✅ 設定啟動指令（注意 gunicorn 綁定 port 10000）
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:10000", "--workers", "1", "--threads", "1", "--timeout", "120"]

