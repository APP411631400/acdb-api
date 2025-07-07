# specs.py
from flask import Blueprint, request, jsonify
import pyodbc

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

# ✅ 取得產品主資料（只讀 Products 表）
@specs_bp.route("/product/info", methods=["GET"])
def get_product_info():
    product_name = request.args.get("name", "")
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



# ✅ 根據 ProductID 取得所有規格（查 ProductSpecs）
@specs_bp.route("/product/specs/id", methods=["GET"])
def get_specs_by_id():
    product_id = request.args.get("id", "")
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SpecName, SpecValue, ProductName
            FROM dbo.ProductSpecs
            WHERE ProductID = ?
        """, (product_id,))
        rows = cursor.fetchall()
        conn.close()

        result = [
            {
                "SpecName": row.SpecName,
                "SpecValue": row.SpecValue,
                "ProductName": row.ProductName
            }
            for row in rows
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

