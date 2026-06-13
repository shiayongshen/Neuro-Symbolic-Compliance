# 神經符號合規分析

神經符號合規分析是一個結合大型語言模型與 Z3 的法律推理管線，用來將法律案例敘述與法條文字轉換成可機器檢查的合規約束、事實與模型。

## 如何引用

如果你在研究或論文中使用這個專案，請引用：

```bibtex
@inproceedings{hsia2025neuro,
  title={Neuro-Symbolic Compliance: Integrating LLMS and SMT Solvers for Automated Financial Legal Analysis},
  author={Hsia, Yung-Shen and Yu, Fang and Jiang, Jie-Hong Roland},
  booktitle={2025 2nd IEEE/ACM International Conference on AI-powered Software (AIware)},
  pages={01--10},
  year={2025},
  organization={IEEE}
}
```

這個專案結合了：

- 大型語言模型：用於法條解析、補完與案例映射
- 規則修復邏輯：修正格式錯誤或彼此矛盾的約束
- Z3：進行形式化驗證、可滿足性檢查與最佳化
- 結構化輸出：便於人工檢視與後續分析

目標是把非結構化的法律文本，轉成可被一致檢查的約束與事實。

## 專案在做什麼

主要入口是 [`main.py`](./main.py)。它會針對 [`dataset/updated_processed_cases.csv`](./dataset/updated_processed_cases.csv) 中的每一列資料執行一個多階段流程。

每個案例大致會經過以下步驟：

1. 從法條文字中抽取候選約束。
2. 補完缺少的規則結構。
3. 驗證並清理產生的 JSON。
4. 從約束中抽取變數規格。
5. 將約束轉成 Z3 表達式，並修復語法問題。
6. 檢查邏輯一致性，必要時修復矛盾。
7. 將案例敘述映射成結構化 facts。
8. 驗證 facts 是否可被 Z3 接受。
9. 檢查案例是否形成違規訊號。
10. 最後執行最佳化並在可能時輸出 SMT2 格式。

流程產生的 JSON、log、模型檔、SMT2 檔與 Excel 摘要都會儲存在 [`outputs/`](./outputs/)。

## Repository 結構

- [`main.py`](./main.py) - 管線總控與結果輸出
- [`config.py`](./config.py) - 透過環境變數設定 LLM
- [`agents/`](./agents) - 用於解析、映射、修復等任務的 AutoGen agents
- [`core/`](./core) - 修復流程與工具函式
- [`find_optimize_result/`](./find_optimize_result) - JSON 轉 Z3 的輔助工具
- [`dataset/`](./dataset) - 輸入資料
- [`outputs/`](./outputs) - 執行後的輸出結果

## 架構概覽

這個專案是一個分階段的 agentic workflow：

- **Statute Parser** - 從法條中抽取法律規則
- **Completion** - 擴充並標準化抽取出的約束
- **VarSpec Agent** - 從約束中推導變數型別與 metadata
- **Constraint Repair Agent** - 修正語法錯誤或結構問題
- **Case Mapper** - 將案例文字轉成 facts
- **Penalty / Repair 邏輯** - 協助修復約束與 satisfiability 問題
- **Z3 層** - 驗證表達式、檢查可滿足性、產生模型

這些 agent 由 [`agents/orchestrator.py`](./agents/orchestrator.py) 統一串接。

## 輸入資料

流程預期 CSV 內至少要有兩個語意欄位：

- 案例文字
- 法條文字

這兩個欄位可以使用中文或英文命名。支援的別名如下：

- 案例文字：`法律案例`, `case`, `case_text`, `case_narrative`, `legal_case`, `legal_case_text`, `facts`
- 法條文字：`相關法條`, `statute`, `statute_text`, `relevant_statute`, `law_text`, `legal_provision`

預設資料檔搜尋順序如下：

- `dataset/updated_processed_cases.csv`
- `../updated_processed_cases.csv`
- `../data_preprocess/updated_processed_cases.csv`

如果這些路徑都找不到，程式會在啟動時直接報錯。

## 需求

