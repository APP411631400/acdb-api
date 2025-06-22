from flask import Blueprint, request, jsonify
import pyodbc
from playwright.sync_api import sync_playwright


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
        # 1. 從資料庫拿各家網址
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 商品名稱,
                   momo_網址   AS momo_url,
                   pchome_網址 AS pchome_url,
                   博客來_網址 AS books_url,
                   屈臣氏_網址 AS watsons_url,
                   康是美_網址 AS cosmed_url
            FROM dbo.比價商品
            WHERE 商品ID = ?
        """, (product_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({'error': '查無此商品'}), 404

        _, momo_url, pchome_url, books_url, watsons_url, cosmed_url = row

        # 2. 用 Playwright 打開瀏覽器，巡迴五家網址去抓價格
        result = {"商品ID": product_id, "商品名稱": row[0]}
        urls = {
            'momo':    momo_url,
            'pchome':  pchome_url,
            '博客來':   books_url,
            '屈臣氏':   watsons_url,
            '康是美':   cosmed_url,
        }

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            for name, url in urls.items():
                if not url or not url.startswith("http"):
                    result[name] = "無"
                    continue
                page = browser.new_page()
                try:
                    page.goto(url, timeout=15000)
                    # 根據各家電商的 CSS selector 抓價格
                    if name == 'momo':
                        text = page.locator("span.price__main-value").text_content()
                    elif name == 'pchome':
                        text = page.locator("span.o-price__content").text_content()
                    elif name == '博客來':
                        text = page.locator("ul.price li strong").text_content()
                    elif name == '屈臣氏':
+                       text = (
+                           page.locator(".price-value").text_content()
+                           or page.locator(".productPrice").text_content()
+                       )
                    else:  # 康是美
+                       text = (
+                           page.locator(".prod-sale-price").text_content()
+                           or page.locator(".price").text_content()
+                       )

                    # 清理非數字字元
                    import re
                    price = re.sub(r'[^0-9.]', '', text.strip())
                    result[name] = f"{price} 元" if price else "查無價格"
                except Exception:
                    result[name] = "查無價格"
                finally:
                    page.close()
            browser.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
