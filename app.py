from flask import Flask, request, jsonify
from ortools.sat.python import cp_model

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ 機器人主廚已上線！OR-Tools 引擎準備就緒！"

@app.route('/schedule', methods=['POST'])
def schedule():
    try:
        # 1️⃣ 【接收訂單資料】
        data = request.get_json()
        staff_list = data.get('staff_list', [])
        days_in_month = data.get('days_in_month', 28)
        
        # 建立 OR-Tools 數學模型與求解器
        model = cp_model.CpModel()
        
        # 2️⃣ 【建立變數 (格子)】
        # 想像我們在電腦記憶體裡畫了一張很大的空白班表
        # noon_shifts[(d, s)] 代表：第 d 天，員工 s 是否要值中午班 (1=是, 0=否)
        noon_shifts = {}
        for d in range(1, days_in_month + 1):
            for s in staff_list:
                noon_shifts[(d, s)] = model.NewBoolVar(f'noon_d{d}_{s}')
                
        # 3️⃣ 【寫入防呆規則 (Constraints)】
        
        for d in range(1, days_in_month + 1):
            # [規則 A] 需求人數：假設平日需要 3 人
            model.Add(sum(noon_shifts[(d, s)] for s in staff_list) == 3)
            
            # [規則 B] 群組 1 防護網：徐淑芳、朱育萱、曹芯穎，每天最多 1 人
            group1 = [s for s in staff_list if s in ["徐淑芳", "朱育萱", "曹芯穎"]]
            if len(group1) > 0:
                model.Add(sum(noon_shifts[(d, s)] for s in group1) <= 1)
                
            # [規則 C] 王不見王：林淑芬與張珮儀絕對不排在同一天
            if "林淑芬" in staff_list and "張珮儀" in staff_list:
                model.Add(noon_shifts[(d, "林淑芬")] + noon_shifts[(d, "張珮儀")] <= 1)
        
        # 4️⃣ 【啟動 AI 求解】
        solver = cp_model.CpSolver()
        # 設定思考時間上限 (例如 10 秒)
        solver.parameters.max_time_in_seconds = 10.0 
        status = solver.Solve(model)
        
        # 5️⃣ 【解讀結果並回傳】
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # 如果成功找到答案，就把名單整理出來
            result_schedule = {}
            for d in range(1, days_in_month + 1):
                daily_staff = []
                for s in staff_list:
                    if solver.Value(noon_shifts[(d, s)]) == 1:
                        daily_staff.append(s)
                result_schedule[f"Day_{d}"] = daily_staff
                
            return jsonify({
                "status": "success",
                "message": "🎉 AI 運算成功！已完美避開所有防呆限制！",
                "schedule": result_schedule
            })
        else:
            return jsonify({"status": "error", "message": "找不到符合所有規則的排班方式，請放寬條件！"})

    except Exception as e:
        return jsonify({"status": "error", "message": f"系統發生錯誤：{str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
