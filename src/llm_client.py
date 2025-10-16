# src/llm_client.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def get_client():
    base_url = "https://openrouter.ai/api/v1"
    # prefer OPENAI_API_KEY, else OPENROUTER_API_KEY, else local 'ollama'
    api_key  = os.getenv("OPENROUTER_API_KEY")
    return OpenAI(base_url=base_url, api_key=api_key)

def get_default_model():
    return os.getenv("DEFAULT_MODEL", "deepseek/deepseek-r1:free")
