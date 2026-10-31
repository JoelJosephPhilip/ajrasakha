import os

from dotenv import load_dotenv

load_dotenv()

# Public MiniMax API only - no self-hosted/Tailscale hop, no automatic
# fallback (explicit product decision: a small, standalone service, not
# worth the dual-mode client writing_assistant needs).
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
# "MiniMax-M3" is the model string the public API actually serves - confirmed
# against writing_assistant's own working deployment config. "MiniMax-M2.7"
# is only ever the self-hosted model name, not a valid public-API value.
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M3")
MINIMAX_CHAT_PATH = os.getenv("MINIMAX_CHAT_PATH", "/text/chatcompletion_v2")
MINIMAX_TIMEOUT_SECONDS = float(os.getenv("MINIMAX_TIMEOUT_SECONDS", "90"))
MINIMAX_SEED = int(os.getenv("MINIMAX_SEED", "0"))
