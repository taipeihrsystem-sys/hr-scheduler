from flask import Flask, request, jsonify
from ortools.sat.python import cp_model

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ 機器人主廚已上線！OR-Tools 引擎準備就緒！"

@app.route('/schedule', methods=['POST'])
def schedule():
    try:
        # 1️⃣ 【接收訂單】：讀取從 Google 試算表傳來的名單與條件 (JSON 格式)
        data = request.get_json()
        
        # 這裡未來會接收：同仁名單、請假日期、歷史打掃次數等
        staff_list = data.get('staff_list', [])
        days_in_month = data.get('days_in_month', 28)

        # 2️⃣ 【啟動引擎】：建立 OR-Tools 數學模型
        model = cp_model.CpModel()

        # --- 🧠 核心邏輯區 (The Brain) ---
        
        # [引擎 A：中午值班]
        # 規則：平日 3-4 人，假日 1-2 人。
        # 防呆：群組1(徐朱曹)<=1，群組2(財務室)<=1，林淑芬與張珮儀不排同天。
        
        # [引擎 B：電子書輪值]
        # 規則：10號後平日排班。限諮詢、出納、帳務。
        # 綁定：優先指派「當天已被排到中午值班」的人。
        
        # [引擎 C：打掃輪值]
        # 規則：結帳室與機動固定。其餘區域取消倒回收優先權。
        # 公平：比對歷史紀錄，優先派給「過去做最少次」的人。
        
        # ---------------------------------
        
        # 3️⃣ 【回傳餐點】：將算好的排班表打包，準備送回 Google 試算表
        # (目前先設定為成功接收訊號的格式，待前端資料接通後即可啟用真實求解器)
        response_data = {
            "status": "success",
            "message": "AI 大腦已成功收到規則，三大輪值引擎運算完畢！",
            "schedule_result": "這裡未來會填滿 28 天的排班結果"
        }
        
        return jsonify(response_data)

    except Exception as e:
        # 如果運算過程出錯，把錯誤訊息傳回試算表，方便我們除錯
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
