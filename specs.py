# specs.py
from flask import Blueprint, request, jsonify
import pyodbc
import re

# 建立 Blueprint 模組
specs_bp = Blueprint('specs', __name__)

# ✅ SQL Server 連線設定（記得保密帳密）
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem666.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888;"
)

# --------- 小工具：名稱規格化，降低兩表名稱差異 ----------
def _normalize_name(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u3000", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[|｜/／\-–—•・☆★【】\[\]\(\)（）:：,，．。\.]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# ✅ 取得產品主資料（只讀 Products 表，依名稱模糊）
@specs_bp.route("/product/info", methods=["GET"])
def get_product_info():
    product_name = request.args.get("name", "").strip()
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ProductID, ProductName, Brand, ProductURL, ImageURL, Category, SubCategory, Vendor
            FROM dbo.Products
            WHERE ProductName LIKE ?
        """, (f"%{product_name}%",))
        rows = cursor.fetchall()
        conn.close()

        result = [
            {
                "ProductID": row.ProductID,
                "ProductName": row.ProductName,
                "Brand": row.Brand,
                "ProductURL": row.ProductURL,
                "ImageURL": row.ImageURL,
                "Category": row.Category,
                "SubCategory": row.SubCategory,
                "Vendor": row.Vendor
            }
            for row in rows
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ 根據 ProductID（數字）取得「商品 + 規格」
#   作法：Products 找 ProductName → ProductSpecs 依名稱查（=、LIKE、關鍵字 AND）
@specs_bp.route("/product/specs/id", methods=["GET"])
def get_specs_by_id():
    pid = (request.args.get("id", "") or "").strip()
    if not pid.isdigit():
        return jsonify({"error": "id 必須是整數的 ProductID"}), 400

    try:
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        # A. 先用 ProductID 抓主檔（Products）
        cur.execute("""
            SELECT ProductID, ProductName, Brand, ProductURL, ImageURL, Category, SubCategory, Vendor
            FROM dbo.Products
            WHERE ProductID = ?
        """, (int(pid),))
        p = cur.fetchone()
        if not p:
            conn.close()
            return jsonify({"error": f"找不到 ProductID={pid} 的商品"}), 404

        product = {
            "ProductID": p.ProductID,
            "ProductName": p.ProductName,
            "Brand": p.Brand,
            "ProductURL": p.ProductURL,
            "ImageURL": p.ImageURL,
            "Category": p.Category,
            "SubCategory": p.SubCategory,
            "Vendor": p.Vendor
        }

        # B. 用名稱去 ProductSpecs 找規格
        specs = []

        # B1. 名稱完全相等
        cur.execute("""
            SELECT SpecID, SpecName, SpecValue
            FROM dbo.ProductSpecs
            WHERE ProductName = ?
            ORDER BY SpecID
        """, (p.ProductName,))
        specs = [{"SpecID": r.SpecID, "SpecName": r.SpecName, "SpecValue": r.SpecValue}
                 for r in cur.fetchall()]

        # B2. 找不到就模糊 LIKE（使用標準化後的關鍵字，避免過長）
        if not specs:
            like_kw = _normalize_name(p.ProductName)[:30]  # 關鍵字太長會慢，切短
            cur.execute("""
                SELECT SpecID, SpecName, SpecValue
                FROM dbo.ProductSpecs
                WHERE ProductName LIKE ?
                ORDER BY SpecID
            """, (f"%{like_kw}%",))
            specs = [{"SpecID": r.SpecID, "SpecName": r.SpecName, "SpecValue": r.SpecValue}
                     for r in cur.fetchall()]

        # B3. 仍沒有 → 拆關鍵字 AND 一起匹配
        if not specs:
            tokens = [t for t in _normalize_name(p.ProductName).split(" ") if t][:6]
            if tokens:
                where = " AND ".join(["ProductName LIKE ?"] * len(tokens))
                params = [f"%{t}%" for t in tokens]
                sql = f"""
                    SELECT SpecID, SpecName, SpecValue
                    FROM dbo.ProductSpecs
                    WHERE {where}
                    ORDER BY SpecID
                """
                cur.execute(sql, params)
                specs = [{"SpecID": r.SpecID, "SpecName": r.SpecName, "SpecValue": r.SpecValue}
                         for r in cur.fetchall()]

        conn.close()

        # C. 組合回傳：商品主檔 + 規格（可能為空陣列）
        product["Specs"] = specs
        return jsonify(product)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
