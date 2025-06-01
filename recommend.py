from flask import Blueprint, request, jsonify
import requests
import pyodbc

recommend = Blueprint("recommend", __name__)

# ✅ Azure OpenAI 設定（請改成你自己的）
AZURE_OPENAI_API_KEY = "AflfAee4CjmRImjTYvN5NjNt1uKCy5uI6GOyDxPKS0fAWyyZ8GTqJQQJ99BEACYeBjFXJ3w3AAABACOGnjCD"
AZURE_OPENAI_ENDPOINT = "https://gptservice01.openai.azure.com/"
AZURE_DEPLOYMENT_NAME = "gpt-35-turbo"
AZURE_API_VERSION = "2023-07-01-preview"

# ✅ 資料庫連線字串（與 cards.py 同一份）
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=shoppingsystem.database.windows.net;"
    "DATABASE=ShoppingSystem;"
    "UID=systemgod666;"
    "PWD=Crazydog888"
)

# ✅ 卡片資料精簡格式（為降低 token 數量而設計）
def format_card(card):
    return f"""
卡名：{card['卡名']}，銀行：{card['銀行名稱']}，回饋：
- 一般：{card['一般優惠']}（條件：{card['一般優惠條件'] or '無'}）
- 額外：{card['額外優惠']}（條件：{card['額外優惠條件'] or '無'}）
- 其他：{card['優惠方案1']}、{card['優惠方案2']}、{card['優惠方案3']}
上限條件：{card['專屬優惠'] or '無'}，百大特店：{card['百大特店'] or '無'}
"""

# ✅ Prompt 模板（清楚指定 GPT 邏輯運算與格式）
def build_prompt(store, amount, cards_summary):
    return f"""
你是一位信用卡回饋推薦顧問，請幫我選出最適合的信用卡來進行此次消費：

🛒 消費地點：「{store}」  
💰 消費金額：{amount} 元  

請從以下卡片中選擇最划算的一張卡，邏輯需符合：
1. 回饋金額 = 消費金額 × 回饋比例（但不得超過回饋上限）
2. 若回饋已達上限，請推薦一張備援卡（較少限制且仍有回饋）
3. 選擇限制條件較少者，如不需綁定、不需登錄、不限日期
4. 估算回饋金額可大約，不需精確（但合理）

請回覆以下格式：
---
推薦卡片：  
預估回饋金額：  
推薦原因：  
注意事項（限制）：  
若已達上限建議使用：  

以下是卡片資料：
{cards_summary}
"""

# ✅ GPT Chat Completion API 呼叫（Azure OpenAI）
def ask_gpt(prompt):
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY
    }
    body = {
        "messages": [
            {"role": "system", "content": "你是一位信用卡回饋推薦 AI 顧問"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# ✅ 主路由 /recommend_card
@recommend.route("/recommend_card", methods=["POST"])
def recommend_card():
    try:
        data = request.get_json()
        store = data.get("store", "未知通路")
        amount = data.get("amount", 1000)

        # 讀取資料庫卡片資料
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        query = "SELECT * FROM dbo.[信用卡資料]"
        rows = cursor.execute(query).fetchall()
        columns = [col[0] for col in cursor.description]

        # 結構化卡片資料
        cards = [
            {col: str(val) if val is not None else '' for col, val in zip(columns, row)}
            for row in rows
        ]

        # 格式化為 GPT 可讀文字格式
        formatted_cards = [format_card(card) for card in cards]
        prompt = build_prompt(store, amount, "\n".join(formatted_cards))

        # 呼叫 GPT 回傳結果
        result = ask_gpt(prompt)
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
