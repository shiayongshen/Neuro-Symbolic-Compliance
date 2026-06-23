"""
Optimize single case tool
輸入 case_xxx，自動找到對應的 JSON 文件並執行 optimize 求解
"""
import json
import z3
import sys
from pathlib import Path

# 添加當前目錄到 Python 路徑，以便導入 json2z3
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from json2z3 import declare_vars, build_expr


def find_case_files(case_id):
    """
    根據 case_id 尋找對應的 constraint_spec.json, facts.json, varspecs.json
    
    Args:
        case_id: 如 'case_0' 或 '0'
    
    Returns:
        (constraint_spec_path, facts_path, varspecs_path) 或 (None, None, None)
    """
    # 標準化 case_id
    if not case_id.startswith('case_'):
        case_id = f'case_{case_id}'
    
    # 搜尋路徑（使用絕對路徑）
    script_dir = Path(__file__).parent.parent  # 項目根目錄
    search_dirs = [
        script_dir / 'outputs',
        Path('../outputs'),
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        constraint_spec_path = search_dir / f'{case_id}.constraint_spec.json'
        facts_path = search_dir / f'{case_id}.facts.json'
        varspecs_path = search_dir / f'{case_id}.varspecs.json'
        
        # 如果三個文件都存在，返回
        if constraint_spec_path.exists() and facts_path.exists() and varspecs_path.exists():
            return constraint_spec_path, facts_path, varspecs_path
    
    return None, None, None


def load_case_data(case_id):
    """
    載入 case 的所有數據
    
    Args:
        case_id: 如 'case_0' 或 '0'
    
    Returns:
        (constraint_spec, facts, varspecs) 或 (None, None, None)
    """
    constraint_spec_path, facts_path, varspecs_path = find_case_files(case_id)
    
    if constraint_spec_path is None:
        print(f"❌ 找不到 {case_id} 的相關 JSON 文件")
        return None, None, None
    
    try:
        with open(constraint_spec_path) as f:
            constraint_spec = json.load(f)
        with open(facts_path) as f:
            facts = json.load(f)
        with open(varspecs_path) as f:
            varspecs = json.load(f)
        
        print(f"✅ 成功載入 {case_id}")
        print(f"   Constraint spec: {constraint_spec_path}")
        print(f"   Facts: {facts_path}")
        print(f"   Varspecs: {varspecs_path}")
        
        return constraint_spec, facts, varspecs
    except Exception as e:
        print(f"❌ 載入 {case_id} 失敗: {e}")
        return None, None, None


def solve_case(constraint_spec, facts, varspecs):
    """
    使用 Z3 Optimize 求解最小合規解
    - constraint_spec: list of constraints (hard if weight > 0, soft if weight == 0)
    - facts: dict of initial facts (added as soft constraints)
    - varspecs: list of variable specifications
    
    返回: (initial_facts, suggested_model) 或 (None, None) 如果無解
    """
    try:
        # 聲明變量
        z3_vars = declare_vars(varspecs)
        
        # 創建 Optimize solver
        opt = z3.Optimize()
        
        # 添加 hard constraints (weight > 0)
        for c in constraint_spec:
            if c.get('weight', 0) > 0:
                expr = build_expr(c['expr'], z3_vars)
                tag = c.get('id', f"constraint_{constraint_spec.index(c)}")
                opt.assert_and_track(expr, tag)
        
        # 添加 soft constraints (weight == 0)
        for c in constraint_spec:
            if c.get('weight', 0) == 0:
                expr = build_expr(c['expr'], z3_vars)
                # Keep all soft constraints in the same objective to avoid
                # lexicographic ordering across per-constraint ids.
                opt.add_soft(expr, weight=1)
        
        # 添加 facts as soft constraints
        for k, v in facts.items():
            fact_expr = build_expr(["EQ", ["VAR", k], v], z3_vars)
            # Facts participate in the same aggregate soft objective.
            opt.add_soft(fact_expr, weight=1)
        
        # 求解
        result = opt.check()
        if result == z3.sat:
            model = opt.model()
            
            # 提取建議值
            suggested = {}
            for var_name in z3_vars:
                try:
                    sugg = model[z3_vars[var_name]]
                    if sugg is not None:
                        if sugg.sort() == z3.BoolSort():
                            suggested[var_name] = z3.is_true(sugg)
                        elif sugg.sort() == z3.IntSort():
                            suggested[var_name] = sugg.as_long()
                        elif sugg.sort() == z3.RealSort():
                            suggested[var_name] = float(sugg.numerator_as_long()) / float(sugg.denominator_as_long())
                        else:
                            suggested[var_name] = str(sugg)
                except:
                    # 如果無法獲取值，跳過
                    pass
            
            return facts, suggested
        else:
            return None, None
            
    except Exception as e:
        print(f"❌ 求解過程出錯: {e}")
        return None, None


def compare_values(initial, suggested):
    """
    比較初始值和建議值，處理數值、Bool 和分數
    """
    if isinstance(initial, bool) and isinstance(suggested, bool):
        return initial == suggested
    elif isinstance(initial, (int, float)) and isinstance(suggested, (int, float)):
        return abs(float(initial) - float(suggested)) < 1e-6
    else:
        return str(initial).lower() == str(suggested).lower()


def optimize_case(case_id):
    """
    主程式：輸入 case_id，執行 optimize 求解並顯示結果
    """
    print(f"\n{'='*60}")
    print(f"🔍 正在處理: {case_id}")
    print(f"{'='*60}\n")
    
    # 載入數據
    constraint_spec, facts, varspecs = load_case_data(case_id)
    if constraint_spec is None:
        return
    
    print(f"\n📊 初始事實:")
    for k, v in facts.items():
        print(f"   {k}: {v}")
    
    # 執行求解
    print(f"\n⏳ 正在求解...")
    initial, suggested = solve_case(constraint_spec, facts, varspecs)
    
    if initial and suggested:
        print(f"\n✅ 求解成功!\n")
        
        # 計算變化
        changes = []
        num_changes = 0
        for k in sorted(suggested.keys()):
            initial_val = initial.get(k, "N/A")
            suggested_val = suggested.get(k, "N/A")
            
            if k in initial:
                if not compare_values(initial_val, suggested_val):
                    changes.append(f"   ⚠️  {k}: {initial_val} → {suggested_val}")
                    num_changes += 1
                else:
                    changes.append(f"   ✓ {k}: {initial_val}")
            else:
                changes.append(f"   ✨ {k}: {suggested_val} (新增)")
        
        print(f"📝 建議模型 (共 {num_changes} 個變化):\n")
        for change in changes:
            print(change)
        
        # 輸出詳細信息
        print(f"\n{'='*60}")
        print(f"📋 詳細結果:")
        print(f"{'='*60}")
        print(f"變化數量: {num_changes}")
        print(f"總變量數: {len(suggested)}")
        print(f"狀態: 成功")
        
    else:
        print(f"\n❌ 求解失敗或無解")
        print(f"狀態: 無解或錯誤")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方式:")
        print("  python optimize_single_case.py case_0")
        print("  python optimize_single_case.py 0")
        print("\n範例:")
        print("  python optimize_single_case.py case_5")
        sys.exit(1)
    
    case_id = sys.argv[1]
    optimize_case(case_id)
