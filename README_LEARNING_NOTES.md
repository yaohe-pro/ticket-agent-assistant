# Enterprise Ticket Agent Assistant

一个面向企业工单处理场景的 Agent 应用雏形。

项目目标是演示：如何用 LangGraph 组织工单处理流程，用 DeepSeek 生成回复草稿，并在关键动作前加入人工审核和处理日志。

## 功能

- 读取模拟工单数据
- 判断工单类别和优先级
- 知识类工单自动检索企业知识库
- 将投诉式工单内容改写成适合检索的标准问题
- 按类别、优先级和关键词相似度读取历史工单，作为上下文记忆参考
- 读取同一工单的历史处理记录，避免重复处理时丢失上下文
- 如果发现同一工单已处理过，人工审核前进行二次确认
- 重复工单如果选择不继续，会在 RAG 和 LLM 调用前提前停止
- 调用 DeepSeek 生成客服回复草稿
- 人工审核回复草稿
- 审核通过后发送，审核拒绝后等待人工修改
- 保存工单处理日志
- 分析历史处理日志，包括审核结果、类别、优先级和知识库使用情况
- 分析历史记忆是否被使用
- 记录本次参考了哪些历史工单，方便审计和排错
- 统计本次处理前是否已有同一工单历史
- 统计重复工单提醒后的人工选择
- 提供 Streamlit 网页页面，可以选择工单、查看流程、审核草稿和查看日志统计

## 项目结构

```text
ticket-agent-assistant/
├── main.py
├── streamlit_app.py
├── analyze_logs.py
├── eval_classification.py
├── eval_duplicate_policy.py
├── eval_memory_retrieval.py
├── inspect_memory.py
├── run_all_evals.py
├── PROJECT_REVIEW.md
├── STREAMLIT_PRODUCT_SUMMARY.md
├── data/
│   ├── classification_eval_report.json
│   ├── duplicate_policy_eval_report.json
│   ├── evaluation_summary.json
│   ├── memory_retrieval_eval_report.json
│   └── ticket_process_log.json
└── ticket_agent/
    ├── agent.py
    ├── classifier.py
    ├── llm.py
    ├── policy.py
    ├── rag.py
    ├── storage.py
    ├── web_workflow.py
    └── ticket_data.py
```

## 运行方式

先进入项目目录并激活虚拟环境：

```bash
cd /Users/yaohe/Desktop/agent—study/ticket-agent-assistant
source ../.venv/bin/activate
```

配置环境变量：

```bash
cp .env.example .env
```

然后在 `.env` 中填写你的 DeepSeek API Key：

