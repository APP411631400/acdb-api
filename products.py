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
                    "--memory-pressure-off",
                    "--disable-images",
                    "--max_old_space_size=256"
                    
                ]
            )
            
            # 針對不同平台使用不同的 context 設定
            def create_context_for_platform(platform):
                if platform in ['momo', 'pchome']:
                    # momo 和 PChome 需要 JavaScript
                    return browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                        locale="zh-TW",
                        viewport={"width": 1920, "height": 1080},
                        java_script_enabled=True,
                        extra_http_headers={
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Cache-Control": "no-cache",
                            "Pragma": "no-cache",
                        }
                    )
                else:
                    # 其他平台保持原設定
                    return browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36"
                        ),
                        locale="zh-TW",
                        viewport={"width": 1024, "height": 768},
                        java_script_enabled=False
                    )

            # 專門處理 momo 的函數
            def scrape_momo_price(page, url):
                try:
                    print(f"正在抓取 momo: {url}")
                    
                    # 設定更長的 timeout 和等待條件
                    page.goto(url, timeout=60000, wait_until="networkidle")
                    
                    # 等待頁面完全載入
                    page.wait_for_timeout(3000)
                    
                    # momo 的多種價格選擇器（按優先順序）
                    selectors = [
                        # 主要價格區域
                        "span.price__main-value",
                        ".prdPrice",
                        ".price-value",
                        # 特價區域
                        ".o-price-promote",
                        ".o-price-promote__content",
                        # 其他可能的價格標籤
                        "[data-test-id='price-main']",
                        ".o-price__content",
                        ".prod-price",
                        ".price",
                        # 通用數字選擇器
                        "[class*='price'][class*='main']",
                        "[class*='price'][class*='value']"
                    ]
                    
                    for selector in selectors:
                        try:
                            element = page.locator(selector).first
                            if element.is_visible(timeout=5000):
                                price_text = element.text_content().strip()
                                if price_text and any(char.isdigit() for char in price_text):
                                    print(f"momo 找到價格: {price_text} (使用選擇器: {selector})")
                                    return price_text
                        except:
                            continue
                    
                    # 如果選擇器都失敗，嘗試正規表達式
                    content = page.content()
                    import re
                    
                    # 更精確的 momo 價格模式
                    price_patterns = [
                        r'價格[：:\s]*\$?([0-9,]+)',
                        r'售價[：:\s]*\$?([0-9,]+)',
                        r'NT\$\s*([0-9,]+)',
                        r'"price[^"]*"[^>]*>.*?\$?([0-9,]+)',
                        r'class="[^"]*price[^"]*"[^>]*>.*?([0-9,]+)',
                        r'\$([0-9,]+)',
                    ]
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            # 取最大的數字（通常是原價）
                            prices = [int(match.replace(',', '')) for match in matches if match.replace(',', '').isdigit()]
                            if prices:
                                max_price = max(prices)
                                print(f"momo 用正規表達式找到價格: {max_price}")
                                return str(max_price)
                    
                    return None
                    
                except Exception as e:
                    print(f"momo 錯誤: {str(e)}")
                    return None

            # 專門處理 PChome 的函數（改進版）
            def scrape_pchome_price(page, url):
                try:
                    print(f"正在抓取 PChome: {url}")
                    
                    page.goto(url, timeout=60000, wait_until="networkidle")
                    page.wait_for_timeout(2000)
                    
                    # 根據實際 PChome 頁面結構的選擇器，按優先順序排列
                    selectors = [
                        # PChome 24h 特價區域（紅色數字）
                        "span.price:not([style*='text-decoration'])",  # 沒有刪除線的價格
                        ".price:not(.original-price):not([style*='line-through'])",  # 排除原價
                        
                        # 常見的特價樣式
                        "[style*='color: red'] .price",
                        "[style*='color:#ff'] .price", 
                        ".sale-price",
                        ".special-price",
                        ".discount-price",
                        
                        # 一般價格選擇器
                        "span.price",
                        ".price-value", 
                        ".o-price__content",
                        ".prod-price",
                        ".price-txt",
                        ".money",
                        ".cost",
                        
                        # 數據屬性
                        "[data-price]",
                        "[data-value]",
                        
                        # 通用價格選擇器（最後嘗試）
                        "[class*='price']:not([class*='original']):not([class*='old'])"
                    ]
                    
                    # 收集所有可能的價格，並區分特價和原價
                    found_prices = []
                    special_prices = []  # 特價
                    regular_prices = []  # 一般價格
                    
                    # 收集所有可能的價格
                    for selector in selectors:
                        try:
                            elements = page.locator(selector).all()
                            for element in elements:
                                if element.is_visible():
                                    price_text = element.text_content().strip()
                                    
                                    # 基本過濾
                                    if not price_text or not any(char.isdigit() for char in price_text):
                                        continue
                                    if len(price_text) > 20 or '評價' in price_text or '商品' in price_text:
                                        continue
                                    
                                    # 檢查是否為刪除線樣式（原價）
                                    try:
                                        style = element.get_attribute('style') or ''
                                        parent_style = element.locator('..').get_attribute('style') or ''
                                        
                                        is_strikethrough = (
                                            'text-decoration' in style and 'line-through' in style
                                        ) or (
                                            'text-decoration' in parent_style and 'line-through' in parent_style
                                        )
                                    except:
                                        is_strikethrough = False
                                    
                                    # 提取數字
                                    import re
                                    numbers = re.findall(r'[0-9,]+', price_text)
                                    for num_str in numbers:
                                        try:
                                            num = int(num_str.replace(',', ''))
                                            # 合理的價格範圍過濾
                                            if 10 <= num <= 999999:
                                                found_prices.append(num)
                                                
                                                # 分類特價和原價
                                                if is_strikethrough:
                                                    regular_prices.append(num)
                                                else:
                                                    special_prices.append(num)
                                        except:
                                            continue
                        except:
                            continue
                    
                    # 智能選擇價格
                    if found_prices:
                        # 優先使用特價（非刪除線的價格）
                        if special_prices:
                            unique_special = sorted(list(set(special_prices)))
                            if len(unique_special) == 1:
                                print(f"PChome 找到特價: {unique_special[0]}")
                                return str(unique_special[0])
                            else:
                                # 多個特價，取最低的
                                min_special = min(unique_special)
                                print(f"PChome 找到多個特價 {unique_special}，取最低: {min_special}")
                                return str(min_special)
                        
                        # 去重並排序所有價格
                        unique_prices = sorted(list(set(found_prices)))
                        
                        # 如果只有一個價格，直接回傳
                        if len(unique_prices) == 1:
                            print(f"PChome 找到單一價格: {unique_prices[0]}")
                            return str(unique_prices[0])
                        
                        # 如果有多個價格，判斷邏輯：
                        # 1. 檢查是否有明顯的特價/原價組合
                        if len(unique_prices) == 2:
                            lower, higher = unique_prices[0], unique_prices[1]
                            
                            # 如果較低價格是較高價格的 50%-95%，很可能是特價
                            ratio = lower / higher
                            if 0.5 <= ratio <= 0.95:
                                print(f"PChome 發現特價組合 {lower}/{higher}，取特價: {lower}")
                                return str(lower)
                        
                        # 2. 如果有很多相似的價格，可能是重複顯示，取最常出現的
                        from collections import Counter
                        counter = Counter(found_prices)
                        most_common_price, count = counter.most_common(1)[0]
                        
                        if count >= 2:  # 如果同一價格出現2次以上
                            print(f"PChome 找到重複價格: {most_common_price} (出現{count}次)")
                            return str(most_common_price)
                        
                        # 3. 否則取最小值（通常是特價）
                        min_price = min(unique_prices)
                        print(f"PChome 找到多個價格 {unique_prices}，取最低價: {min_price}")
                        return str(min_price)
                    
                    # 如果選擇器都沒找到，用正規表達式從頁面內容中尋找
                    content = page.content()
                    import re
                    
                    price_patterns = [
                        # 更精確的 PChome 價格模式
                        r'特價[：:\s]*NT?\$?\s*([0-9,]+)',
                        r'售價[：:\s]*NT?\$?\s*([0-9,]+)', 
                        r'price["\']:\s*["\']?([0-9,]+)',
                        r'NT\$\s*([0-9,]+)',
                        r'\$([0-9,]+)(?!\d)',  # 避免連續數字
                        r'([0-9,]+)\s*元',
                    ]
                    
                    regex_prices = []
                    for pattern in price_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches:
                            try:
                                num = int(match.replace(',', ''))
                                if 10 <= num <= 999999:  # 合理價格範圍
                                    regex_prices.append(num)
                            except:
                                continue
                    
                    if regex_prices:
                        # 同樣的邏輯處理正規表達式找到的價格
                        unique_regex_prices = sorted(list(set(regex_prices)))
                        
                        if len(unique_regex_prices) == 1:
                            price = unique_regex_prices[0]
                            print(f"PChome 用正規表達式找到價格: {price}")
                            return str(price)
                        else:
                            # 取最小值或最常出現的
                            from collections import Counter
                            counter = Counter(regex_prices)
                            most_common_price = counter.most_common(1)[0][0]
                            print(f"PChome 用正規表達式找到價格: {most_common_price}")
                            return str(most_common_price)
                    
                    return None
                    
                except Exception as e:
                    print(f"PChome 錯誤: {str(e)}")
                    return None

            # 處理每個平台
            for platform, url in urls.items():
                if not url or not url.startswith("http"):
                    result[platform] = "無"
                    continue

                context = create_context_for_platform(platform)
                
                # 反檢測腳本
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-TW', 'zh', 'en']});
                """)

                page = context.new_page()
                
                try:
                    if platform == 'momo':
                        price_text = scrape_momo_price(page, url)
                    elif platform == 'pchome':
                        price_text = scrape_pchome_price(page, url)
                    else:
                        # 其他平台保持原邏輯
                        print(f"正在抓取 {platform}: {url}")
                        page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        time.sleep(2)
                        
                        # 各平台的 selector 邏輯（原本的邏輯）
                        price_text = None
                        
                        if platform == '博客來':
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
                            content = page.content()
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
                    
                    # 清理並格式化價格
                    if price_text:
                        import re
                        num = re.sub(r'[^0-9.]', '', price_text.strip())
                        if num:
                            result[platform] = f"{num} 元"
                        else:
                            result[platform] = "查無價格"
                    else:
                        result[platform] = "查無價格"

                except Exception as e:
                    print(f"{platform} 錯誤: {str(e)}")
                    result[platform] = f"錯誤: {str(e)[:50]}"
                finally:
                    page.close()
                    context.close()

            browser.close()

        return jsonify(result)

    except Exception as e:
        print(f"整體錯誤: {str(e)}")
        return jsonify({'error': str(e)}), 500