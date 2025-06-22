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

        name, momo_url, pchome_url, books_url, watsons_url, cosmed_url = row

        # 2. 用 Playwright 打開瀏覽器，巡迴五家網址去抓價格
        result = {"商品ID": product_id, "商品名稱": name}
        urls = {
            'momo':    momo_url,
            'pchome':  pchome_url,
            '博客來':   books_url,
            '屈臣氏':   watsons_url,
            '康是美':   cosmed_url,
        }

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            for platform, url in urls.items():
                if not url or not url.startswith("http"):
                    result[platform] = "無"
                    continue

                page = browser.new_page()
                try:
                    # 等待網路靜止（所有資源載入完成）
                    page.goto(url, timeout=15000, wait_until="networkidle")

                    if platform == 'momo':
                        page.wait_for_selector("span.price__main-value", timeout=15000)
                        text = page.locator("span.price__main-value").first.text_content()

                    elif platform == 'pchome':
                        page.wait_for_selector("span.o-price__content", timeout=15000)
                        text = page.locator("span.o-price__content").first.text_content()

                    elif platform == '博客來':
                        # 先嘗試新版 selector，失敗再 fallback
                        try:
                            page.wait_for_selector("ul.price li strong", timeout=10000)
                            text = page.locator("ul.price li strong").first.text_content()
                        except:
                            page.wait_for_selector("span.price", timeout=5000)
                            text = page.locator("span.price").first.text_content()

                    elif platform == '屈臣氏':
                        page.wait_for_selector(".price-value, .productPrice", timeout=15000)
                        # 優先拿 .price-value
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

                    # 清理非數字字元
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
