from flask import Flask, jsonify
from ortools.sat.python import cp_model

app = Flask(__name__)

# 這是測試主廚有沒有醒來的網址
@app.route('/')
def home():
    return "✅ 機器人主廚已上線！OR-Tools 引擎準備就緒！"

# 這是未來 Google 試算表要把資料丟過來的地方
@app.route('/schedule', methods=['POST'])
def schedule():
    # 未來我們會把「三大輪值表」的複雜數學邏輯全部寫在這裡
    return jsonify({"status": "success", "message": "API 連線測試成功！等待排班資料中..."})

if __name__ == '__main__':
    # 讓程式在雲端環境正確運行
    app.run(host='0.0.0.0', port=10000)