```text
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

运行工单 Agent：

```bash
python main.py
```

运行 Streamlit 网页版：

```bash
streamlit run streamlit_app.py --server.port 8502
```

然后打开：

```text
http://localhost:8502
```

可测试工单编号：

```text
T1001
T1002
T1003
```

分析处理日志：

```bash
python analyze_logs.py
```

评估工单分类和优先级：

```bash
python eval_classification.py
```

评估重复工单处理策略：

```bash
python eval_duplicate_policy.py
```

评估历史记忆检索：

```bash
python eval_memory_retrieval.py
```

查看某个工单会匹配到哪些历史记忆：

```bash
python inspect_memory.py
```

一键运行全部评估：

```bash
python run_all_evals.py
```

运行后会生成评估报告：

```text
data/classification_eval_report.json
data/duplicate_policy_eval_report.json
data/evaluation_summary.json
data/memory_retrieval_eval_report.json
```

## Agent 流程

```text
读取工单
-> 判断类别和优先级
-> 读取同一工单历史
-> 如果是重复工单，先确认是否继续处理
-> 如果选择不继续，直接保存日志并停止
-> 读取相似历史工单
-> 将知识类工单改写成标准检索问题
-> 知识类工单检索企业知识库
-> DeepSeek 生成回复草稿
-> 人工审核
-> 审核通过：发送回复
-> 审核拒绝：等待人工修改
-> 保存处理日志
```

## 核心模块

- `ticket_agent/agent.py`：LangGraph 工单处理主流程
- `ticket_agent/classifier.py`：工单分类和优先级规则
- `ticket_agent/llm.py`：DeepSeek API 调用封装
- `ticket_agent/policy.py`：重复工单等业务策略
- `ticket_agent/rag.py`：复用企业知识库 RAG 检索器
- `ticket_agent/storage.py`：JSON 日志读写和关键词打分式历史工单检索
- `ticket_agent/ticket_data.py`：模拟工单数据
- `ticket_agent/web_workflow.py`：网页版本专用流程，把终端确认改成按钮确认
- `main.py`：命令行运行入口
- `streamlit_app.py`：Streamlit 网页产品入口
- `analyze_logs.py`：日志分析入口
- `eval_classification.py`：分类和优先级评估入口
- `eval_duplicate_policy.py`：重复工单策略评估入口
- `eval_memory_retrieval.py`：历史记忆检索评估入口
- `inspect_memory.py`：历史记忆匹配过程检查工具
- `run_all_evals.py`：一键运行全部评估并生成总览报告
- `MEMORY_STATE_HITL_SUMMARY.md`：记忆、状态和人工确认阶段总结
- `STREAMLIT_PRODUCT_SUMMARY.md`：网页产品化阶段总结
- `PROJECT_REVIEW.md`：项目复盘和面试讲解材料
- `data/classification_eval_report.json`：分类评估报告
- `data/duplicate_policy_eval_report.json`：重复工单策略评估报告
- `data/evaluation_summary.json`：全部评估总览报告
- `data/memory_retrieval_eval_report.json`：历史记忆检索评估报告

## 面试可讲点

- 使用 LangGraph 把工单处理拆成多个可控节点
- 用 State 保存工单编号、内容、分类、优先级、草稿和审核状态
- 对知识类工单先检索企业知识库，再生成回复草稿
- 使用 Streamlit 把命令行 Agent 产品化为可演示网页
- 将终端 `input()` 式人工确认改造成网页按钮式人工审核
- 对“知识库没找到产品介绍”这类投诉式表达做查询改写，提高召回和回复质量
- 把历史处理日志作为长期记忆，并用关键词相似度优先召回更相关的历史工单
- 读取同一工单历史，让 Agent 知道当前工单是否被处理过
- 对重复工单增加二次确认，避免不小心重复发送
- 将重复工单确认前置，选择停止时不再调用 RAG 和大模型
- 把重复工单处理规则抽成策略模块，并提供策略评估脚本
- 用 DeepSeek 生成回复草稿，但不让模型直接执行最终动作
- 在回复发送前加入人工审核节点，体现 human-in-the-loop
- 将处理结果保存为 JSON 日志，支持后续审计和评估
- 提供日志统计分析，观察审核通过率、工单类别和优先级分布
- 记录知识类工单是否使用了企业知识库资料
- 记录每次处理是否使用了历史记忆
- 记录每次处理参考的历史工单编号，让记忆来源可追踪
- 记录处理前已有多少条同一工单历史
- 提供分类评估脚本，验证工单类别和优先级规则是否命中预期
- 提供历史记忆评估脚本，验证相似历史工单是否能被正确召回
- 提供一键评估入口，汇总分类、策略和记忆检索的测试结果

## 当前阶段

这是第二个作品项目的第一版工程化雏形，已经完成命令行版工单 Agent、RAG 接入、历史记忆、重复工单确认、日志分析、评估闭环和 Streamlit 网页产品化。阶段总结见 `MEMORY_STATE_HITL_SUMMARY.md` 和 `STREAMLIT_PRODUCT_SUMMARY.md`。

后续计划继续加入：

- 更真实的工单数据
- 把关键词历史匹配升级为向量相似度匹配
- 页面中的评估报告展示
- 评估用例
- GitHub 项目整理
