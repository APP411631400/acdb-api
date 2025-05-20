# cards.py
from flask import Blueprint, jsonify
import pyodbc

cards = Blueprint('cards', __name__)

# ✅ 資料庫連線字串（可與 app.py 共用）
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
            [優惠方案1],
            [優惠方案條件1],
            [優惠方案2],
            [優惠方案條件2],
            [優惠方案3],
            [優惠方案條件3],
            [專屬優惠],
            [巨大特招]
        FROM dbo.[信用卡資料]
        """
        result = cursor.execute(query).fetchall()
        columns = [column[0] for column in cursor.description]

        cards = [dict(zip(columns, row)) for row in result]

        return jsonify(cards)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

