from flask import Blueprint, request, jsonify
import pyodbc
from playwright.sync_api import sync_playwright
import re
import time
import random

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
        result = {"商品ID": product_id, "商品名稱": name}
        urls = {
            'momo':    momo_url,
            'pchome':  pchome_url,
            '博客來':   books_url,
            '屈臣氏':   watsons_url,
            '康是美':   cosmed_url,
        }

        # 2. 輕量化 Playwright 設定
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--memory-pressure-off",
                    "--max_old_space_size=256"  # 降低記憶體限制
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="zh-TW",
                viewport={"width": 1024, "height": 768},  # 縮小 viewport
                java_script_enabled=True
            )

            # 簡化反檢測
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            def get_price(text):
                """輕量級價格提取"""
                import re
                if not text: return None
                
                patterns = [r'\$(\d{1,3}(?:,\d{3})*)', r'(\d{1,3}(?:,\d{3})*)\s*元']
                for p in patterns:
                    m = re.search(p, text)
                    if m:
                        try:
                            n = int(m.group(1).replace(',', ''))
                            if 10 <= n <= 999999: return m.group(1)
                        except: pass
                return None

            for platform, url in urls.items():
                if not url or not url.startswith("http"):
                    result[platform] = "無"
                    continue

                page = context.new_page()
                try:
                    if platform == 'momo':
                        # momo 需要 JS 和較長等待
                        page.goto(url, timeout=35000, wait_until="networkidle")
                        time.sleep(3)
                        selectors = [".price__main-value", ".prdPrice", ".price-value", "[data-testid='price-value']"]
                        
                    elif platform == 'pchome':
                        # PChome 相對簡單
                        page.goto(url, timeout=25000, wait_until="domcontentloaded")
                        time.sleep(2)
                        selectors = [".price-value", ".prod-price", "#price"]
                        
                    else:
                        # 其他平台
                        page.goto(url, timeout=25000, wait_until="domcontentloaded")
                        time.sleep(1.5)
                        if platform == '博客來':
                            selectors = ["ul.price li strong", "span.price", ".price-tag"]
                        elif platform == '屈臣氏':
                            selectors = [".price-value", ".productPrice", ".price"]
                        else:  # 康是美
                            selectors = [".prod-sale-price", ".price", ".product-price"]
                    
                    # 嘗試選擇器
                    price_found = False
                    for selector in selectors:
                        try:
                            els = page.locator(selector)
                            if els.count() > 0:
                                for i in range(min(3, els.count())):
                                    if els.nth(i).is_visible():
                                        text = els.nth(i).text_content()
                                        price = get_price(text)
                                        if price:
                                            result[platform] = f"{price} 元"
                                            price_found = True
                                            break
                            if price_found: break
                        except: continue
                    
                    # 備用：從頁面內容找
                    if not price_found:
                        content = page.content()
                        price = get_price(content)
                        result[platform] = f"{price} 元" if price else "查無價格"

                except Exception as e:
                    if "timeout" in str(e).lower():
                        result[platform] = "超時"
                    else:
                        result[platform] = "錯誤"
                finally:
                    try:
                        page.close()
                    except: pass

            context.close()
            browser.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'系統錯誤'}), 500