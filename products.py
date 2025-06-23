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


# ✅ 取得比價商品資料（前端顯示）
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

            # 強化的 momo 爬蟲 - 反反爬蟲版本
            def scrape_momo_price_enhanced(page, url):
                try:
                    print(f"正在抓取 momo: {url}")
                    
                    # 第一步：設定更多反檢測腳本
                    page.add_init_script("""
                        // 移除 webdriver 痕跡
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        
                        // 偽造 plugins
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });
                        
                        // 偽造 languages
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['zh-TW', 'zh', 'en-US', 'en']
                        });
                        
                        // 偽造 permissions
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                            parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                        );
                        
                        // 偽造 chrome 對象
                        window.chrome = {
                            runtime: {},
                            loadTimes: function() {},
                            csi: function() {},
                            app: {}
                        };
                        
                        // 移除 _phantom, callPhantom 等
                        delete window._phantom;
                        delete window.callPhantom;
                        
                        // 覆蓋 console.debug
                        console.debug = () => {};
                    """)
                    
                    # 設定 cookies (模擬正常用戶)
                    page.context.add_cookies([
                        {
                            'name': 'devicePixelRatio',
                            'value': '1',
                            'domain': '.momoshop.com.tw',
                            'path': '/'
                        },
                        {
                            'name': 'city',
                            'value': '6',
                            'domain': '.momoshop.com.tw', 
                            'path': '/'
                        }
                    ])
                    
                    # 隨機延遲
                    import random
                    time.sleep(random.uniform(1, 3))
                    
                    # 第二步：訪問首頁建立 session
                    print("先訪問 momo 首頁...")
                    page.goto("https://www.momoshop.com.tw/", timeout=30000, wait_until="networkidle")
                    time.sleep(random.uniform(2, 4))
                    
                    # 第三步：再訪問目標頁面
                    print("訪問商品頁面...")
                    page.goto(url, timeout=60000, wait_until="networkidle")
                    
                    # 等待更長時間讓頁面完全載入
                    time.sleep(random.uniform(3, 6))
                    
                    # 模擬人類行為：滾動頁面
                    page.evaluate("window.scrollTo(0, 500)")
                    time.sleep(1)
                    page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(1)
                    
                    # 檢查頁面是否被阻擋
                    page_content = page.content()
                    if '系統偵測' in page_content or '安全驗證' in page_content or len(page_content) < 1000:
                        print("頁面可能被反爬蟲系統阻擋")
                        return None
                    
                    # 嘗試多種方式抓取價格
                    
                    # 方式1：直接找價格元素
                    price_selectors = [
                        # 基於截圖的精確選擇器
                        'span[style*="color: rgb(255, 51, 51)"]',  # 紅色促銷價
                        '.prdPrice .price',
                        '.prdPrice span:last-child',
                        
                        # 常見的價格選擇器
                        'span.price__main-value',
                        '.price-value',
                        '.o-price__content',
                        '.prod-price',
                        
                        # 更通用的選擇器
                        'span:has-text("元")',
                        'div:has-text("元")',
                        '[class*="price"]',
                    ]
                    
                    for selector in price_selectors:
                        try:
                            elements = page.locator(selector).all()
                            for element in elements:
                                if element.is_visible():
                                    text = element.text_content().strip()
                                    if text and '元' in text:
                                        # 提取數字
                                        import re
                                        numbers = re.findall(r'\d+', text)
                                        if numbers:
                                            price = max([int(n) for n in numbers])
                                            if 10 <= price <= 99999:  # 合理價格範圍
                                                print(f"方式1找到價格: {text} -> {price}")
                                                return str(price)
                        except Exception as e:
                            continue
                    
                    # 方式2：JavaScript 執行抓取
                    try:
                        price_js = page.evaluate("""
                            () => {
                                // 找所有包含數字和'元'的文字
                                const walker = document.createTreeWalker(
                                    document.body,
                                    NodeFilter.SHOW_TEXT,
                                    null,
                                    false
                                );
                                
                                const prices = [];
                                let node;
                                
                                while (node = walker.nextNode()) {
                                    const text = node.textContent.trim();
                                    if (text.includes('元') && /\\d/.test(text)) {
                                        const numbers = text.match(/\\d+/g);
                                        if (numbers) {
                                            for (let num of numbers) {
                                                const price = parseInt(num);
                                                if (price >= 10 && price <= 99999) {
                                                    prices.push(price);
                                                }
                                            }
                                        }
                                    }
                                }
                                
                                // 返回最常出現的價格
                                if (prices.length > 0) {
                                    const counts = {};
                                    prices.forEach(p => counts[p] = (counts[p] || 0) + 1);
                                    
                                    let maxCount = 0;
                                    let mostCommon = prices[0];
                                    
                                    for (let price in counts) {
                                        if (counts[price] > maxCount) {
                                            maxCount = counts[price];
                                            mostCommon = parseInt(price);
                                        }
                                    }
                                    
                                    return mostCommon;
                                }
                                
                                return null;
                            }
                        """)
                        
                        if price_js:
                            print(f"方式2找到價格: {price_js}")
                            return str(price_js)
                            
                    except Exception as e:
                        print(f"JavaScript 執行失敗: {e}")
                    
                    # 方式3：正規表達式在完整 HTML 中搜尋
                    import re
                    
                    # 先解碼可能的亂碼
                    try:
                        # 如果是 UTF-8 編碼問題
                        content_bytes = page_content.encode('latin1')
                        decoded_content = content_bytes.decode('utf-8', errors='ignore')
                    except:
                        decoded_content = page_content
                    
                    price_patterns = [
                        r'促銷價[^0-9]*?(\d+)[^0-9]*?元',
                        r'售價[^0-9]*?(\d+)[^0-9]*?元',
                        r'價格[^0-9]*?(\d+)[^0-9]*?元',
                        r'NT\$[^0-9]*?(\d+)',
                        r'>(\d+)<[^>]*元',
                        r'(\d+)\s*元',
                        r'"price"[^}]*?(\d+)',
                        r'"salePrice"[^}]*?(\d+)',
                    ]
                    
                    all_found_prices = []
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, decoded_content, re.IGNORECASE)
                        for match in matches:
                            try:
                                price = int(match)
                                if 10 <= price <= 99999:
                                    all_found_prices.append(price)
                            except:
                                continue
                    
                    if all_found_prices:
                        # 統計頻率，選擇最可能的價格
                        from collections import Counter
                        price_counts = Counter(all_found_prices)
                        most_common = price_counts.most_common(1)[0]
                        print(f"方式3找到價格: {all_found_prices} -> 選擇: {most_common[0]}")
                        return str(most_common[0])
                    
                    print("所有方式都無法找到價格")
                    return None
                    
                except Exception as e:
                    print(f"momo 抓取失敗: {str(e)}")
                    return None
                    
                    # 專門為 momo 優化的 context 設定
            def create_momo_context(browser):
                """為 momo 創建專門的 context，加強反檢測"""
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="zh-TW",
                    timezone_id="Asia/Taipei",
                    viewport={"width": 1920, "height": 1080},
                    java_script_enabled=True,
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )
                
                return context

            # 修正後的 PChome 價格清理函數
            def clean_pchome_price(price_text):
                """處理 PChome 特價和劃線原價被一起抓取的問題"""
                import re
                
                # 移除非數字字符
                numbers_only = re.sub(r'[^0-9]', '', price_text)
                
                # 如果數字太短，直接返回
                if len(numbers_only) < 3:
                    return numbers_only
                
                # 檢查是否為重複數字（如 268268）
                if len(numbers_only) >= 6 and len(numbers_only) % 2 == 0:
                    half = len(numbers_only) // 2
                    first_half = numbers_only[:half]
                    second_half = numbers_only[half:]
                    
                    # 如果兩半完全相同，就是重複價格，取一個
                    if first_half == second_half and first_half.isdigit():
                        return first_half
                
                # 如果長度是6位數且可能是兩個3位數價格（如 179195）
                if len(numbers_only) == 6:
                    # 嘗試分割成兩個3位數
                    left_3 = numbers_only[:3]
                    right_3 = numbers_only[3:]
                    
                    # 檢查是否都是合理的價格範圍（100-999）
                    if (left_3.isdigit() and right_3.isdigit() and
                        100 <= int(left_3) <= 999 and 100 <= int(right_3) <= 999):
                        # 取較小的作為特價
                        return left_3 if int(left_3) < int(right_3) else right_3
                
                # 如果長度是5位數，可能是兩個不等長的價格
                elif len(numbers_only) == 5:
                    # 嘗試分割方式：2+3 或 3+2
                    splits = [
                        (numbers_only[:2], numbers_only[2:]),  # 2+3: 17|195 (X)
                        (numbers_only[:3], numbers_only[3:])   # 3+2: 179|95 (X)
                    ]
                    
                    for left_part, right_part in splits:
                        if (left_part.isdigit() and right_part.isdigit()):
                            left_val = int(left_part)
                            right_val = int(right_part)
                            
                            # 更嚴格的判斷：避免不合理的分割
                            # 2位數價格必須 >= 50，3位數價格必須 >= 100
                            if len(left_part) == 2 and left_val < 50:
                                continue
                            if len(left_part) == 3 and left_val < 100:
                                continue
                            if len(right_part) == 2 and right_val < 50:
                                continue
                            if len(right_part) == 3 and right_val < 100:
                                continue
                            
                            # 取較小的作為特價
                            return left_part if left_val < right_val else right_part
                
                # 如果是4位數，檢查是否是兩個2位數（不太可能，但以防萬一）
                elif len(numbers_only) == 4:
                    left_2 = numbers_only[:2]
                    right_2 = numbers_only[2:]
                    
                    if (left_2.isdigit() and right_2.isdigit() and
                        int(left_2) >= 50 and int(right_2) >= 50):
                        return left_2 if int(left_2) < int(right_2) else right_2
                
                # 其他情況：如果是正常的價格長度（3-4位），直接返回
                if 3 <= len(numbers_only) <= 4:
                    return numbers_only
                
                # 如果是很長的數字，可能包含多個價格，嘗試找最短的合理價格
                if len(numbers_only) > 6:
                    # 從左到右找3-4位數的合理價格
                    for start in range(len(numbers_only) - 2):
                        for length in [3, 4]:
                            if start + length <= len(numbers_only):
                                candidate = numbers_only[start:start + length]
                                if candidate.isdigit() and 100 <= int(candidate) <= 9999:
                                    return candidate
                
                # 最後手段：直接返回原數字
                return numbers_only


            # 完整的 PChome 抓取函數
            def scrape_pchome_price(page, url):
                try:
                    print(f"正在抓取 PChome: {url}")
                    
                    page.goto(url, timeout=60000, wait_until="networkidle")
                    page.wait_for_timeout(2000)
                    
                    # PChome 的多種價格選擇器
                    selectors = [
                        # 24h 購物的價格
                        "span.price",
                        ".price-value",
                        ".o-price__content",
                        # 商店街的價格
                        ".prod-price",
                        ".price-txt",
                        # 其他可能的標籤
                        "[class*='price']",
                        ".money",
                        ".cost",
                        # 數據屬性
                        "[data-price]",
                        "[data-value]"
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = page.locator(selector).all()
                            for element in elements:
                                if element.is_visible():
                                    price_text = element.text_content().strip()
                                    if price_text and any(char.isdigit() for char in price_text):
                                        # 排除一些不是價格的文字
                                        if len(price_text) > 20 or '評價' in price_text or '商品' in price_text:
                                            continue
                                        
                                        # 使用修正後的價格清理函數
                                        cleaned_price = clean_pchome_price(price_text)
                                        print(f"PChome 找到價格: {price_text} -> 清理後: {cleaned_price} (使用選擇器: {selector})")
                                        return cleaned_price
                        except:
                            continue
                    
                    # 正規表達式備用方案
                    content = page.content()
                    import re
                    
                    price_patterns = [
                        r'price["\']:\s*["\']?([0-9,]+)',
                        r'售價[：:\s]*\$?([0-9,]+)',
                        r'NT\$\s*([0-9,]+)',
                        r'\$([0-9,]+)',
                        r'([0-9,]+)\s*元',
                    ]
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            # 取最常見的價格
                            from collections import Counter
                            counter = Counter(matches)
                            most_common = counter.most_common(1)
                            if most_common:
                                price = most_common[0][0]
                                
                                # 使用修正後的價格清理函數
                                cleaned_price = clean_pchome_price(price)
                                print(f"PChome 用正規表達式找到價格: {price} -> 清理後: {cleaned_price}")
                                return cleaned_price
                    
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