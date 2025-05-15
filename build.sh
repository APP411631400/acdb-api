#!/bin/bash

# 👉 更新套件庫
apt-get update

# 👉 安裝 Microsoft ODBC 驅動的前置依賴
apt-get install -y curl gnupg apt-transport-https

# 👉 加入 Microsoft ODBC 套件來源
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

# 👉 安裝 Microsoft ODBC Driver 17 for SQL Server
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev

# 👉 安裝 Python 套件
pip install -r requirements.txt
