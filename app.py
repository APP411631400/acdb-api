from flask import Flask, request, jsonify
from auth import auth
import base64
import pyodbc
from datetime import datetime

app = Flask(__name__)
app.register_blueprint(auth)  # ✅ 註冊登入路由

# ✅ 資料庫連線字串（請勿公開）
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888;"
)

# ✅ 上傳價格回報紀錄（使用前端時間、接收圖片、座標等）
@app.route("/upload", methods=["POST"])
def upload():
    try:
        data = request.json

        # 🔽 取得欄位資料
        name = data.get("name", "")
        price = float(data.get("price", 0))
        lat = data.get("latitude", 0)
        lng = data.get("longitude", 0)
        store = data.get("store", "APP回報")
        barcode = data.get("barcode", "")
        user_id = data.get("userId", "guest")
        image_base64 = data.get("imageBase64")

        # ✅ 時間（前端傳入 captureTime）
        capture_time_str = data.get("captureTime")
        if not capture_time_str:
            return jsonify({"status": "fail", "error": "缺少 captureTime"}), 400

        try:
            timestamp = datetime.fromisoformat(capture_time_str)
        except Exception:
            return jsonify({"status": "fail", "error": "captureTime 格式錯誤"}), 400

        # ✅ 圖片轉為 BLOB
        image_data = base64.b64decode(image_base64) if image_base64 else None

        # ✅ 連接資料庫並執行 insert + 取得主鍵 ID
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO dbo.門市商品 (
                商品名稱, 價格, 位置描述, 座標, 圖片, 時間, 條碼, 來源, 使用者ID
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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

        new_id_row = cursor.fetchone()
        new_id = new_id_row[0] if new_id_row else None
        print(f"✅ 寫入成功，主鍵 ID：{new_id}")

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "timestamp": timestamp.isoformat(),
            "id": new_id
        })

    except Exception as e:
        print(f"❌ 上傳錯誤：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500

# ✅ 刪除指定紀錄（依據唯一主鍵 ID，安全不重複）
@app.route("/delete", methods=["POST"])
def delete():
    try:
        data = request.json
        print("🧪 收到刪除請求：", data)

        # ✅ 強制轉為 int（避免 JSON 傳字串型別）
        try:
            record_id = int(data.get("id"))
        except:
            return jsonify({"status": "fail", "error": "id 不是有效數字"}), 400

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM dbo.門市商品
            WHERE id = ?
        """, (record_id,))

        # ✅ 若找不到該筆資料則回傳錯誤
        if cursor.rowcount == 0:
            return jsonify({"status": "fail", "error": f"查無 id {record_id}"}), 404

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"❌ 刪除錯誤：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500

# ✅ 查詢所有回報資料（不含圖片）
@app.route("/records", methods=["GET"])
def get_all_records():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, 商品名稱, 價格, 座標, 時間, 條碼, 來源
            FROM dbo.門市商品
            ORDER BY 時間 DESC
        """)

        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]

        result = []
        for row in rows:
            record = dict(zip(columns, row))
            # ✅ 明確轉換「時間」欄位為 ISO 格式字串（給前端用）
            if isinstance(record["時間"], datetime):
                record["時間"] = record["時間"].isoformat()
            result.append(record)

        cursor.close()
        conn.close()
        return jsonify(result)

    except Exception as e:
        print(f"❌ 查詢失敗：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500

# ✅ 根據 id 傳出圖片（base64 格式）
@app.route("/image/<int:record_id>", methods=["GET"])
def get_image_by_id(record_id):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 圖片 FROM dbo.門市商品 WHERE id = ?
        """, (record_id,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if row and row[0]:
            image_blob = row[0]
            image_base64 = base64.b64encode(image_blob).decode("utf-8")
            return jsonify({
                "status": "success",
                "imageBase64": image_base64
            })
        else:
            return jsonify({
                "status": "fail",
                "error": "查無圖片或圖片為空"
            }), 404

    except Exception as e:
        print(f"❌ 圖片查詢錯誤：{e}")
        return jsonify({"status": "fail", "error": str(e)}), 500

# ✅ API 狀態首頁
@app.route("/")
def home():
    return "✅ ACDB API is running! You can POST to /upload, /delete or GET /records"

# ✅ 啟動伺服器（允許外部連線）
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
