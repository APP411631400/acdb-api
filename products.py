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
            # 更輕量的瀏覽器設定
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
                    "--disable-images",
                    "--memory-pressure-off",
                    "--max_old_space_size=256",  # 降低記憶體限制
                    "--disable-background-networking",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                ]
            )

            for platform, url in urls.items():
                if not url or not url.startswith("http"):
                    result[platform] = "無"
                    continue

                # 根據平台決定是否需要 JavaScript
                need_js = platform in ['momo']
                
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    ),
                    locale="zh-TW",
                    viewport={"width": 1024, "height": 768},
                    java_script_enabled=need_js
                )

                # 反檢測
                if need_js:
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    """)

                page = context.new_page()
                try:
                    print(f"正在抓取 {platform}: {url}")
                    
                    # 根據平台調整 timeout 和等待策略
                    if platform == 'momo':
                        page.goto(url, timeout=45000, wait_until="networkidle")
                        time.sleep(3)  # 等待 JavaScript 渲染
                    else:
                        page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        time.sleep(1)
                    
                    price_text = None
                    
                    # 各平台特化的抓取邏輯
                    if platform == 'momo':
                        # momo 的價格在 JavaScript 渲染後的多個可能位置
                        selectors = [
                            "span.price__main-value",
                            ".prdPrice .o-price__price-value",
                            ".prdPrice .price",
                            "[data-price]",
                            ".price-value",
                            ".price-num"
                        ]
                        
                        # 先嘗試從 JavaScript 變數中抓取
                        try:
                            js_price = page.evaluate("""
                                () => {
                                    // 嘗試從全域變數取得
                                    if (window.goodsPrice) return window.goodsPrice;
                                    if (window.price) return window.price;
                                    
                                    // 從 JSON-LD 取得
                                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                                    for (let script of scripts) {
                                        try {
                                            const data = JSON.parse(script.textContent);
                                            if (data.offers && data.offers.price) {
                                                return data.offers.price;
                                            }
                                        } catch(e) {}
                                    }
                                    
                                    return null;
                                }
                            """)
                            if js_price:
                                price_text = str(js_price)
                        except:
                            pass
                        
                        # 如果 JS 方法失敗，用 selector
                        if not price_text:
                            for selector in selectors:
                                try:
                                    element = page.locator(selector).first
                                    if element.is_visible(timeout=5000):
                                        price_text = element.text_content()
                                        if price_text and any(char.isdigit() for char in price_text):
                                            break
                                except:
                                    continue

                    elif platform == 'pchome':
                        # PChome 的價格結構較穩定
                        selectors = [
                            ".o-price-data__price",
                            ".o-price__content span",
                            ".price-value",
                            "#price span"
                        ]
                        
                        # 特別針對 PChome 的價格格式
                        try:
                            # 尋找包含 $ 符號的價格
                            price_elements = page.locator("text=/\\$\\d+/").all()
                            for element in price_elements:
                                text = element.text_content()
                                if text and '$' in text and len(text) < 20:  # 避免抓到太長的文字
                                    price_text = text
                                    break
                        except:
                            pass
                        
                        # 備用選擇器
                        if not price_text:
                            for selector in selectors:
                                try:
                                    element = page.locator(selector).first
                                    if element.is_visible():
                                        price_text = element.text_content()
                                        if price_text:
                                            break
                                except:
                                    continue

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
                    
                    # 針對其他平台的通用選擇器邏輯
                    if platform not in ['momo', 'pchome'] and not price_text:
                        for selector in selectors:
                            try:
                                element = page.locator(selector).first
                                if element.is_visible():
                                    price_text = element.text_content()
                                    if price_text:
                                        break
                            except:
                                continue
                    
                    # 如果還是沒抓到，用正規表達式從頁面內容搜尋
                    if not price_text:
                        import re
                        content = page.content()
                        
                        # 針對不同平台的價格模式
                        if platform == 'momo':
                            patterns = [
                                r'"price":\s*"?(\d+)"?',
                                r'價格[：:\s]*\$?([0-9,]+)',
                                r'NT\$\s*([0-9,]+)',
                            ]
                        elif platform == 'pchome':
                            patterns = [
                                r'\$(\d+)',
                                r'驚喜優惠[^0-9]*\$(\d+)',
                                r'特價[^0-9]*\$?([0-9,]+)',
                            ]
                        else:
                            patterns = [
                                r'NT\$\s*([0-9,]+)',
                                r'\$\s*([0-9,]+)',
                                r'價格[：:\s]*([0-9,]+)',
                                r'售價[：:\s]*([0-9,]+)',
                            ]
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, content)
                            if matches:
                                # 取最常見的價格（避免抓到廣告價格）
                                price_candidates = [m for m in matches if m.replace(',', '').isdigit()]
                                if price_candidates:
                                    price_text = max(set(price_candidates), key=price_candidates.count)
                                    break
                    
                    # 清理和格式化價格
                    if price_text:
                        # 移除非數字字符但保留逗號和小數點
                        clean_price = re.sub(r'[^\d,.]', '', price_text.strip())
                        if clean_price and clean_price.replace(',', '').replace('.', '').isdigit():
                            # 格式化數字
                            try:
                                num = float(clean_price.replace(',', ''))
                                if num > 0 and num < 1000000:  # 合理的價格範圍
                                    result[platform] = f"{int(num):,} 元"
                                else:
                                    result[platform] = "價格異常"
                            except:
                                result[platform] = "價格格式錯誤"
                        else:
                            result[platform] = "查無價格"
                    else:
                        result[platform] = "查無價格"

                except Exception as e:
                    print(f"{platform} 錯誤: {str(e)}")
                    result[platform] = "抓取失敗"
                finally:
                    page.close()
                    context.close()

            browser.close()

        return jsonify(result)

    except Exception as e:
        print(f"整體錯誤: {str(e)}")
        return jsonify({'error': str(e)}), 500