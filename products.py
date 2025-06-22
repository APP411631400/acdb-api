from flask import Blueprint, request, jsonify
import pyodbc
from playwright.sync_api import sync_playwright
import re

products = Blueprint('products', __name__)

# ✅ 資料庫連線
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888"
)


# ✅ 取得所有比價商品資料（前端顯示）
@products.route('/products', methods=['GET'])
def get_all_products():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1000 商品名稱,
                momo_圖片, momo_價格, momo_網址,
                pchome_圖片, pchome_價格, pchome_網址,
                博客來_圖片, 博客來_價格, 博客來_網址,
                屈臣氏_圖片, 屈臣氏_價格, 屈臣氏_網址,
                康是美_圖片, 康是美_價格, 康是美_網址,
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


@products.route('/products/search', methods=['GET'])
def search_products():
    query = request.args.get('query', '')
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 100 商品名稱,
                momo_圖片, momo_價格, momo_網址,
                pchome_圖片, pchome_價格, pchome_網址,
                博客來_圖片, 博客來_價格, 博客來_網址,
                屈臣氏_圖片, 屈臣氏_價格, 屈臣氏_網址,
                康是美_圖片, 康是美_價格, 康是美_網址,
                商品ID
            FROM dbo.比價商品
            WHERE 商品名稱 LIKE ?
        """, (f'%{query}%',))
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@products.route('/product_detail', methods=['GET'])
def get_product_detail():
    product_id = request.args.get("id", "")
    try:
        # 1. 从 DB 取出 商品ID、商品名稱 和 五家网址
        conn   = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
              [商品ID],
              [商品名稱],
              [momo_網址]   AS momo_url,
              [pchome_網址] AS pchome_url,
              [博客來_網址] AS books_url,
              [屈臣氏_網址] AS watsons_url,
              [康是美_網址] AS cosmed_url
            FROM dbo.比價商品
            WHERE 商品ID = ?
        """, (product_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "查無此商品"}), 404

        # 确保 unpack 顺序跟 SELECT 一致
        _id, name, momo_url, pchome_url, books_url, watsons_url, cosmed_url = row

        # DEBUG：打印看到底拿到了什么 URL
        print("[DEBUG] 拿到的五家 URL：")
        print("  momo   =", momo_url)
        print("  pchome =", pchome_url)
        print("  books  =", books_url)
        print("  watsons=", watsons_url)
        print("  cosmed =", cosmed_url)

        # 你可以先只回传这些 URL 给前端确认
        return jsonify({
            "商品ID":     _id,
            "商品名稱":   name,
            "debug_urls": {
                "momo":    momo_url,
                "pchome":  pchome_url,
                "books":   books_url,
                "watsons": watsons_url,
                "cosmed":  cosmed_url
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
