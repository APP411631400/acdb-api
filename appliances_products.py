from flask import Blueprint, request, jsonify
import pyodbc

# ✅ 設定 Blueprint 名稱為 appliances_products
appliances_products = Blueprint('appliances_products', __name__)

# ✅ 資料庫連線字串
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem666.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888"
)

# ✅ 取得所有家電比價商品
@appliances_products.route('/appliances/products', methods=['GET'])
def get_all_products():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1000 商品名稱,
                燦坤_價格, 燦坤_圖片, 燦坤_連結,
                PChome_價格, PChome_圖片, PChome_連結,
                momo_價格, momo_圖片, momo_連結,
                全國電子_價格, 全國電子_圖片, 全國電子_連結
            FROM dbo.家電比價
        """)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ✅ 支援商品名稱模糊搜尋
@appliances_products.route('/appliances/products/search', methods=['GET'])
def search_products():
    query = request.args.get('query', '')
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 100 商品名稱,
                燦坤_價格, 燦坤_圖片, 燦坤_連結,
                PChome_價格, PChome_圖片, PChome_連結,
                momo_價格, momo_圖片, momo_連結,
                全國電子_價格, 全國電子_圖片, 全國電子_連結
            FROM dbo.家電比價
            WHERE 商品名稱 LIKE ?
        """, (f'%{query}%',))
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
