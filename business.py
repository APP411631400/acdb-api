from flask import Blueprint, request, jsonify
import pyodbc
import hashlib

business_bp = Blueprint('business', __name__)

# ✅ 資料庫連線字串
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem666.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888"
)

# ✅ 商家登入 API
@business_bp.route('/api/business/login', methods=['POST'])
def business_login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'status': 'fail', 'error': '缺少 email 或 password'}), 400

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # 查詢商家帳號
        cursor.execute("""
            SELECT StoreID, StoreName, Email, PasswordHash, Verified
            FROM [dbo].[商家帳號]
            WHERE Email = ?
        """, email)

        row = cursor.fetchone()
        conn.close()

        if row:
            store_id = row.StoreID
            store_name = row.StoreName
            password_hash_db = row.PasswordHash

            # ✅ 假設原本密碼是明碼用 SHA256 存的，你可以改你的 hash 規則
            password_hash_input = hashlib.sha256(password.encode('utf-8')).hexdigest()

            if password_hash_input == password_hash_db:
                return jsonify({
                    'status': 'success',
                    'storeId': store_id,
                    'storeName': store_name
                }), 200
            else:
                return jsonify({'status': 'fail', 'error': '密碼錯誤'}), 401
        else:
            return jsonify({'status': 'fail', 'error': '帳號不存在'}), 404

    except Exception as e:
        return jsonify({'status': 'fail', 'error': str(e)}), 500
