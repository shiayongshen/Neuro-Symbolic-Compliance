import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")  # 默认值

# 验证配置
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY 未設定。請在 .env 檔案中設定或設定環境變數。")

if not OPENAI_MODEL:
    print("⚠️ OPENAI_MODEL 未設定，使用默認值: gpt-4.1-mini")
    OPENAI_MODEL = "gpt-4.1-mini"

llm_config = {
    "config_list": [
        {
            "model": OPENAI_MODEL,
            "api_key": OPENAI_API_KEY,
        }
    ],
    "temperature": 0,
    "seed": 42,
}
