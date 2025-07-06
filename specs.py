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

# ✅ 查詢某商品的所有規格（條件模糊查詢名稱）
@specs_bp.route("/product/specs", methods=["GET"])
def get_product_specs():
    product_name = request.args.get("name", "")
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ProductID, SpecName, SpecValue, ProductName
            FROM dbo.ProductSpecs
            WHERE ProductName LIKE ?
        """, (f"%{product_name}%",))
        rows = cursor.fetchall()
        conn.close()

        result = [
            {
                "ProductID": row.ProductID,
                "SpecName": row.SpecName,
                "SpecValue": row.SpecValue,
                "ProductName": row.ProductName
            }
            for row in rows
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ 比較某個規格名稱（SpecName）下不同商品的規格值
@specs_bp.route("/compare/spec", methods=["GET"])
def compare_spec_value():
    spec_name = request.args.get("spec", "")
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ProductName, SpecValue
            FROM dbo.ProductSpecs
            WHERE SpecName = ?
        """, (spec_name,))
        rows = cursor.fetchall()
        conn.close()

        result = [
            {
                "ProductName": row.ProductName,
                "SpecValue": row.SpecValue
            }
            for row in rows
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
