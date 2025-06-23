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


def extract_momo_product_id(url):
    """從 momo URL 提取商品 ID"""
    try:
        # momo URL 格式: https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code=商品ID
        parsed = urlparse(url)
        if 'momoshop.com.tw' in parsed.netloc:
            params = parse_qs(parsed.query)
            if 'i_code' in params:
                return params['i_code'][0]
    except:
        pass
    return None

def extract_pchome_product_id(url):
    """從 PChome URL 提取商品 ID"""
    try:
        # PChome URL 格式: https://24h.pchome.com.tw/prod/商品ID
        parsed = urlparse(url)
        if 'pchome.com.tw' in parsed.netloc:
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part and len(part) > 5:  # 商品ID通常較長
                    return part
    except:
        pass
    return None

def get_momo_price_by_api(product_url):
    """使用 momo API 獲取價格"""
    try:
        product_id = extract_momo_product_id(product_url)
        if not product_id:
            return "無法解析商品ID"
        
        # momo API endpoint (可能需要調整)
        api_urls = [
            f"https://www.momoshop.com.tw/ajax/GetProductDetail.ashx?i_code={product_id}",
            f"https://www.momoshop.com.tw/ajax/product/GetProductDetail.ashx?i_code={product_id}",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://www.momoshop.com.tw/',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        for api_url in api_urls:
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    # 嘗試不同的價格欄位
                    price_fields = ['SalePrice', 'Price', 'sellPrice', 'price', 'finalPrice']
                    for field in price_fields:
                        if field in data and data[field]:
                            return f"{data[field]} 元"
                    
                    # 如果JSON結構複雜，遞迴搜尋價格
                    def find_price_in_dict(obj, depth=0):
                        if depth > 3:  # 避免無限遞迴
                            return None
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if any(keyword in key.lower() for keyword in ['price', '價格', 'amount']):
                                    if isinstance(value, (int, float)) and value > 0:
                                        return value
                                elif isinstance(value, (dict, list)):
                                    result = find_price_in_dict(value, depth + 1)
                                    if result:
                                        return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_price_in_dict(item, depth + 1)
                                if result:
                                    return result
                        return None
                    
                    price = find_price_in_dict(data)
                    if price:
                        return f"{price} 元"
                        
            except Exception as e:
                print(f"momo API {api_url} 錯誤: {e}")
                continue
        
        return "API無法獲取價格"
        
    except Exception as e:
        return f"momo API錯誤: {str(e)[:50]}"

def get_pchome_price_by_api(product_url):
    """使用 PChome API 獲取價格"""
    try:
        product_id = extract_pchome_product_id(product_url)
        if not product_id:
            return "無法解析商品ID"
        
        # PChome API endpoints
        api_urls = [
            f"https://ecapi.pchome.com.tw/ecservice/product/v1/product/{product_id}",
            f"https://ecapi-cdn.pchome.com.tw/cdn/ecservice/product/v1/product/{product_id}",
            f"https://24h.pchome.com.tw/api/prod/{product_id}",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://24h.pchome.com.tw/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8'
        }
        
        for api_url in api_urls:
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    # PChome 常見的價格欄位
                    price_paths = [
                        ['Price'],
                        ['SalePrice'], 
                        ['price'],
                        ['data', 'price'],
                        ['data', 'Price'],
                        ['product', 'price'],
                        ['result', 'price'],
                    ]
                    
                    for path in price_paths:
                        try:
                            value = data
                            for key in path:
                                value = value[key]
                            if isinstance(value, (int, float)) and value > 0:
                                return f"{value} 元"
                        except (KeyError, TypeError):
                            continue
                    
                    # 深度搜尋價格
                    def find_price_recursive(obj, depth=0):
                        if depth > 4:
                            return None
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if 'price' in key.lower() and isinstance(value, (int, float)) and value > 0:
                                    return value
                                elif isinstance(value, (dict, list)):
                                    result = find_price_recursive(value, depth + 1)
                                    if result:
                                        return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_price_recursive(item, depth + 1)
                                if result:
                                    return result
                        return None
                    
                    price = find_price_recursive(data)
                    if price:
                        return f"{price} 元"
                        
            except Exception as e:
                print(f"PChome API {api_url} 錯誤: {e}")
                continue
        
        return "API無法獲取價格"
        
    except Exception as e:
        return f"PChome API錯誤: {str(e)[:50]}"

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
        
        # 2. 處理 momo 和 PChome - 優先使用 API
        print("開始處理 momo 和 PChome...")
        
        # momo
        if momo_url and momo_url.startswith("http"):
            print(f"正在用API抓取 momo: {momo_url}")
            momo_price = get_momo_price_by_api(momo_url)
            result['momo'] = momo_price
        else:
            result['momo'] = "無"
        
        # PChome    
        if pchome_url and pchome_url.startswith("http"):
            print(f"正在用API抓取 PChome: {pchome_url}")
            pchome_price = get_pchome_price_by_api(pchome_url)
            result['pchome'] = pchome_price
        else:
            result['pchome'] = "無"

        # 3. 其他平台用 Playwright（博客來、屈臣氏、康是美）
        other_urls = {
            '博客來': books_url,
            '屈臣氏': watsons_url,
            '康是美': cosmed_url,
        }
        
        print("開始處理其他平台...")
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
                    "--disable-images",
                    "--memory-pressure-off",
                    "--max_old_space_size=4096"
                ]
            )
            
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                locale="zh-TW",
                viewport={"width": 1024, "height": 768},
                java_script_enabled=True  # 這些網站可能需要JS
            )

            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            for platform, url in other_urls.items():
                if not url or not url.startswith("http"):
                    result[platform] = "無"
                    continue

                page = context.new_page()
                try:
                    print(f"正在抓取 {platform}: {url}")
                    
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    time.sleep(3)  # 等待JS渲染
                    
                    content = page.content()
                    print(f"{platform} 頁面長度: {len(content)}")
                    
                    price_text = None
                    
                    if platform == '博客來':
                        selectors = [
                            "ul.price li strong",
                            "span.price",
                            ".price-tag",
                            ".price"
                        ]
                        
                    elif platform == '屈臣氏':
                        selectors = [
                            ".price-value",
                            ".productPrice", 
                            ".price",
                            "[data-testid='price']"
                        ]
                        
                    else:  # 康是美
                        selectors = [
                            ".prod-sale-price",
                            ".price",
                            ".product-price",
                            ".sale-price"
                        ]
                    
                    # 嘗試多個選擇器
                    for selector in selectors:
                        try:
                            element = page.locator(selector).first
                            if element.is_visible():
                                price_text = element.text_content()
                                if price_text and price_text.strip():
                                    break
                        except:
                            continue
                    
                    # 正規表達式搜尋
                    if not price_text:
                        price_patterns = [
                            r'NT\$\s*([0-9,]+)',
                            r'\$\s*([0-9,]+)', 
                            r'價格[：:\s]*([0-9,]+)',
                            r'售價[：:\s]*([0-9,]+)',
                            r'定價[：:\s]*([0-9,]+)',
                        ]
                        
                        for pattern in price_patterns:
                            match = re.search(pattern, content)
                            if match:
                                price_text = match.group(1)
                                break
                    
                    # 清理並格式化價格
                    if price_text:
                        num = re.sub(r'[^0-9.]', '', price_text.strip())
                        if num and float(num) > 0:
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

        print("所有平台處理完成")
        return jsonify(result)

    except Exception as e:
        print(f"整體錯誤: {str(e)}")
        return jsonify({'error': str(e)}), 500