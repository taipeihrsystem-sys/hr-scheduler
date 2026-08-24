from flask import Flask, request, jsonify
from ortools.sat.python import cp_model
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # 允許 Google Apps Script 跨網域呼叫

@app.route('/', methods=['GET'])
def home():
    return "機器人主廚已上線！OR-Tools 引擎準備就緒！"

@app.route('/schedule', methods=['POST'])
def schedule():
    try:
        # 1. 接收來自 Google 試算表的資料包裹
        data = request.get_json()
        
        lunch_staff = data.get('lunch_staff', [])
        ebook_staff = data.get('ebook_staff', [])
        month_days = data.get('month_days', 28)
        
        # 特殊日與請假資料 (預計從前端傳來)
        meeting_days = data.get('meeting_days', []) # 例如: [3, 10] 代表第3天和第10天有會議
        holiday_days = data.get('holiday_days', []) # 假日的日期清單
        
        # 2. 啟動 OR-Tools 數學模型
        model = cp_model.CpModel()
        
        # ==========================================
        # 🍱 引擎一：中午值班 (The Noon Engine)
        # ==========================================
        lunch_shifts = {}
        for d in range(1, month_days + 1):
            for staff in lunch_staff:
                lunch_shifts[(d, staff)] = model.NewBoolVar(f'lunch_d{d}_{staff}')
                
        # [規則] 每日需求人數
        for d in range(1, month_days + 1):
            if d in holiday_days:
                # 假日邏輯：需根據實際上班人數動態決定 (暫設至少1人，後續依傳入參數精準計算)
                model.Add(sum(lunch_shifts[(d, staff)] for staff in lunch_staff) >= 1)
            else:
                # 平日 1-25 日排 3 人，26 日後排 4 人
                req = 3 if d <= 25 else 4
                model.Add(sum(lunch_shifts[(d, staff)] for staff in lunch_staff) == req)
                
        # [規則] 王不見王：林淑芬與張珮儀絕對不同天
        if "林淑芬" in lunch_staff and "張珮儀" in lunch_staff:
            for d in range(1, month_days + 1):
                model.Add(lunch_shifts[(d, "林淑芬")] + lunch_shifts[(d, "張珮儀")] <= 1)

        # [規則] 會議防護網 (組會/幹部會)
        specific_groups = ["徐淑芳", "朱育萱", "曹芯穎"] # 加上出納與財務室名單...
        for d in meeting_days:
            for staff in specific_groups:
                if staff in lunch_staff:
                    model.Add(lunch_shifts[(d, staff)] == 0) # 強制不排班

        # ==========================================
        # 📖 引擎二：電子書輪值 (The E-book Engine)
        # ==========================================
        ebook_shifts = {}
        for d in range(1, month_days + 1):
            for staff in ebook_staff:
                ebook_shifts[(d, staff)] = model.NewBoolVar(f'ebook_d{d}_{staff}')
                
        # [規則] 10號以後才開始排班，且排除假日
        for d in range(1, month_days + 1):
            if d <= 10 or d in holiday_days:
                for staff in ebook_staff:
                    model.Add(ebook_shifts[(d, staff)] == 0)

        # ==========================================
        # 3. 呼叫求解器 (Solver)
        # ==========================================
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15.0 # 設定運算時間上限 15 秒
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # 成功解出最佳排班表，將結果打包回傳
            result = {
                "status": "success",
                "message": "AI 排班成功！",
                # 這裡會放入解析後的班表資料，回傳給 Google 表單
            }
            return jsonify(result), 200
        else:
            return jsonify({"status": "error", "message": "條件過於嚴苛，AI 無法找到符合所有規則的排班表！"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
