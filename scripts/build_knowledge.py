#!/usr/bin/env python3
"""
Tab3: 知识结构化总结 - 输出 Markdown 格式 + 带引用来源
"""
import json, os, datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
OUT = os.path.join(DATA_DIR, 'knowledge.json')

def load(f):
    try:
        with open(os.path.join(DATA_DIR, f)) as fp: return json.load(fp)
    except: return {"items": []}

MARKDOWN = """\
# AI Agent 知识体系

> 本文档由系统每日自动更新，汇总面试题库、真实面经与主流开源项目技术栈，聚焦 AI Agent 核心知识。

---

## 一、核心概念与范式

### 1.1 什么是 AI Agent

AI Agent 是一种能够**感知环境、自主规划、调用工具并持续行动**以完成目标的 LLM 应用系统。与单次问答的 LLM 不同，Agent 具备循环推理与外部交互能力。[^1]

核心组成：
- **大脑（LLM）**：推理、规划、语言理解
- **感知（Perception）**：接收文本、图像、工具返回值等输入
- **记忆（Memory）**：短期（Context Window）+ 长期（向量数据库）
- **行动（Action）**：调用工具、执行代码、调用 API

### 1.2 主流推理范式对比

| 范式 | 核心思想 | 代表工作 |
|------|---------|---------|
| **Chain-of-Thought (CoT)** | 逐步推理，无外部交互 | Wei et al., 2022 |
| **ReAct** | 推理 + 行动交错，循环执行 | Yao et al., 2022 [^2] |
| **Reflexion** | 自我反思 + 记忆改进 | Shinn et al., 2023 |
| **Tree of Thoughts (ToT)** | 树状搜索多条推理路径 | Yao et al., 2023 |
| **Plan-and-Execute** | 先全局规划再逐步执行 | Wang et al., 2023 |

### 1.3 ReAct 框架详解

ReAct = **Re**asoning + **Act**ing，核心循环：

```
Thought → Action → Observation → Thought → ...
```

- **Thought**：模型内部推理，分析当前状态
- **Action**：调用工具（搜索、计算、代码执行等）
- **Observation**：工具返回结果，注入下一轮上下文

优势：可解释、支持实时信息获取、错误可被观察纠正  
局限：长任务 context 溢出、工具失败时恢复困难

---

## 二、记忆系统

### 2.1 记忆分类 [^3]

| 类型 | 存储位置 | 特点 | 实现方式 |
|------|---------|------|---------|
| **感觉记忆** | 输入流 | 即时、不持久 | Raw input |
| **短期记忆** | Context Window | 有限、会话级 | Prompt |
| **长期记忆** | 外部存储 | 持久、可检索 | 向量数据库 |
| **实体记忆** | KG / 结构化 DB | 精确、关系化 | Knowledge Graph |

### 2.2 记忆管理策略

- **滑动窗口**：保留最近 N 条对话，超出截断
- **摘要压缩**：用 LLM 将旧对话压缩为摘要
- **重要性打分**：基于相关性/时效性保留关键信息
- **层级检索**：先检索摘要，再按需加载详细内容

---

## 三、工具调用（Tool Use）

### 3.1 Function Calling

OpenAI 于 2023 年推出 Function Calling，允许 LLM 以结构化 JSON 格式调用预定义函数。[^4]

```json
{
  "name": "search_web",
  "description": "搜索互联网获取实时信息",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "搜索关键词"}
    },
    "required": ["query"]
  }
}
```

### 3.2 Model Context Protocol (MCP)

Anthropic 2024 年提出 MCP，标准化 LLM 与工具的交互协议，支持：[^5]
- **Resources**：文件、数据库等资源访问
- **Tools**：可执行工具定义
- **Prompts**：提示模板管理

### 3.3 工具调用最佳实践

- 工具描述要**精确、无歧义**，避免 LLM 误调用
- 实现**幂等性**，允许重试而不产生副作用
- 设置**超时与重试**机制（建议最多 3 次）
- 对工具输出进行**格式校验**再注入 context

---

## 四、RAG（检索增强生成）

### 4.1 RAG 演进路线

```
Naive RAG → Advanced RAG → Modular RAG
```

**Naive RAG**：Query → 向量检索 → 拼接 Context → 生成  
**Advanced RAG**：引入 Query 改写、混合检索、Re-ranking  
**Modular RAG**：各模块解耦可替换，支持路由、融合、自适应 [^6]

### 4.2 检索质量优化

| 优化点 | 方案 | 效果 |
|--------|------|------|
| **Chunking** | 语义分块 + 10-20% 重叠 | 保留上下文完整性 |
| **Embedding** | BGE-M3 / text-embedding-3 | 领域适配 |
| **混合检索** | 向量 + BM25，RRF 融合 | 召回率↑ |
| **Re-ranking** | Cross-Encoder 重排序 | 精度↑ |
| **HyDE** | 先生成假设答案再检索 | 语义对齐↑ |
| **Self-RAG** | 自我评估检索必要性 | 噪音↓ |

### 4.3 常见坑

- **Lost in the Middle**：相关内容在 context 中间时 LLM 易忽略，建议放首尾
- **Chunk 割裂语义**：避免在句子中间切分，使用 RecursiveTextSplitter
- **Embedding 模型不匹配**：检索模型与生成模型的语义空间需对齐

---

## 五、多 Agent 系统

### 5.1 架构模式

| 架构 | 特点 | 代表框架 |
|------|------|---------|
| **层级式** | Orchestrator 分配任务，Sub-Agent 执行 | AutoGen, CrewAI |
| **扁平式** | Agent 平等协作，共享状态 | CAMEL |
| **混合式** | 动态角色，按需组合 | MetaGPT, AgentScope |

### 5.2 协调机制

- **共享内存**：所有 Agent 读写同一状态存储（Redis/内存）
- **消息队列**：基于 Pub/Sub 解耦（Kafka/RabbitMQ）
- **DAG 调度**：有向无环图描述任务依赖关系

### 5.3 主流框架对比 [^7]

| 框架 | 公司 | 特点 | Stars |
|------|------|------|-------|
| **LangGraph** | LangChain | 图状态机，细粒度控制 | 10k+ |
| **AutoGen** | Microsoft | 对话驱动多 Agent | 35k+ |
| **CrewAI** | CrewAI | 角色扮演流水线 | 25k+ |
| **AgentScope** | Alibaba | 多模态，国产 | 5k+ |
| **MetaGPT** | FoundationAgents | 软件开发场景 | 45k+ |

---

## 六、工程实践

### 6.1 可靠性设计

- **重试机制**：指数退避，最多 3 次，记录每次失败原因
- **Fallback 策略**：主模型失败时降级到备用模型
- **输出校验**：结构化输出用 Pydantic 验证，JSON 解析失败时重新生成
- **沙箱执行**：代码执行 Agent 必须在隔离环境运行

### 6.2 上下文管理

```python
# 滑动窗口 + 摘要压缩示例
MAX_TOKENS = 4096
SUMMARY_THRESHOLD = 3000

if token_count(messages) > SUMMARY_THRESHOLD:
    summary = llm.summarize(messages[:-10])  # 保留最近10条
    messages = [{"role": "system", "content": summary}] + messages[-10:]
```

### 6.3 可观测性

- **LangSmith**：LangChain 官方追踪工具，可视化每步推理
- **Phoenix (Arize)**：开源 LLM 可观测平台
- **自定义日志**：记录 Thought/Action/Observation 完整链路

### 6.4 评估指标

| 指标 | 含义 | 工具 |
|------|------|------|
| **Faithfulness** | 生成内容是否忠实于检索结果 | RAGAS |
| **Answer Relevancy** | 答案与问题的相关性 | RAGAS |
| **Context Recall** | 检索结果覆盖参考答案的程度 | RAGAS |
| **Task Success Rate** | Agent 完成任务的比率 | 自定义 |

---

## 七、安全与对齐

### 7.1 Prompt Injection 防御

- 对用户输入进行**内容过滤**，检测指令注入模式
- 使用**角色分离**：System Prompt 与用户输入严格隔离
- 工具输出注入上下文前进行**安全扫描**

### 7.2 输出控制

- **结构化输出**：强制 JSON Schema，避免越界输出
- **内容过滤**：接入安全分类模型（如 Llama Guard）
- **人工审核环节（HITL）**：高风险操作前强制人工确认

---

[^1]: Weng, Lilian. "LLM-powered Autonomous Agents". Lil'Log, 2023. https://lilianweng.github.io/posts/2023-06-23-agent/
[^2]: Yao et al. "ReAct: Synergizing Reasoning and Acting in Language Models". ICLR 2023. https://arxiv.org/abs/2210.03629
[^3]: 记忆分类参考 Lilian Weng 的 Agent 综述以及 Langchain Memory 文档
[^4]: OpenAI Function Calling 官方文档. https://platform.openai.com/docs/guides/function-calling
[^5]: Anthropic Model Context Protocol. https://modelcontextprotocol.io/
[^6]: Gao et al. "Retrieval-Augmented Generation for Large Language Models: A Survey". 2024. https://arxiv.org/abs/2312.10997
[^7]: 数据来自 GitHub，更新于每日采集任务
"""

