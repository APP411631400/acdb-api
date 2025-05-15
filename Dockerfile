# ✅ 使用官方 Python 基底映像
FROM python:3.10-slim

# ✅ 安裝 Microsoft ODBC Driver 17 + 系統相依套件
RUN apt-get update && \
    apt-get install -y gnupg2 curl unixodbc-dev gcc g++ && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ✅ 設定工作目錄
WORKDIR /app

# ✅ 複製當前專案到容器中
COPY . .

# ✅ 安裝 Python 套件
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ✅ 設定啟動指令（注意 gunicorn 綁定 port 10000）
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:10000"]
