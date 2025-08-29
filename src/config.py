"""
InvisibleChat configuration (OpenRouter edition)

Keep DEFAULT_ALPHA = 1.0 for your first working run; set to 0.8 later if you
want translucency.
"""

# === OpenRouter endpoint (note /api/v1 !) ===
API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

APP_TITLE = "InvisibleChat"
DEFAULT_ALPHA = 1.0

# Keyring identifiers (new key name so you’ll be prompted again)
KEYRING_SERVICE = "InvisibleChat"
KEYRING_KEY = "openrouter_api_key"

# Model (auto routing is fine; you can pin a free model later)
# Examples that are often available free: 
#   "deepseek/deepseek-chat:free"
#   "cognitivecomputations/dolphin3.0-r1-mistral-24b:free"
MODEL = "openrouter/auto"

HTTP_TIMEOUT_SECS = 60
USER_AGENT = f"{APP_TITLE}/2.4 (+Windows)"

# Bias coding answers toward runnable Java 17 programs.
SYSTEM_PROMPT = (
    "You are a precise coding assistant. When the user asks programming questions, "
    "prefer Java 17 and return a complete, runnable example with:\n"
    "- a single public class Main\n"
    "- a public static void main(String[] args) entry point\n"
    "- only the necessary imports.\n"
    "Keep explanations brief unless asked. For non-coding questions, answer normally."
)

# Logging verbosity (INFO during setup; set to ERROR to reduce noise)
DEFAULT_LOG_LEVEL = "INFO"
