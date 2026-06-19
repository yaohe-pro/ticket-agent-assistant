import os
from pathlib import Path

from dotenv import load_dotenv
from openai import APIConnectionError, OpenAI


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STUDY_ROOT = PROJECT_ROOT.parent
RAG_PROJECT_ROOT = STUDY_ROOT / "enterprise-rag-assistant"

load_dotenv(STUDY_ROOT / ".env")
load_dotenv(STUDY_ROOT / "rag_learning" / ".env")
load_dotenv(RAG_PROJECT_ROOT / ".env")
load_dotenv()


def create_deepseek_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError(
            "没有读取到 DEEPSEEK_API_KEY，请检查 rag_learning/.env 或 "
            "enterprise-rag-assistant/.env。"
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )


def call_deepseek(prompt: str) -> str:
    client = create_deepseek_client()

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
    except APIConnectionError as error:
        raise RuntimeError(
            "连接 DeepSeek 失败，请检查网络、代理或稍后重试。"
        ) from error

    return response.choices[0].message.content.strip()
