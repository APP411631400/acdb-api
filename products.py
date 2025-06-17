from flask import Blueprint, request, jsonify
import pyodbc

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

import re, json, requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# ---------- momo -------------------------------------------------
def crawl_momo(url: str) -> str:
    try:
        i_code = re.search(r"i_code=(\d+)", url).group(1)
        api = f"https://m.momoshop.com.tw/exapp/api/v1/product/{i_code}?_dataVersion=V1.2.0"
        res = requests.get(api, headers={**HEADERS, "Referer": url}, timeout=6)
        price = res.json().get("price", {}).get("salePrice")
        return f"{price} 元" if price else "查無價格"
    except Exception as e:
        print("[momo] error →", e)
        return "爬蟲失敗"

# ---------- PChome ----------------------------------------------
def crawl_pchome(url: str) -> str:
    try:
        pid = url.rstrip("/").split("/")[-1].split("?")[0]
        api = f"https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/{pid}?fields=Price"
        res = requests.get(api, headers=HEADERS, timeout=6)
        price = res.json()[pid]["Price"]["P"]          # 現價
        return f"{price} 元" if price else "查無價格"
    except Exception as e:
        print("[pchome] error →", e)
        return "爬蟲失敗"

# ---------- 博客來 ----------------------------------------------
def crawl_books(url: str) -> str:
    try:
        soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=6).text, "html.parser")
        tag = soup.select_one("ul.price li strong") or soup.select_one("span.price")
        return tag.text.strip() if tag else "查無價格"
    except Exception as e:
        print("[books] error →", e)
        return "爬蟲失敗"

# ---------- Watsons ---------------------------------------------
def crawl_watsons(url: str) -> str:
    try:
        html = requests.get(url, headers=HEADERS, timeout=6).text
        m = re.search(r"window\.__NUXT__\s*=\s*(\{.*});", html)
        if not m:
            return "查無價格"
        data = json.loads(m.group(1))
        price = data["state"]["product"]["items"][0]["price"]        # 路徑已核對
        return f"{price} 元" if price else "查無價格"
    except Exception as e:
        print("[watsons] error →", e)
        return "爬蟲失敗"

# ---------- Cosmed ----------------------------------------------
def crawl_cosmed(url: str) -> str:
    try:
        html = requests.get(url, headers=HEADERS, timeout=6).text
        m = re.search(r"window\.__NUXT__\s*=\s*(\{.*});", html)
        if not m:
            return "查無價格"
        data = json.loads(m.group(1))
        price = data["state"]["product"]["data"]["Price"]            # 最新路徑
        return f"{price} 元" if price else "查無價格"
    except Exception as e:
        print("[cosmed] error →", e)
        return "爬蟲失敗"