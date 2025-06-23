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

        # 2. 針對 Render 環境優化的 Playwright 設定
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",  # 不載入圖片，節省資源
                    "--disable-javascript",  # 部分網站可能不需要JS
                    "--memory-pressure-off",
                    "--max_old_space_size=4096"
                ]
            )
            
            # 使用更保守的設定
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                locale="zh-TW",
                viewport={"width": 1024, "height": 768},
                java_script_enabled=False  # 先試試看不用JS
            )

            # 簡化的反檢測
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            for platform, url in urls.items():
                if not url or not url.startswith("http"):
                    result[platform] = "無"
                    continue

                page = context.new_page()
                try:
                    print(f"正在抓取 {platform}: {url}")  # 加入 debug 資訊
                    
                    # 延長 timeout，Render 網路較慢
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    
                    # 等待頁面穩定
                    time.sleep(2)
                    
                    # 先嘗試簡單的方法 - 直接抓取網頁內容
                    content = page.content()
                    print(f"{platform} 頁面長度: {len(content)}")  # debug
                    
                    # 各平台的 selector 邏輯（加入更多容錯）
                    price_text = None
                    
                    if platform == 'momo':
                        selectors = [
                            "span.price__main-value",
                            ".prdPrice",
                            ".price"
                        ]
                        
                    elif platform == 'pchome':
                        selectors = [
                            "span.o-price__content",
                            ".price",
                            "#price"
                        ]
                        
                    elif platform == '博客來':
                        selectors = [
                            "ul.price li strong",
                            "span.price",
                            ".price-tag"
                        ]
                        
                    elif platform == '屈臣氏':
                        selectors = [
                            ".price-value",
                            ".productPrice",
                            ".price"
                        ]
                        
                    else:  # 康是美
                        selectors = [
                            ".prod-sale-price",
                            ".price",
                            ".product-price"
                        ]
                    
                    # 嘗試多個選擇器
                    for selector in selectors:
                        try:
                            element = page.locator(selector).first
                            if element.is_visible():
                                price_text = element.text_content()
                                if price_text:
                                    break
                        except:
                            continue
                    
                    # 如果還是沒抓到，嘗試用正規表達式從整個頁面找
                    if not price_text:
                        import re
                        # 尋找台幣價格模式
                        price_patterns = [
                            r'NT\$\s*([0-9,]+)',
                            r'\$\s*([0-9,]+)',
                            r'價格[：:\s]*([0-9,]+)',
                            r'售價[：:\s]*([0-9,]+)',
                        ]
                        
                        for pattern in price_patterns:
                            match = re.search(pattern, content)
                            if match:
                                price_text = match.group(1)
                                break
                    
                    # 清理數字
                    if price_text:
                        num = re.sub(r'[^0-9.]', '', price_text.strip())
                        result[platform] = f"{num} 元" if num else "查無價格"
                    else:
                        result[platform] = "查無價格"

                except Exception as e:
                    print(f"{platform} 錯誤: {str(e)}")  # debug
                    result[platform] = f"錯誤: {str(e)[:50]}"
                finally:
                    page.close()

            context.close()
            browser.close()

        return jsonify(result)

    except Exception as e:
        print(f"整體錯誤: {str(e)}")  # debug
        return jsonify({'error': str(e)}), 500