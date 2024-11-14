import logging
import os
import sys

from dotenv import load_dotenv
from utils.log import setup_logging

load_dotenv(override=True)

# Set up logging
LOG_LEVEL = os.getenv("LOG_LEVEL")
LOG_FORMAT = os.getenv("LOG_FORMAT")
setup_logging(LOG_LEVEL, LOG_FORMAT)
DEFAULT_LOGGER_NAME = os.getenv("DEFAULT_LOGGER_NAME", "ddg")


def get_logger(logger_name: str = DEFAULT_LOGGER_NAME):
    return logging.getLogger(logger_name)

# # # Set up the environment variables
DEFAULT_OPENAI_API_KEY = "AIzaSyDwwPQj1u0dyNi2Cw5pYQGHL82f4vyxmas"
# # IS_AZURE = bool(os.getenv("OPENAI_API_BASE") or os.getenv("AZURE_OPENAI_API_KEY"))
# # EMBEDDINGS_DEPLOYMENT_NAME = os.getenv("EMBEDDINGS_DEPLOYMENT_NAME")
# # CHAT_DEPLOYMENT_NAME = os.getenv("CHAT_DEPLOYMENT_NAME")
GEMINI_API_KEY = "AIzaSyDwwPQj1u0dyNi2Cw5pYQGHL82f4vyxmas"

# WEATHER KEY
WEATHER_KEY = os.getenv("WEATHER_SECRET_KEY", "")


# if USE_CHROMA_VIA_HTTP := bool(os.getenv("USE_CHROMA_VIA_HTTP")):
#     os.environ["CHROMA_API_IMPL"] = "rest"

# # The following three variables are only used if USE_CHROMA_VIA_HTTP is True
# CHROMA_SERVER_HOST = os.getenv("CHROMA_SERVER_HOST", "localhost")
# CHROMA_SERVER_HTTP_PORT = os.getenv("CHROMA_SERVER_HTTP_PORT", "8000")
# CHROMA_SERVER_AUTHN_CREDENTIALS = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS", "")

# # The following variable is only used if USE_CHROMA_VIA_HTTP is False
# VECTORDB_DIR = os.getenv("VECTORDB_DIR", "chroma/")

MODEL_NAME = "gemini-1.5-flash"  # rename to DEFAULT_MODEL?
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.1))

LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", 9))

DEFAULT_MODE = os.getenv("DEFAULT_MODE", "/chat")

hashtags_mapping = {
    "#분위기맛집 🌟": "분위기가 좋은 맛집을 원한다.",
    "#존맛 😋": "맛이 정말 뛰어난 맛집을 찾고 있다",
    "#서비스굿굿 👍": "서비스가 좋은 맛집을 원한다",
    "#가성비갑 💸": "가격 대비 만족도가 높은 맛집을 원한다",
    "#푸짐한음식량 🍽️": "음식 양이 푸짐한 맛집을 찾고 있다",
    "#연인과함께 💑": "연인과 함께 가기 좋은 맛집을 찾고 있다.",
    "#다양한메뉴 📜": "메뉴 선택의 폭이 넓은 맛집을 원한다.",
    "#만족도200프로 😊": "만족도가 매우 높은 맛집을 원한다.",
    "#청결도최상 🧼": "청결하고 위생적인 맛집을 찾고 있다.",
    "#주차편리 🚗": "주차가 편리한 맛집을 원한다.",
    "#위치편리 📍": "위치가 편리한 맛집을 찾고 있다."
}

is_env_loaded = True

jeju_emojis = """Here are some Jeju-themed emojis you can use in chat:
🌴🍊 : Tangerines and palm trees, symbols of Jeju
🌋 : Hallasan Mountain and Jeju’s volcanic landscape
🏖️ : Beautiful beaches, like Hyeopjae Beach
🐴 : Jeju horses, unique to the island
🐬 : Dolphins in Jeju's coastal waters
🍲 : Jeju’s traditional dish, pork noodles (gogi-guksu)
🍵 : Tea from the O’sulloc green tea fields
🌞 : Jeju’s bright and sunny weather
🚗🛣️ : Scenic driving routes around Jeju"""