- Python 3.13
- [`uv`](https://docs.astral.sh/uv/)
- OpenAI API key

執行時會用到的套件包含：

- `autogen`
- `openai`
- `pandas`
- `openpyxl`
- `z3-solver`
- `python-dotenv`

## 安裝

安裝相依套件：

```bash
uv sync
```

建立或更新 `.env`：

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

注意：

- `OPENAI_API_KEY` 為必填。
- `OPENAI_MODEL` 為選填，不填時預設為 `gpt-4.1-mini`。
- `.env` 不應提交到版本控制。

## 執行

執行主流程：

```bash
uv run python main.py
```

### 目前預設行為

在 [`main.py`](./main.py) 的底部，目前寫的是：

```python
fail_list_path = [0]
main(failed_indices=fail_list_path)
```

所以預設只會處理 `case_0`。

如果要處理整個資料集，可以：

- 把列表改成你想跑的 index
- 或是直接呼叫 `main()`，不要帶過濾條件

## Pipeline 步驟

### 1. 法條解析

Statute Parser 會從法條文字中抽取候選約束，並回傳結構化結果。

### 2. 補完

Parser 會再次被提示，用來補上缺漏的法律結構並提升覆蓋率。

### 3. JSON 驗證

系統會清理輸出並解析成合法 JSON。如果失敗，流程會直接報錯。

### 4. VarSpec 抽取

VarSpec Agent 會找出約束中涉及的變數，並指定型別與 metadata。

### 5. 約束可解析性檢查

系統會把約束轉為 Z3 表達式。如果解析失敗，會啟動修復流程。

### 6. 一致性檢查

系統會檢查約束是否存在邏輯衝突。如果有，會嘗試修復，必要時重新生成 VarSpec。

### 7. Case mapping

Case Mapper 會將案例敘述轉成可被 Z3 使用的 facts。

### 8. Case-law hard check

系統會檢查案例與約束是否形成違規結果。如果結果不符合預期，會嘗試修復策略，讓整體結果趨向 UNSAT。

### 9. 最佳化

最後的約束與 facts 會交給最佳化器產生模型。

### 10. SMT2 匯出

專案可以把結果匯出成 SMT-LIB 格式，方便使用外部 Z3 工具重現。

## 輸出檔案

每個案例可能會在 [`outputs/`](./outputs/) 產生以下檔案：

- `<case_id>.constraint_spec.json`
- `<case_id>.varspecs.json`
- `<case_id>.facts.json`
- `<case_id>.stats.json`
- `<case_id>.log`
- `<case_id>.smt2`
- `<case_id>.model.txt`

完整執行後還會額外輸出：

- `pipeline_statisticsv2.xlsx`

## 輸出內容範例

如果某個案例成功跑完，通常會看到：

- 清理後的 constraint specification
- 變數規格檔
- 由案例推導出的 facts
- Z3 model 的文字輸出
- 可直接拿去重播的 SMT2 檔
- 包含統計與檢查點狀態的 Excel 報表

## 常見問題

### 找不到 `openai` 模組

重新安裝相依套件：

```bash
uv sync
```

### 找不到 `openpyxl` 模組

這個專案會使用 `pandas.ExcelWriter(..., engine="openpyxl")`，因此必須透過 `uv sync` 安裝 `openpyxl`。

### 沒有設定 `OPENAI_API_KEY`

程式會透過 `python-dotenv` 讀取 `.env`。如果 key 缺失，`config.py` 會在啟動時直接失敗。

### 找不到資料集

請確認 CSV 檔存在於前述支援路徑其中之一，而且欄位名稱正確。

### SAT / UNSAT 結果和預期不同

這個專案是以「違規案例」為前提設計的。如果 facts 無法強制違規，系統可能會嘗試修復，或在某些情況下讓案例失敗但仍保留部分輸出。

## 開發備註

- 目前程式結構偏向單一批次處理流程。
- [`main.py`](./main.py) 同時包含 orchestration、log、repair 與 export 邏輯，實際可運作，但未來很適合再拆分。
- 多個模組都包含 domain-specific prompt 與 repair heuristics，因此執行結果高度依賴 LLM 輸出品質。

## 重新跑一次的步驟

1. 執行 `uv sync`
2. 在 `.env` 設定 `OPENAI_API_KEY`
3. 確認資料集存在於 `dataset/updated_processed_cases.csv`
4. 執行 `uv run python main.py`
5. 到 `outputs/` 檢查輸出檔

## 授權

本專案採用 MIT License，詳見 [LICENSE](./LICENSE)。
