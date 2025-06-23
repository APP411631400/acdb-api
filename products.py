from flask import Blueprint, request, jsonify
import pyodbc
from playwright.sync_api import sync_playwright
import re
import time, random

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
    # 1. 先从数据库拿各家商品页 URL
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

    # 2. 用 Playwright + stealth 模式逐家抓价格
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            slow_mo=100,  # 每步操作慢 100ms，更像真人
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            locale="zh-TW",
            viewport={"width": 1280, "height": 720}
        )
        # 注入最简单的 stealth JS，去掉 navigator.webdriver 等标记
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = {runtime:{}};
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-TW', 'zh']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        """)

        for platform, url in urls.items():
            if not url or not url.startswith("http"):
                result[platform] = "無"
                continue

            page = context.new_page()
            try:
                # 随机等一小段再导航，减少检测
                time.sleep(random.uniform(0.5, 1.5))
                page.goto(url, timeout=20000, wait_until="networkidle")

                # 针对每个平台 wait_for_selector + locator
                if platform == 'momo':
                    page.wait_for_selector("span.price__main-value", timeout=15000)
                    txt = page.locator("span.price__main-value").first.text_content()

                elif platform == 'pchome':
                    page.wait_for_selector("span.o-price__content", timeout=15000)
                    txt = page.locator("span.o-price__content").first.text_content()

                elif platform == '博客來':
                    # 静态结构比较好抓
                    try:
                        page.wait_for_selector("ul.price li strong", timeout=10000)
                        txt = page.locator("ul.price li strong").first.text_content()
                    except:
                        page.wait_for_selector("span.price", timeout=5000)
                        txt = page.locator("span.price").first.text_content()

                elif platform == '屈臣氏':
                    page.wait_for_selector(".price-value, .productPrice", timeout=15000)
                    txt = (
                        page.locator(".price-value").first.text_content()
                        or page.locator(".productPrice").first.text_content()
                    )

                else:  # 康是美
                    page.wait_for_selector(".prod-sale-price, .price", timeout=15000)
                    txt = (
                        page.locator(".prod-sale-price").first.text_content()
                        or page.locator(".price").first.text_content()
                    )

                # 清数字
                num = re.sub(r'[^0-9.]', '', (txt or '').strip())
                result[platform] = f"{num} 元" if num else "查無價格"

            except Exception:
                result[platform] = "查無價格"
            finally:
                page.close()

        context.close()
        browser.close()

    return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
