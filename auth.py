# auth.py
from flask import Blueprint, request, jsonify
import pyodbc
import hashlib

auth = Blueprint('auth', __name__)

# ✅ 資料庫連線
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem666.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888;"
)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

@auth.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"status": "fail", "error": "缺少欄位"}), 400

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT UserID, UserName, PasswordHash
            FROM dbo.會員帳號
            WHERE Email = ?
        """, (email,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row and row.PasswordHash == hash_password(password):
            return jsonify({
                "status": "success",
                "userId": row.UserID,
                "userName": row.UserName
            })
        else:
            return jsonify({"status": "fail", "error": "帳號或密碼錯誤"}), 401
    except Exception as e:
        return jsonify({"status": "fail", "error": str(e)}), 500
