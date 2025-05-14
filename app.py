from flask import Flask, request, jsonify
import base64
import pyodbc
from datetime import datetime

app = Flask(__name__)

# ✅ 資料庫連線字串（請勿外洩）
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888;"
)

# ✅ 上傳價格回報紀錄（含圖片、座標等）
@app.route("/upload", methods=["POST"])
def upload():
    try:
        data = request.json

        # 🔽 取得所有欄位資料
        name = data.get("name", "")
        price = float(data.get("price", 0))
        lat = data.get("latitude", 0)
        lng = data.get("longitude", 0)
        store = data.get("store", "APP回報")
        barcode = data.get("barcode", "")
        user_id = data.get("userId", "guest")
        image_base64 = data.get("imageBase64")

        # ✅ 寫入資料的 timestamp（由後端生成）
        timestamp = datetime.now()

        # ✅ 圖片 base64 轉二進位（若有）
        image_data = base64.b64decode(image_base64) if image_base64 else None

        # ✅ 建立連線並寫入資料
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
            f"{lat},{lng}",
            image_data,
            timestamp,
            barcode,
            "拍照",
            user_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        # ✅ 回傳成功與該筆 timestamp（給前端儲存）
        return jsonify({
            "status": "success",
            "timestamp": timestamp.isoformat()
        })

    except Exception as e:
        print(f"❌ 上傳錯誤：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500

# ✅ 刪除指定紀錄（名稱 + 秒級時間格式）
@app.route("/delete", methods=["POST"])
def delete():
    try:
        data = request.json
        name = data.get("name")
        timestamp_str = data.get("timestamp")

        if not name or not timestamp_str:
            return jsonify({"status": "fail", "error": "缺少 name 或 timestamp"}), 400

        # ✅ 將 ISO 時間轉換為 datetime，並轉為秒級字串格式
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")  # ➜ 只保留到秒（避免毫秒誤判）
        except Exception:
            return jsonify({"status": "fail", "error": "時間格式錯誤"}), 400

        # ✅ 執行 SQL 刪除語句（注意使用 CONVERT 秒級比對）
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM dbo.門市商品
            WHERE 商品名稱 = ? AND CONVERT(varchar, 時間, 120) = ?
        """, (name, formatted_time))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"❌ 刪除錯誤：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500

# ✅ 查詢所有回報資料（不包含圖片）
@app.route("/records", methods=["GET"])
def get_all_records():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 商品名稱, 價格, 座標, 時間, 條碼, 來源
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

# ✅ 啟動 Flask 伺服器（允許外部裝置存取）
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
