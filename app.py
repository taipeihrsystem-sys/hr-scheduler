from flask import Flask, request, jsonify
from ortools.sat.python import cp_model
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return "機器人主廚已上線！OR-Tools 引擎準備就緒！"

@app.route('/schedule', methods=['POST'])
def schedule():
    try:
        data = request.get_json()
        
        lunch_staff = data.get('lunch_staff', [])
        ebook_staff = data.get('ebook_staff', [])
        month_days = data.get('month_days', 28)
        
        # 接收前端的 1~28 天特殊設定
        meeting_days = data.get('meeting_days', []) 
        holiday_shifts = data.get('holiday_shifts', {}) 
        last_month_counts = data.get('last_month_counts', {})
        
        model = cp_model.CpModel()
        
        # ==========================================
        # 🍱 引擎一：中午值班 (The Noon Engine)
        # ==========================================
        lunch_shifts = {}
        for d in range(1, month_days + 1):
            for staff in lunch_staff:
                lunch_shifts[(d, staff)] = model.NewBoolVar(f'lunch_d{d}_{staff}')
                
        # [核心規則 1] 每日人數與假日強制排班
        for d in range(1, month_days + 1):
            day_str = str(d)
            if day_str in holiday_shifts:
                # 假日有上班的人
                working_today = holiday_shifts[day_str]
                work_count = len(working_today)
                
                # 依上班人數決定排班人數 (5人以上排3人, 4人排2人, 3人排1人, 否則不排)
                req = 3 if work_count >= 5 else (2 if work_count == 4 else (1 if work_count == 3 else 0))
                model.Add(sum(lunch_shifts[(d, staff)] for staff in lunch_staff) == req)
                
                # 強制只能從「當天有上班的人」裡面挑選
                for staff in lunch_staff:
                    if staff not in working_today:
                        model.Add(lunch_shifts[(d, staff)] == 0)
            else:
                # 平日預設排 3 人 (暫定全部3人，若需精確判斷26日後排4人，可透過日期推算)
                model.Add(sum(lunch_shifts[(d, staff)] for staff in lunch_staff) == 3)
                
        # [核心規則 2] 群組防護網 (每天最多 1 人)
        group_cashier = ["吳仕惇", "孫淑美", "曾速賢", "王思婷"] # 出納股
        group_specific = ["徐淑芳", "朱育萱", "曹芯穎"] # 特定群組1
        
        for d in range(1, month_days + 1):
            # 確保出納股每天最多 1 人
            present_c = [s for s in group_cashier if s in lunch_staff]
            if present_c:
                model.Add(sum(lunch_shifts[(d, s)] for s in present_c) <= 1)
                
            # 確保特定群組每天最多 1 人
            present_s = [s for s in group_specific if s in lunch_staff]
            if present_s:
                model.Add(sum(lunch_shifts[(d, s)] for s in present_s) <= 1)

        # [核心規則 3] 王不見王
        if "林淑芬" in lunch_staff and "張珮儀" in lunch_staff:
            for d in range(1, month_days + 1):
                model.Add(lunch_shifts[(d, "林淑芬")] + lunch_shifts[(d, "張珮儀")] <= 1)

        # [核心規則 4] 會議避開特定群組
        for d in meeting_days:
            for staff in group_specific:
                if staff in lunch_staff:
                    model.Add(lunch_shifts[(d, staff)] == 0)

        # [高級規則 5] 疲勞度管理 (強制間隔至少 3 天)
        # 代表連續 4 天內 (d, d+1, d+2, d+3)，同一個人最多只能上 1 次
        for staff in lunch_staff:
            for d in range(1, month_days - 2):
                model.Add(sum(lunch_shifts[(d + i, staff)] for i in range(4)) <= 1)

        # [高級規則 6] 本月上限 (上個月排 4 次以上，本月限 3 次；否則限 4 次)
        for staff in lunch_staff:
            last_count = last_month_counts.get(staff, 0)
            max_shifts = 3 if last_count >= 4 else 4
            model.Add(sum(lunch_shifts[(d, staff)] for d in range(1, month_days + 1)) <= max_shifts)


        # ==========================================
        # 📖 引擎二：電子書輪值 (The E-book Engine)
        # ==========================================
        ebook_shifts = {}
        for d in range(1, month_days + 1):
            for staff in ebook_staff:
                ebook_shifts[(d, staff)] = model.NewBoolVar(f'ebook_d{d}_{staff}')
                
        # [電子書規則 1] 10號以後才開始，且遇到假日不排 (若當天 holiday_shifts 有紀錄代表是假日)
        for d in range(1, month_days + 1):
            if d <= 10 or str(d) in holiday_shifts:
                for staff in ebook_staff:
                    model.Add(ebook_shifts[(d, staff)] == 0)
            else:
                # 平日電子書需 1 人
                model.Add(sum(ebook_shifts[(d, staff)] for staff in ebook_staff) == 1)

        # [電子書規則 2] 疲勞度管理 (間隔至少 5 天) -> 連續 6 天內只能上 1 次
        for staff in ebook_staff:
            for d in range(1, month_days - 4):
                model.Add(sum(ebook_shifts[(d + i, staff)] for i in range(6)) <= 1)

        # [電子書規則 3] 本月上限最多 2 次
        for staff in ebook_staff:
             model.Add(sum(ebook_shifts[(d, staff)] for d in range(1, month_days + 1)) <= 2)


        # ==========================================
        # 3. 呼叫求解器並打包結果
        # ==========================================
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 20.0 
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule_result = {"lunch": {}, "ebook": {}}
            
            for d in range(1, month_days + 1):
                daily_lunch = [staff for staff in lunch_staff if solver.Value(lunch_shifts[(d, staff)]) == 1]
                schedule_result["lunch"][str(d)] = daily_lunch
                
                daily_ebook = [staff for staff in ebook_staff if solver.Value(ebook_shifts[(d, staff)]) == 1]
                schedule_result["ebook"][str(d)] = daily_ebook

            return jsonify({"status": "success", "message": "AI 排班成功！", "data": schedule_result}), 200
        else:
            return jsonify({"status": "error", "message": "條件過於嚴苛，AI 無法找到符合所有規則的排班表！"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
