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

            # 專門處理 momo 的函數 (修正版)
            def scrape_momo_price(page, url):
                try:
                    print(f"正在抓取 momo: {url}")
                    
                    # 設定更長的 timeout 和等待條件
                    page.goto(url, timeout=60000, wait_until="networkidle")
                    
                    # 等待頁面完全載入
                    page.wait_for_timeout(3000)
                    
                    # 根據截圖，momo 的價格結構優化後的選擇器
                    selectors = [
                        # 促銷價格 (優先抓取，通常是實際售價)
                        "span:has-text('促銷價') + span",
                        ".prdPrice .price",
                        "span[style*='color: rgb(255, 51, 51)']",  # 紅色價格文字
                        
                        # 主要價格區域
                        ".prdPrice",
                        ".price-value", 
                        "span.price__main-value",
                        
                        # 市售價 (備用)
                        "span:has-text('市售價') + span",
                        
                        # 其他可能的價格標籤
                        "[data-test-id='price-main']",
                        ".o-price__content",
                        ".prod-price",
                        ".price",
                        
                        # 通用數字選擇器
                        "[class*='price'][class*='main']",
                        "[class*='price'][class*='value']",
                        
                        # 根據截圖的具體結構
                        "span:contains('元')",
                        "strong:contains('元')",
                    ]
                    
                    # 先嘗試找促銷價格
                    for selector in selectors:
                        try:
                            elements = page.locator(selector).all()
                            for element in elements:
                                if element.is_visible(timeout=2000):
                                    price_text = element.text_content().strip()
                                    
                                    # 檢查是否包含數字和元
                                    if price_text and ('元' in price_text or any(char.isdigit() for char in price_text)):
                                        # 排除一些不是價格的文字
                                        exclude_keywords = ['評價', '商品', '運費', '免運', '滿', '折扣', '優惠', '回饋']
                                        if any(keyword in price_text for keyword in exclude_keywords):
                                            continue
                                        
                                        # 提取數字
                                        import re
                                        numbers = re.findall(r'\d+', price_text)
                                        if numbers:
                                            # 取最大的數字（通常是價格）
                                            price_num = max([int(num) for num in numbers])
                                            
                                            # 合理價格範圍檢查 (10-99999元)
                                            if 10 <= price_num <= 99999:
                                                print(f"momo 找到價格: {price_text} -> {price_num} (使用選擇器: {selector})")
                                                return str(price_num)
                                    
                        except Exception as e:
                            print(f"選擇器 {selector} 失敗: {e}")
                            continue
                    
                    # 如果選擇器都失敗，嘗試更精確的正規表達式
                    print("嘗試使用正規表達式...")
                    content = page.content()
                    
                    # 更精確的 momo 價格模式
                    price_patterns = [
                        # 促銷價格模式
                        r'促銷價[^>]*?(\d+)\s*元',
                        r'特價[^>]*?(\d+)\s*元',
                        
                        # 一般價格模式
                        r'售價[：:\s]*(\d+)\s*元',
                        r'價格[：:\s]*(\d+)\s*元',
                        r'NT\$\s*(\d+)',
                        r'\$\s*(\d+)',
                        
                        # 數字+元的模式
                        r'(\d+)\s*元',
                        
                        # JSON 資料中的價格
                        r'"price"[^}]*?(\d+)',
                        r'"salePrice"[^}]*?(\d+)',
                        r'"marketPrice"[^}]*?(\d+)',
                    ]
                    
                    found_prices = []
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                        for match in matches:
                            price_num = int(match)
                            # 合理價格範圍檢查
                            if 10 <= price_num <= 99999:
                                found_prices.append(price_num)
                    
                    if found_prices:
                        # 移除重複並排序
                        unique_prices = list(set(found_prices))
                        unique_prices.sort()
                        
                        # 通常促銷價會比市售價小，選擇較小的價格
                        final_price = min(unique_prices)
                        print(f"momo 用正規表達式找到價格: {found_prices} -> 選擇: {final_price}")
                        return str(final_price)
                    
                    # 最後嘗試：直接搜尋頁面中的所有數字，找出最可能的價格
                    print("最後嘗試：分析頁面中的所有數字...")
                    all_numbers = re.findall(r'\b(\d{2,4})\b', content)
                    
                    if all_numbers:
                        # 轉換為整數並過濾合理範圍
                        valid_prices = []
                        for num_str in all_numbers:
                            num = int(num_str)
                            if 50 <= num <= 9999:  # 合理的商品價格範圍
                                valid_prices.append(num)
                        
                        if valid_prices:
                            # 統計出現頻率，選擇出現最多次的價格
                            from collections import Counter
                            price_counts = Counter(valid_prices)
                            most_common_prices = price_counts.most_common(5)
                            
                            print(f"最常出現的價格: {most_common_prices}")
                            
                            # 選擇最常出現的合理價格
                            for price, count in most_common_prices:
                                if count >= 2 and 100 <= price <= 9999:  # 至少出現2次的合理價格
                                    print(f"momo 選擇最常出現的價格: {price}")
                                    return str(price)
                    
                    print("momo 未找到任何有效價格")
                    return None
                    
                except Exception as e:
                    print(f"momo 錯誤: {str(e)}")
                    return None

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