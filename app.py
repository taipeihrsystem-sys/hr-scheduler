from flask import Flask, request, jsonify
from ortools.sat.python import cp_model

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ 機器人主廚已上線！OR-Tools 引擎準備就緒！"

@app.route('/schedule', methods=['POST'])
def schedule():
    try:
        data = request.get_json()
        staff_list = data.get('staff_list', [])
        days_in_month = data.get('days_in_month', 28)
        
        model = cp_model.CpModel()
        
        noon_shifts = {}
        for d in range(1, days_in_month + 1):
            for s in staff_list:
                noon_shifts[(d, s)] = model.NewBoolVar(f'noon_d{d}_{s}')
                
        for d in range(1, days_in_month + 1):
            model.Add(sum(noon_shifts[(d, s)] for s in staff_list) == 3)
            
            group1 = [s for s in staff_list if s in ["徐淑芳", "朱育萱", "曹芯穎"]]
            if len(group1) > 0:
                model.Add(sum(noon_shifts[(d, s)] for s in group1) <= 1)
                
            if "林淑芬" in staff_list and "張珮儀" in staff_list:
                model.Add(noon_shifts[(d, "林淑芬")] + noon_shifts[(d, "張珮儀")] <= 1)
        
        # [規則 D] 公平原則：計算每人最多只能排幾次
        max_shifts = (days_in_month * 3) // len(staff_list) + 1
        for s in staff_list:
            model.Add(sum(noon_shifts[(d, s)] for d in range(1, days_in_month + 1)) <= max_shifts)
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0 
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            result_schedule = {}
            for d in range(1, days_in_month + 1):
                daily_staff = []
                for s in staff_list:
                    if solver.Value(noon_shifts[(d, s)]) == 1:
                        daily_staff.append(s)
                result_schedule[f"Day_{d}"] = daily_staff
                
            return jsonify({
                "status": "success",
                "message": "🎉 AI 運算成功！已完美避開所有防呆限制，並確保排班公平！",
                "schedule": result_schedule
            })
        else:
            return jsonify({"status": "error", "message": "找不到符合所有規則的排班方式，請放寬條件！"})

    except Exception as e:
        return jsonify({"status": "error", "message": f"系統發生錯誤：{str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
