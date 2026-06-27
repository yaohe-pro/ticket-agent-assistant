def classify_ticket_content(content: str) -> dict:
    if "支付" in content or "开通" in content or "价格" in content or "套餐" in content:
        category = "billing_question"
        priority = "high" if "支付成功" in content or "没有开通" in content else "medium"
    elif "登录" in content or "验证码" in content or "账号" in content:
        category = "account_issue"
        priority = "high" if "无法进入" in content or "多次" in content else "medium"
    elif "打不开" in content or "影响" in content or "加载很慢" in content or "处理中" in content:
        category = "system_issue"
        priority = "high" if "影响" in content or "一直" in content else "medium"
    elif "课程" in content or "直播" in content or "培训课程" in content:
        category = "schedule_question"
        priority = "high" if "今天" in content or "影响" in content else "medium"
    elif "投诉" in content or "一直没有回复" in content:
        category = "complaint"
        priority = "high"
    elif (
        "产品" in content
        or "人群" in content
        or "适合" in content
        or "题目解析" in content
        or "知识库问答" in content
        or "AI 学习助手" in content
    ):
        category = "knowledge_question"
        priority = "medium"
    else:
        category = "unknown"
        priority = "low"

    return {
        "category": category,
        "priority": priority,
    }