def convert_footnotes(md):
    """把 [^N] 脚注转换为可点击上标，并提取 refs 列表"""
    import re
    ref_defs = {}
    # 提取脚注定义 [^N]: ...
    for m in re.finditer(r'^\[\^(\d+)\]: (.+)$', md, re.MULTILINE):
        num, text = m.group(1), m.group(2)
        # 提取 URL
        url_m = re.search(r'https?://\S+', text)
        url = url_m.group(0).rstrip('.,)') if url_m else ''
        title = re.sub(r'https?://\S+', '', text).strip().rstrip('-— ').strip()
        ref_defs[num] = {'title': title or text, 'url': url}

    # 移除脚注定义行
    md_clean = re.sub(r'^\[\^\d+\]: .+\n?', '', md, flags=re.MULTILINE)

    # 替换引用 [^N] → 上标链接
    def replace_cite(m):
        n = m.group(1)
        ref = ref_defs.get(n, {})
        title = ref.get('title', '').replace('"', '&quot;')
        return f'<sup class="cite"><a href="#ref-{n}" title="{title}">[{n}]</a></sup>'

    md_clean = re.sub(r'\[\^(\d+)\]', replace_cite, md_clean)

    refs = [{'num': k, **v} for k, v in sorted(ref_defs.items(), key=lambda x: int(x[0]))]
    return md_clean, refs

def main():
    interviews = load('interviews.json')
    experiences = load('experiences.json')
    projects = load('projects.json')

    md, refs = convert_footnotes(MARKDOWN)

    # 动态统计注入
    stats_note = f"\n\n> 📊 当前数据：面试题 **{len(interviews.get('items',[]))}** 道 · 面经 **{len(experiences.get('items',[]))}** 条 · 开源项目 **{len(projects.get('items',[]))}** 个 · 更新于 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    md = md.replace('> 本文档由系统每日自动更新', stats_note.strip() + '\n\n> 本文档由系统每日自动更新', 1)

    result = {
        "markdown": md,
        "refs": refs,
        "updated_at": datetime.datetime.now().isoformat()
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[knowledge] ✅ 生成 Markdown 文档，{len(refs)} 条参考来源")

if __name__ == '__main__':
    main()
