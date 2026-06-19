import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STUDY_ROOT = PROJECT_ROOT.parent
RAG_PROJECT_ROOT = STUDY_ROOT / "enterprise-rag-assistant"
RAG_APP_DIR = RAG_PROJECT_ROOT / "app"
RAG_DOCS_DIR = RAG_PROJECT_ROOT / "data" / "docs"

sys.path.append(str(RAG_APP_DIR))

from rag_utils import create_ensemble_retriever_from_folder  # noqa: E402


def rewrite_ticket_question(ticket_content: str) -> str:
    if "产品" in ticket_content or "产品介绍" in ticket_content:
        return "蓝海科技有哪些主要产品？"

    if "人群" in ticket_content or "适合" in ticket_content:
        return "蓝海科技的目标用户和适用人群是谁？"

    return ticket_content


def format_docs(docs: list) -> str:
    context_parts = []

    for doc in docs:
        source = Path(doc.metadata.get("source", "未知来源")).name
        chunk_id = doc.metadata.get("chunk_id", "未知分块")
        context_parts.append(
            f"来源文件：{source}\n分块编号：{chunk_id}\n内容：{doc.page_content}"
        )

    return "\n\n".join(context_parts)


def score_doc(query: str, doc) -> int:
    content = doc.page_content
    score = 0

    if "产品" in query:
        strong_keywords = ["主要产品", "产品包括", "AI 学习助手", "智能题库", "问答系统"]
        weak_negative_keywords = ["没有在知识库中提供", "产品资料"]

        for keyword in strong_keywords:
            if keyword in content:
                score += 3

        for keyword in weak_negative_keywords:
            if keyword in content:
                score -= 2

    if "目标用户" in query or "适用人群" in query or "人群" in query:
        user_keywords = ["目标用户", "大学生", "培训机构", "企业员工", "知识管理团队"]

        for keyword in user_keywords:
            if keyword in content:
                score += 3

    return score


def rerank_docs(query: str, docs: list) -> list:
    scored_docs = []

    for doc in docs:
        scored_docs.append((score_doc(query, doc), doc))

    scored_docs.sort(key=lambda item: item[0], reverse=True)

    reranked_docs = [doc for score, doc in scored_docs if score > 0]

    if not reranked_docs:
        return docs[:2]

    return reranked_docs[:3]


def retrieve_knowledge(question: str) -> dict:
    rewritten_query = rewrite_ticket_question(question)

    retriever = create_ensemble_retriever_from_folder(
        str(RAG_DOCS_DIR),
        vector_k=2,
        bm25_k=2,
        vector_weight=0.5,
        bm25_weight=0.5,
        chunk_size=80,
        chunk_overlap=10,
    )

    raw_docs = retriever.invoke(rewritten_query)
    docs = rerank_docs(rewritten_query, raw_docs)

    return {
        "docs": docs,
        "query": rewritten_query,
        "context": format_docs(docs),
    }
