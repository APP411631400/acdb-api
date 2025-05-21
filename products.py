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

# ✅ 取得所有商品
@products.route('/products', methods=['GET'])
def get_all_products():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1000 平台, 分類, 店家名稱, 商品名稱, 原價, 特價, 連結, 圖片網址, 商品ID FROM dbo.商品資訊")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ✅ 模糊搜尋商品名稱
@products.route('/products/search', methods=['GET'])
def search_products():
    query = request.args.get('query', '')
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 100 平台, 分類, 店家名稱, 商品名稱, 原價, 特價, 連結, 圖片網址, 商品ID
            FROM dbo.商品資訊
            WHERE 商品名稱 LIKE ?
        """, (f'%{query}%',))  # ✅ 注意這裡用 tuple 傳參
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

