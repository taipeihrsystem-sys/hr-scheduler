from flask import Flask, request, jsonify
from ortools.sat.python import cp_model
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return "機器人主廚已上線！三大引擎 (全規則終極版) 準備就緒！"

@app.route('/schedule', methods=['POST'])
def schedule():
    try:
        data = request.get_json()
        lunch_staff = data.get('lunch_staff', [])
        ebook_staff = data.get('ebook_staff', [])
        clean_staff = data.get('clean_staff', [])
        month_days = data.get('month_days', 28)
        calendar_dates = data.get('calendar_dates', [])
        meeting_days = data.get('meeting_days', []) 
        holiday_shifts = data.get('holiday_shifts', {}) 
        last_month_counts = data.get('last_month_counts', {})
        clean_history = data.get('clean_history', {})
        
        model = cp_model.CpModel()
        
        # ==========================================
        # 🍱 引擎一：中午值班 (The Noon Engine)
        # ==========================================
        lunch_shifts = {}
        for d in range(1, month_days + 1):
            for staff in lunch_staff:
                lunch_shifts[(d, staff)] = model.NewBoolVar(f'lunch_d{d}_{staff}')
                
        for d in range(1, month_days + 1):
            day_str = str(d)
            if day_str in holiday_shifts:
                # 假日動態人數：過濾大安與留停後計算
                working_today = holiday_shifts[day_str]
                valid_working = [s for s in working_today if s in lunch_staff]
                work_count = len(valid_working)
                req = 3 if work_count >= 5 else (2 if work_count == 4 else (1 if work_count == 3 else 0))
                model.Add(sum(lunch_shifts[(d, staff)] for staff in lunch_staff) == req)
                for staff in lunch_staff:
                    if staff not in valid_working:
                        model.Add(lunch_shifts[(d, staff)] == 0)
            else:
                # 平日 1~25 日排 3 人，26 日後排 4 人
                date_str = calendar_dates[d-1] if (d-1) < len(calendar_dates) else ""
                day_val = 1
                if '/' in date_str:
                    try: day_val = int(date_str.split('/')[1])
                    except: pass
                req = 4 if day_val >= 26 else 3
                model.Add(sum(lunch_shifts[(d, staff)] for staff in lunch_staff) == req)
                
        # 群組防護網
        group_cashier = ["吳仕惇", "孫淑美", "曾速賢", "王思婷"] 
        group_specific = ["徐淑芳", "朱育萱", "曹芯穎"] 
        group_finance = ["陳可孋", "呂旭玲", "王聖鷹", "潘萍芬"] # 財務室
        
        for d in range(1, month_days + 1):
            present_c = [s for s in group_cashier if s in lunch_staff]
            if present_c: model.Add(sum(lunch_shifts[(d, s)] for s in present_c) <= 1)
            present_s = [s for s in group_specific if s in lunch_staff]
            if present_s: model.Add(sum(lunch_shifts[(d, s)] for s in present_s) <= 1)
            present_f = [s for s in group_finance if s in lunch_staff]
            if present_f: model.Add(sum(lunch_shifts[(d, s)] for s in present_f) <= 1)

        # 王不見王
        if "林淑芬" in lunch_staff and "張珮儀" in lunch_staff:
            for d in range(1, month_days + 1):
                model.Add(lunch_shifts[(d, "林淑芬")] + lunch_shifts[(d, "張珮儀")] <= 1)
                
        # 會議避開
        for d in meeting_days:
            for staff in group_specific + group_finance:
                if staff in lunch_staff:
                    model.Add(lunch_shifts[(d, staff)] == 0)
                    
        # 疲勞度管理 (間隔 3 天)
        for staff in lunch_staff:
            for d in range(1, month_days - 2):
                model.Add(sum(lunch_shifts[(d + i, staff)] for i in range(4)) <= 1)
                
        # 每月次數上限
        lunch_counts = {staff: sum(lunch_shifts[(d, staff)] for d in range(1, month_days + 1)) for staff in lunch_staff}
        for staff in lunch_staff:
            last_count = last_month_counts.get(staff, 0)
            max_shifts = 3 if last_count >= 4 else 4
            model.Add(lunch_counts[staff] <= max_shifts)

        # ==========================================
        # 📖 引擎二：電子書輪值 (The E-book Engine)
        # ==========================================
        ebook_shifts = {}
        for d in range(1, month_days + 1):
            for staff in ebook_staff:
                ebook_shifts[(d, staff)] = model.NewBoolVar(f'ebook_d{d}_{staff}')
                
        for d in range(1, month_days + 1):
            date_str = calendar_dates[d-1] if (d-1) < len(calendar_dates) else ""
            day_val = 1
            if '/' in date_str:
                try: day_val = int(date_str.split('/')[1])
                except: pass
            
            if day_val < 10 or str(d) in holiday_shifts:
                for staff in ebook_staff:
                    model.Add(ebook_shifts[(d, staff)] == 0)
            else:
                model.Add(sum(ebook_shifts[(d, staff)] for staff in ebook_staff) == 1)

        for staff in ebook_staff:
            for d in range(1, month_days - 4):
                model.Add(sum(ebook_shifts[(d + i, staff)] for i in range(6)) <= 1)
                
        ebook_counts = {staff: sum(ebook_shifts[(d, staff)] for d in range(1, month_days + 1)) for staff in ebook_staff}
        for staff in ebook_staff:
             model.Add(ebook_counts[staff] <= 2)

        # ==========================================
        # 🧹 引擎三：打掃輪值 (The Cleaning Engine)
        # ==========================================
        clean_shifts = {}
        clean_categories = ["辦公室掃地", "辦公室拖地", "會議室", "窗戶", "志工區", "公共櫃", "倒回收"]
        clean_reqs = {"辦公室掃地": 6, "辦公室拖地": 6, "會議室": 2, "窗戶": 1, "志工區": 3, "公共櫃": 2, "倒回收": 2}
        
        for staff in clean_staff:
            for cat in clean_categories:
                clean_shifts[(staff, cat)] = model.NewBoolVar(f'clean_{staff}_{cat}')
                
        # 加入淑如後，確保所有人公平分配任務
        max_tasks = 1 if len(clean_staff) >= sum(clean_reqs.values()) else 2
        for staff in clean_staff:
            model.Add(sum(clean_shifts[(staff, cat)] for cat in clean_categories) <= max_tasks)
            
        for cat in clean_categories:
            model.Add(sum(clean_shifts[(staff, cat)] for staff in clean_staff) == clean_reqs[cat])

        # ==========================================
        # 🌟 智慧優化與公平正義指標 (Penalties & Bonuses)
        # ==========================================
        penalty = 0
        overlap_bonus = 0
        
        # 打掃歷史迴避 (做過越多次越不會被抽中)
        for staff in clean_staff:
            history = clean_history.get(staff, {})
            for cat in clean_categories:
                done_times = int(history.get(cat, 0))
                penalty += clean_shifts[(staff, cat)] * (done_times * 100)
                    
        # 電子書優先挑選當天有值午班的人
        for d in range(1, month_days + 1):
            for staff in ebook_staff:
                if staff in lunch_staff:
                    overlap_var = model.NewBoolVar(f'overlap_d{d}_{staff}')
                    model.Add(overlap_var <= lunch_shifts[(d, staff)])
                    model.Add(overlap_var <= ebook_shifts[(d, staff)])
                    overlap_bonus += overlap_var * 5
                    
        for staff in ebook_staff:
            has_ebook = model.NewBoolVar(f'has_ebook_{staff}')
            model.Add(ebook_counts[staff] >= 1).OnlyEnforceIf(has_ebook)
            model.Add(ebook_counts[staff] == 0).OnlyEnforceIf(has_ebook.Not())
            overlap_bonus += has_ebook * 20 
            
        for staff in lunch_staff:
            has_lunch = model.NewBoolVar(f'has_lunch_{staff}')
            model.Add(lunch_counts[staff] >= 2).OnlyEnforceIf(has_lunch)
            model.Add(lunch_counts[staff] < 2).OnlyEnforceIf(has_lunch.Not())
            overlap_bonus += has_lunch * 15 

        model.Minimize(penalty - overlap_bonus)

        # ==========================================
        # 3. 呼叫求解器
        # ==========================================
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 20.0 
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule_result = {"lunch": {}, "ebook": {}, "clean": {}}
            for d in range(1, month_days + 1):
                schedule_result["lunch"][str(d)] = [staff for staff in lunch_staff if solver.Value(lunch_shifts[(d, staff)]) == 1]
                schedule_result["ebook"][str(d)] = [staff for staff in ebook_staff if solver.Value(ebook_shifts[(d, staff)]) == 1]
            for cat in clean_categories:
                schedule_result["clean"][cat] = [staff for staff in clean_staff if solver.Value(clean_shifts[(staff, cat)]) == 1]

            return jsonify({"status": "success", "message": "三大引擎排班成功！", "data": schedule_result}), 200
        else:
            return jsonify({"status": "error", "message": "條件過於嚴苛，AI 無法排班！"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
