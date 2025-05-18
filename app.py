from flask import Flask, request, jsonify
import base64
import pyodbc
from datetime import datetime

app = Flask(__name__)

# ✅ 資料庫連線字串（記得保密）
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888;"
)

# ✅ 上傳價格回報紀錄（含圖片、GPS、條碼等）
@app.route("/upload", methods=["POST"])
def upload():
    try:
        data = request.json

        # 🔽 取得前端傳來的欄位
        name = data.get("name", "")
        price = float(data.get("price", 0))
        lat = data.get("latitude", 0)
        lng = data.get("longitude", 0)
        store = data.get("store", "APP回報")
        barcode = data.get("barcode", "")
        user_id = data.get("userId", "guest")
        image_base64 = data.get("imageBase64")

        # ✅ 使用前端傳來的拍照時間作為儲存時間（解決 Render 時區誤差問題）
        capture_time_str = data.get("captureTime")
        timestamp = datetime.fromisoformat(capture_time_str) if capture_time_str else datetime.now()

        # ✅ 將圖片 base64 解碼為二進位格式（若有）
        image_data = base64.b64decode(image_base64) if image_base64 else None

        # ✅ 寫入資料庫
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO dbo.門市商品 (
                商品名稱, 價格, 位置描述, 座標, 圖片, 時間, 條碼, 來源, 使用者ID
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            price,
            store,
            f"{lat},{lng}",  # 將緯度經度合併為一欄
            image_data,
            timestamp,
            barcode,
            "拍照",  # 固定來源為拍照回報
            user_id
        ))

        # ✅ 回傳主鍵 id（方便之後精準刪除）
        cursor.execute("SELECT SCOPE_IDENTITY()")
        new_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "timestamp": timestamp.isoformat(),
            "id": new_id  # 回傳給前端儲存
        })

    except Exception as e:
        print(f"❌ 上傳錯誤：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500


# ✅ 刪除指定紀錄（只依據唯一 id，避免時間誤差與名稱重複）
@app.route("/delete", methods=["POST"])
def delete():
    try:
        data = request.json
        record_id = data.get("id")  # 前端要傳來儲存過的 id

        if not record_id:
            return jsonify({"status": "fail", "error": "缺少 id"}), 400

        # ✅ 執行刪除語句
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM dbo.門市商品
            WHERE id = ?
        """, (record_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"❌ 刪除錯誤：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500


# ✅ 查詢所有回報資料（不含圖片，供前端顯示用）
@app.route("/records", methods=["GET"])
def get_all_records():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # ✅ 查詢欄位包含主鍵 id（方便前端操作）
        cursor.execute("""
            SELECT id, 商品名稱, 價格, 座標, 時間, 條碼, 來源
            FROM dbo.門市商品
            ORDER BY 時間 DESC
        """)

        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()
        return jsonify(result)

    except Exception as e:
        print(f"❌ 查詢失敗：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500


# ✅ 首頁提示 API 狀態
@app.route("/")
def home():
    return "✅ ACDB API is running! You can POST to /upload, /delete or GET /records"


# ✅ 啟動 Flask（允許外部裝置連線）
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
