# cards.py
from flask import Blueprint, jsonify
import pyodbc

cards = Blueprint('cards', __name__)

# ✅ 資料庫連線字串（與 app.py 共用）
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888"
)

@cards.route('/cards', methods=['GET'])
def get_all_cards():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        query = """
        SELECT 
            id,
            [銀行名稱],
            [卡名],
            [來源頁面網址],
            [一般優惠],
            [一般優惠條件],
            [額外優惠],
            [額外優惠條件],
            [優惠方案1],
            [優惠方案1條件],
            [優惠方案2],
            [優惠方案2條件],
            [優惠方案3],
            [優惠方案3條件],
            [專屬優惠],
            [百大特店]
        FROM dbo.[信用卡資料]
        """

        result = cursor.execute(query).fetchall()
        columns = [column[0] for column in cursor.description]

        # ✅ 安全處理欄位轉換，防止 None 導致 jsonify 出錯
        cards = [
            {column: (str(value) if value is not None else '') for column, value in zip(columns, row)}
            for row in result
        ]

        return jsonify(cards)

    except Exception as e:
        print("❌ 錯誤：", e)
        return jsonify({'error': str(e)}), 500

