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
        
        meeting_days = data.get('meeting_days', []) 
        holiday_days = data.get('holiday_days', []) 
        
        # 2. 啟動 OR-Tools 數學模型
        model = cp_model.CpModel()
        
        # ==========================================
        # 🍱 引擎一：中午值班
        # ==========================================
        lunch_shifts = {}
        for d in range(1, month_days + 1):
            for staff in lunch_staff:
                lunch_shifts[(d, staff)] = model.NewBoolVar(f'lunch_d{d}_{staff}')
                
        for d in range(1, month_days + 1):
            if d in holiday_days:
                model.Add(sum(lunch_shifts[(d, staff)] for staff in lunch_staff) >= 1)
            else:
                req = 3 if d <= 25 else 4
                model.Add(sum(lunch_shifts[(d, staff)] for staff in lunch_staff) == req)
                
        if "林淑芬" in lunch_staff and "張珮儀" in lunch_staff:
            for d in range(1, month_days + 1):
                model.Add(lunch_shifts[(d, "林淑芬")] + lunch_shifts[(d, "張珮儀")] <= 1)

        specific_groups = ["徐淑芳", "朱育萱", "曹芯穎"] 
        for d in meeting_days:
            for staff in specific_groups:
                if staff in lunch_staff:
                    model.Add(lunch_shifts[(d, staff)] == 0)

        # ==========================================
        # 📖 引擎二：電子書輪值
        # ==========================================
        ebook_shifts = {}
        for d in range(1, month_days + 1):
            for staff in ebook_staff:
                ebook_shifts[(d, staff)] = model.NewBoolVar(f'ebook_d{d}_{staff}')
                
        for d in range(1, month_days + 1):
            if d <= 10 or d in holiday_days:
                for staff in ebook_staff:
                    model.Add(ebook_shifts[(d, staff)] == 0)

        # ==========================================
        # 3. 呼叫求解器並打包結果
        # ==========================================
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15.0 
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule_result = {
                "lunch": {},
                "ebook": {}
            }
            
            for d in range(1, month_days + 1):
                daily_lunch = []
                for staff in lunch_staff:
                    if solver.Value(lunch_shifts[(d, staff)]) == 1:
                        daily_lunch.append(staff)
                schedule_result["lunch"][str(d)] = daily_lunch
                
            for d in range(1, month_days + 1):
                daily_ebook = []
                for staff in ebook_staff:
                    if solver.Value(ebook_shifts[(d, staff)]) == 1:
                        daily_ebook.append(staff)
                schedule_result["ebook"][str(d)] = daily_ebook

            result = {
                "status": "success",
                "message": "AI 排班成功！",
                "data": schedule_result
            }
            return jsonify(result), 200
        else:
            return jsonify({"status": "error", "message": "條件過於嚴苛，AI 無法找到符合所有規則的排班表！"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
