from flask import Blueprint, request, jsonify
import pyodbc

products = Blueprint('products', __name__)

# ✅ 資料庫連線設定
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888"
)

# ✅ 取得所有比價商品資料（前端顯示用）
@products.route('/products', methods=['GET'])
def get_all_products():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1000 商品名稱,
                momo_價格, momo_網址,
                pchome_價格, pchome_網址,
                博客來_價格, 博客來_網址,
                屈臣氏_價格, 屈臣氏_網址,
                康是美_價格, 康是美_網址,
                商品ID
            FROM dbo.比價商品
        """)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ✅ 搜尋比價商品（模糊搜尋）
@products.route('/products/search', methods=['GET'])
def search_products():
    query = request.args.get('query', '')
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 100 商品名稱,
                momo_價格, momo_網址,
                pchome_價格, pchome_網址,
                博客來_價格, 博客來_網址,
                屈臣氏_價格, 屈臣氏_網址,
                康是美_價格, 康是美_網址,
                商品ID
            FROM dbo.比價商品
            WHERE 商品名稱 LIKE ?
        """, (f'%{query}%',))  # ✅ 注意這裡用 tuple 傳參
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

