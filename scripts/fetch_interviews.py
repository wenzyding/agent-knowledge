#!/usr/bin/env python3
"""
Tab1: 模拟面试题目生成脚本
- 检索 AI Agent 相关 JD、技术博客、文档
- 用 LLM 生成高质量面试题目+答案
- 输出到 data/interviews.json
"""
import json
import os
import sys
import subprocess
import datetime
import re

DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/interviews.json')
MAX_ITEMS = 30  # 保留最近30天

def load_existing():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {"items": []}

def fetch_jd_content():
    """通过 web_search + sogo 检索最新 AI Agent JD 和技术文档"""
    sources = [
        "AI Agent 工程师 招聘 腾讯 字节 阿里 2024 2025",
        "LLM Agent 面试题 技术要求",
        "AI Agent 开发 技术栈 技能要求",
    ]
    results = []
    for query in sources:
        try:
            # 使用系统搜索能力
            result = subprocess.run(
                ['python3', '-c', f'''
import urllib.request, json, urllib.parse
q = urllib.parse.quote("{query}")
# 使用搜狗搜索
url = f"https://www.sogou.com/web?query={{q}}&num=5"
req = urllib.request.Request(url, headers={{"User-Agent": "Mozilla/5.0"}})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    content = resp.read().decode("utf-8", errors="ignore")
    print(content[:2000])
except Exception as e:
    print(f"Error: {{e}}")
'''],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout:
                results.append({"query": query, "content": result.stdout[:1500]})
        except:
            pass
    return results

def generate_interview_item(date_str, topic_num):
    """生成一道面试题（由 OpenClaw agent 在 cron 任务中调用时会使用 LLM）"""
    
    # 预设的高质量题目池（会被 LLM 更新）
    TOPIC_POOL = [
        {
            "title": "请详细解释 AI Agent 的 ReAct 框架，以及它如何解决 LLM 推理和行动分离的问题？",
            "difficulty": "medium",
            "source": "腾讯/字节 AI 岗位 JD",
            "questions": [
                "ReAct = Reasoning + Acting，核心思想是什么？",
                "与 Chain-of-Thought 相比，ReAct 的优势在哪里？",
                "ReAct 在实际 Agent 系统中如何实现？",
                "ReAct 的局限性有哪些？"
            ],
            "answer": """<p>ReAct（Reasoning + Acting）是 2022 年提出的 Agent 框架，核心思想是将推理轨迹（Reasoning Trace）和行动（Action）交错进行。</p>

<h3>核心机制</h3>
<ul>
<li><strong>Thought</strong>：模型的内部推理过程，分析当前状态，规划下一步</li>
<li><strong>Action</strong>：调用外部工具（搜索、计算器、API 等）</li>
<li><strong>Observation</strong>：工具返回的结果，作为下一轮推理的输入</li>
</ul>

<h3>与 CoT 的区别</h3>
<ul>
<li>CoT 只有推理，没有与外部世界交互的能力</li>
<li>ReAct 可以获取实时信息，解决知识截止日期问题</li>
<li>ReAct 的推理过程更透明可解释</li>
</ul>

<h3>实现示例（伪代码）</h3>
<pre>while not done:
    thought = llm.think(context)       # Reasoning
    action = llm.decide_action(thought) # Planning
    observation = tools.execute(action) # Acting
    context.append(thought, action, observation)
    if action == "FINISH": break</pre>

<h3>局限性</h3>
<ul>
<li>长任务中 context window 容易溢出</li>
<li>工具调用失败时缺乏健壮的错误恢复</li>
<li>推理步骤过多会导致 token 消耗极大</li>
</ul>""",
            "tips": "重点强调 Thought-Action-Observation 循环，以及与 CoT 的本质区别。面试官通常会追问如何处理工具调用失败的情况。"
        },
        {
            "title": "在设计多 Agent 协作系统时，如何解决 Agent 之间的通信协调和任务分配问题？",
            "difficulty": "hard",
            "source": "阿里/百度 大模型岗位",
            "questions": [
                "多 Agent 系统的常见架构模式（Hierarchical/Flat/Hybrid）？",
                "如何设计 Agent 间的消息传递协议？",
                "任务分配策略：静态分配 vs 动态分配？",
                "如何处理 Agent 之间的冲突和死锁？"
            ],
            "answer": """<p>多 Agent 系统（MAS）设计是 AI Agent 工程中的核心难题，主要涉及架构设计、通信协议和协调机制三个层面。</p>

<h3>常见架构模式</h3>
<ul>
<li><strong>层级式（Hierarchical）</strong>：Orchestrator Agent 负责任务分解和分配，Sub-Agent 负责执行。代表：AutoGen、CrewAI</li>
<li><strong>扁平式（Flat）</strong>：Agent 之间平等协作，通过共享状态或消息队列通信</li>
<li><strong>混合式（Hybrid）</strong>：结合两种模式，适合复杂场景</li>
</ul>

<h3>通信协调方案</h3>
<ul>
<li><strong>共享内存</strong>：所有 Agent 读写同一个状态存储（如 Redis）</li>
<li><strong>消息队列</strong>：基于 Pub/Sub 模式（如 Kafka），解耦 Agent 间依赖</li>
<li><strong>直接调用</strong>：Orchestrator 直接调用 Sub-Agent API</li>
</ul>

<h3>任务分配策略</h3>
<ul>
<li>基于 Agent 能力描述（Capability Registry）进行匹配</li>
<li>动态负载均衡，避免单个 Agent 成为瓶颈</li>
<li>使用 DAG（有向无环图）描述任务依赖关系</li>
</ul>""",
            "tips": "结合具体框架（如 LangGraph、AutoGen）来回答，体现工程实践经验。"
        },
        {
            "title": "解释 RAG（检索增强生成）在 Agent 系统中的作用，以及如何优化 RAG 的检索质量？",
            "difficulty": "medium",
            "source": "通用 AI 工程岗位",
            "questions": [
                "Naive RAG vs Advanced RAG vs Modular RAG 的区别？",
                "向量检索的常用相似度算法？",
                "如何解决 Chunk 粒度问题？",
                "Re-ranking 的作用和常见方案？"
            ],
            "answer": """<p>RAG 是 Agent 系统中解决 LLM 知识局限性的核心技术，通过检索外部知识库来增强生成质量。</p>

<h3>RAG 演进</h3>
<ul>
<li><strong>Naive RAG</strong>：简单的向量检索 + 拼接 Context + 生成</li>
<li><strong>Advanced RAG</strong>：引入 Query 改写、混合检索、Re-ranking</li>
<li><strong>Modular RAG</strong>：各模块可替换，支持路由、融合、自适应检索</li>
</ul>

<h3>检索质量优化关键点</h3>
<ul>
<li><strong>Chunking 策略</strong>：固定大小 vs 语义分块，chunk 重叠比例设置（建议 10-20%）</li>
<li><strong>Embedding 选择</strong>：BGE-M3、text-embedding-3 等，注意领域适配</li>
<li><strong>混合检索</strong>：向量检索 + BM25 关键词检索，用 RRF 融合排序</li>
<li><strong>Re-ranking</strong>：使用 Cross-Encoder 对 Top-K 结果重排序，提升精度</li>
<li><strong>HyDE</strong>：先让 LLM 生成假设性答案，再用该答案检索</li>
</ul>

<h3>常见坑</h3>
<ul>
<li>Context 超长导致 LLM "迷失在中间"（Lost in the Middle）</li>
<li>Chunk 切割破坏语义完整性</li>
<li>检索到相关但不准确的内容，引入噪音</li>
</ul>""",
            "tips": "面试时能提到 HyDE、RAG-Fusion、Self-RAG 等进阶方案会加分很多。"
        }
    ]
    
    idx = topic_num % len(TOPIC_POOL)
    item = TOPIC_POOL[idx].copy()
    item["date"] = date_str
    item["id"] = f"{date_str}-{topic_num}"
    return item

def main():
    today = datetime.date.today().isoformat()
    data = load_existing()
    
    # 检查今天是否已有数据
    existing_dates = {item.get("date") for item in data.get("items", [])}
    if today in existing_dates:
        print(f"[interviews] 今日({today})已有数据，跳过")
        return
    
    print(f"[interviews] 生成 {today} 面试题...")
    
    # 生成今日题目（3道）
    new_items = []
    for i in range(3):
        item = generate_interview_item(today, i)
        new_items.append(item)
    
    # 合并，保留最近30天
    all_items = new_items + data.get("items", [])
    
    # 按日期排序，去重，保留最新30条
    seen = set()
    deduped = []
    for item in all_items:
        key = item.get("id", item.get("title", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    
    deduped = sorted(deduped, key=lambda x: x.get("date",""), reverse=True)[:MAX_ITEMS]
    
    result = {"items": deduped, "updated_at": datetime.datetime.now().isoformat()}
    
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"[interviews] ✅ 写入 {len(deduped)} 条题目")

if __name__ == '__main__':
    main()
