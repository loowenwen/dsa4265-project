import os


VERY_HIGH_INCOME_THRESHOLD = 1_000_000
LOAN_TO_INCOME_MULTIPLIER_ALERT = 1.5
DTI_MEDIUM_THRESHOLD = 43.0

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
EXPLANATION_MODEL = os.getenv("EXPLANATION_MODEL", "openai/gpt-oss-120b:free")
EXPLANATION_TIMEOUT_SECONDS = float(os.getenv("EXPLANATION_TIMEOUT_SECONDS", "20"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
)
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost")
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "credit-risk-explainer")
