from flask import Blueprint, request, jsonify
import pyodbc

products = Blueprint('products', __name__)

# ✅ 資料庫連線設定
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888"
)

# ✅ 取得所有比價商品資料（前端顯示用）
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


# ✅ 即時價格比價（根據商品 ID 爬五家價格）
@products.route('/product_detail', methods=['GET'])
def get_product_detail():
    product_id = request.args.get("id", "")
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 商品名稱,
                   momo_網址, pchome_網址, 博客來_網址, 屈臣氏_網址, 康是美_網址
            FROM dbo.比價商品
            WHERE 商品ID = ?
        """, (product_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': '查無此商品'}), 404

        name, momo_url, pchome_url, books_url, watsons_url, cosmed_url = row

        # ✅ 回傳即時價格（不儲存資料庫，只做查詢）
        result = {
            "商品ID": product_id,
            "商品名稱": name,
            "momo": crawl_momo(momo_url) if momo_url else "無",
            "pchome": crawl_pchome(pchome_url) if pchome_url else "無",
            "博客來": crawl_books(books_url) if books_url else "無",
            "屈臣氏": crawl_watsons(watsons_url) if watsons_url else "無",
            "康是美": crawl_cosmed(cosmed_url) if cosmed_url else "無"
        }

        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -------------------- ⬇⬇⬇ 爬蟲函式區 ⬇⬇⬇ --------------------

import requests
from bs4 import BeautifulSoup
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0 Safari/537.36"
}

# ✅ momo 商品價格 API 爬蟲
def crawl_momo(url):
    try:
        i_code = url.split("i_code=")[-1].split("&")[0]
        api_url = f"https://m.momoshop.com.tw/exapp/api/v1/product/{i_code}?_dataVersion=V1.2.0"
        res = requests.get(api_url, headers=headers, timeout=5)
        data = res.json()
        price = data.get("price", {}).get("salePrice")
        return f"{price} 元" if price else "查無價格"
    except Exception as e:
        print(f"[momo 爬蟲錯誤] {e}")
        return "爬蟲失敗"

# ✅ pchome 商品價格 API 爬蟲
def crawl_pchome(url):
    try:
        product_id = url.split("/")[-1]
        api_url = f"https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/{product_id}&fields=Price"
        res = requests.get(api_url, headers=headers, timeout=5)
        data = res.json()
        price = data[product_id]["Price"]["P"]
        return f"{price} 元" if price else "查無價格"
    except Exception as e:
        print(f"[pchome 爬蟲錯誤] {e}")
        return "爬蟲失敗"

# ✅ 博客來（靜態 HTML 抓價格）
def crawl_books(url):
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        price_tag = soup.select_one("ul.price li strong") or soup.select_one("span.price")
        return price_tag.text.strip() if price_tag else "查無價格"
    except Exception as e:
        print(f"[books 爬蟲錯誤] {e}")
        return "爬蟲失敗"

# ✅ 屈臣氏：價格藏在 script JSON 裡（需解析 window.__NUXT__）
def crawl_watsons(url):
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        script_tag = soup.find("script", text=lambda t: t and "__NUXT__" in t)
        if script_tag:
            text = script_tag.string or ""
            json_str = text.split("window.__NUXT__=")[-1].rsplit(";</script>", 1)[0]
            data = json.loads(json_str)
            # 找價格：會隨結構變動
            price = data["state"]["product"]["items"][0]["price"]
            return f"{price} 元" if price else "查無價格"
        return "查無價格"
    except Exception as e:
        print(f"[watsons 爬蟲錯誤] {e}")
        return "爬蟲失敗"

# ✅ 康是美：價格在 window.__NUXT__ JSON 內
def crawl_cosmed(url):
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        script_tag = soup.find("script", text=lambda t: t and "__NUXT__=" in t)
        if script_tag:
            text = script_tag.string or ""
            json_str = text.split("window.__NUXT__=")[-1].rsplit(";</script>", 1)[0]
            data = json.loads(json_str)
            price = data["state"]["product"]["productSalePrice"]
            return f"{price} 元" if price else "查無價格"
        return "查無價格"
    except Exception as e:
        print(f"[cosmed 爬蟲錯誤] {e}")
        return "爬蟲失敗"

