# ✅ 使用官方 Python 基底映像
FROM python:3.10-slim

# ─── 2. 安装系统依赖：ODBC 驱动 + Playwright Chromium 运行库 ────
RUN apt-get update && apt-get install -y \
      gnupg2 curl unixodbc-dev gcc g++ \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
      libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
      libasound2 libpangocairo-1.0-0 libpango-1.0-0 \
      libgtk-3-0 libdrm2 libdbus-1-3 && \
    # 安装 Microsoft ODBC Driver 17
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    # 清理缓存
    rm -rf /var/lib/apt/lists/*

# ✅ 設定工作目錄
WORKDIR /app

# ✅ 複製當前專案到容器中
COPY . .

# ✅ 安裝 Python 套件
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN playwright install --with-deps chromium

# ✅ 設定啟動指令（注意 gunicorn 綁定 port 10000）
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:10000", "--workers", "1", "--threads", "1", "--timeout", "120"]
