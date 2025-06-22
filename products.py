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
        # 1. 從資料庫撈 URL
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

        name, momo_url, pchome_url, books_url, watsons_url, cosmed_url = row
        result = {"商品ID": product_id, "商品名稱": name}
        urls = {
            'momo':   momo_url,
            'pchome': pchome_url,
            '博客來':  books_url,
            '屈臣氏':  watsons_url,
            '康是美':  cosmed_url,
        }

        # 2. Playwright 撰寫
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            for platform, url in urls.items():
                if not url or not url.startswith("http"):
                    result[platform] = "無"
                    continue

                page = browser.new_page()
                try:
                    # （a）先到「原始 URL」等 networkidle
                    page.goto(url, timeout=15000, wait_until="networkidle")
                    final = page.url
                    # （b）如果有跳轉，把它當「最終 URL」再 load 一次
                    if final != url:
                        page.goto(final, timeout=15000, wait_until="networkidle")

                    # （c）根據不同平台用 wait_for_selector + locator 撈價錢
                    if platform == 'momo':
                        page.wait_for_selector("span.price__main-value", timeout=15000)
                        text = page.locator("span.price__main-value").first.text_content()

                    elif platform == 'pchome':
                        page.wait_for_selector("span.o-price__content", timeout=15000)
                        text = page.locator("span.o-price__content").first.text_content()

                    elif platform == '博客來':
                        # 博客來可能有兩種版面
                        try:
                            page.wait_for_selector("ul.price li strong", timeout=8000)
                            text = page.locator("ul.price li strong").first.text_content()
                        except:
                            page.wait_for_selector("span.price", timeout=8000)
                            text = page.locator("span.price").first.text_content()

                    elif platform == '屈臣氏':
                        page.wait_for_selector(".price-value, .productPrice", timeout=15000)
                        text = (
                            page.locator(".price-value").first.text_content()
                            or page.locator(".productPrice").first.text_content()
                        )

                    else:  # 康是美
                        page.wait_for_selector(".prod-sale-price, .price", timeout=15000)
                        text = (
                            page.locator(".prod-sale-price").first.text_content()
                            or page.locator(".price").first.text_content()
                        )

                    # （d）清理數字
                    num = re.sub(r'[^0-9.]', '', (text or '').strip())
                    result[platform] = f"{num} 元" if num else "查無價格"

                except Exception:
                    result[platform] = "查無價格"
                finally:
                    page.close()

            browser.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
