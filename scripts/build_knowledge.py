#!/usr/bin/env python3
"""
Tab3: 知识结构化总结脚本
- 汇总面试题、面经、开源项目技术栈
- 生成结构清晰的知识文档
- 输出到 data/knowledge.json
"""
import json
import os
import datetime
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
KNOWLEDGE_FILE = os.path.join(DATA_DIR, 'knowledge.json')

def load_json(fname):
    try:
        with open(os.path.join(DATA_DIR, fname)) as f:
            return json.load(f)
    except:
        return {"items": []}

def extract_topics_from_interviews(interviews):
    """从面试题中提取核心知识点"""
    topics = {}
    for item in interviews.get('items', []):
        title = item.get('title', '')
        questions = item.get('questions', [])
        for q in questions:
            # 简单提取关键词
            for kw in ['ReAct', 'RAG', 'Agent', 'LLM', '向量', 'Embedding', '工具调用', 'Function Call', 'MCP', 'Planning', 'Memory']:
                if kw.lower() in (title + q).lower():
                    topics[kw] = topics.get(kw, 0) + 1
    return topics

def extract_tech_from_projects(projects):
    """从开源项目中提取技术栈"""
    techs = {}
    for item in projects.get('items', []):
        lang = item.get('language', '')
        if lang:
            techs[lang] = techs.get(lang, 0) + 1
        desc = item.get('description', '').lower()
        for kw in ['pytorch', 'transformers', 'fastapi', 'redis', 'elasticsearch', 'qdrant', 'chroma', 'faiss']:
            if kw in desc:
                techs[kw] = techs.get(kw, 0) + 1
    return techs

def build_knowledge(interviews, experiences, projects):
    """构建结构化知识文档"""
    
    # 统计面经中的高频公司
    company_counts = {}
    for exp in experiences.get('items', []):
        c = exp.get('company', 'other')
        company_counts[c] = company_counts.get(c, 0) + 1
    
    # 构建知识结构
    sections = [
        {
            "id": "overview",
            "title": "AI Agent 核心概念",
            "icon": "🧠",
            "type": "concepts",
            "concepts": [
                {"name": "ReAct", "desc": "Reasoning + Acting，推理与行动交错执行的 Agent 范式"},
                {"name": "RAG", "desc": "检索增强生成，将外部知识库与 LLM 结合"},
                {"name": "Tool Use", "desc": "Function Calling / MCP，让 LLM 调用外部工具和 API"},
                {"name": "Memory", "desc": "短期记忆（Context）+ 长期记忆（向量数据库）+ 实体记忆"},
                {"name": "Planning", "desc": "任务分解（Task Decomposition）与子任务调度"},
                {"name": "Multi-Agent", "desc": "多 Agent 协作，Orchestrator + Sub-Agent 架构"},
                {"name": "Self-Reflection", "desc": "Reflexion、自我批评与迭代改进机制"},
                {"name": "Grounding", "desc": "将 LLM 输出与实际环境/工具结果对齐"},
            ]
        },
        {
            "id": "frameworks",
            "title": "主流框架与技术栈",
            "icon": "🔧",
            "type": "subsections",
            "subsections": [
                {
                    "title": "Agent 框架",
                    "items": [
                        "LangChain / LangGraph：最广泛使用的 LLM 应用框架，Graph-based 状态管理",
                        "AutoGen（微软）：多 Agent 对话框架，支持人类参与循环",
                        "CrewAI：角色扮演式多 Agent 协作，适合任务流水线",
                        "Camel：角色扮演通信框架，早期多 Agent 研究代表",
                        "MetaGPT：将 Agent 定义为职场角色（PM/Dev/QA），软件开发场景",
                        "AgentScope（阿里）：多模态多 Agent 平台，国产代表",
                    ]
                },
                {
                    "title": "向量数据库",
                    "items": [
                        "Chroma：轻量级，适合开发测试",
                        "Qdrant：高性能，Rust 实现，支持过滤",
                        "Weaviate：内置 ML 模型，图文多模态",
                        "FAISS（Meta）：高效相似度搜索，不支持实时更新",
                        "Milvus：企业级，云原生向量数据库",
                    ]
                },
                {
                    "title": "LLM 推理服务",
                    "items": [
                        "vLLM：PagedAttention，高吞吐量推理",
                        "Ollama：本地运行 LLM，开发友好",
                        "TGI（HuggingFace）：生产级文本生成推理",
                        "SGLang：结构化生成，高性能",
                        "llama.cpp：CPU 推理，量化支持",
                    ]
                }
            ]
        },
        {
            "id": "interview_hotspots",
            "title": "面试高频考点",
            "icon": "🎯",
            "type": "subsections",
            "subsections": [
                {
                    "title": "算法与模型",
                    "items": [
                        "Transformer 注意力机制：Self-Attention、Multi-Head Attention、KV Cache",
                        "RLHF 流程：SFT → Reward Model → PPO/DPO",
                        "RAG 优化：Chunking 策略、混合检索、Re-ranking、HyDE",
                        "Prompt Engineering：Few-shot、CoT、Self-Consistency、ToT",
                        "Fine-tuning：LoRA/QLoRA、PEFT、全量微调 vs 参数高效微调",
                    ]
                },
                {
                    "title": "工程实践",
                    "items": [
                        "Agent 可靠性：重试机制、工具调用失败处理、幂等性设计",
                        "上下文管理：滑动窗口、摘要压缩、重要信息保留策略",
                        "评估体系：Faithfulness、Relevance、Coherence 等指标",
                        "延迟优化：流式输出、并行工具调用、缓存策略",
                        "安全与对齐：Prompt Injection 防御、输出过滤、沙箱执行",
                    ]
                },
                {
                    "title": "系统设计",
                    "items": [
                        "大规模 Agent 系统架构：任务队列、状态持久化、分布式协调",
                        "Memory 系统设计：分层存储、遗忘策略、重要性打分",
                        "Tool Registry：工具注册与发现、能力描述规范（OpenAPI/MCP）",
                        "可观测性：Tracing（LangSmith/Phoenix）、日志、指标监控",
                    ]
                }
            ]
        },
        {
            "id": "companies",
            "title": "各大厂 Agent 方向",
            "icon": "🏢",
            "type": "subsections",
            "subsections": [
                {
                    "title": "腾讯",
                    "items": [
                        "混元大模型 + Agent 能力集成",
                        "企业微信 AI Agent 平台",
                        "游戏 NPC 智能体（IEG）",
                        "代码 Agent（工蜂 AI）",
                    ]
                },
                {
                    "title": "字节跳动",
                    "items": [
                        "豆包大模型 / Coze Agent 平台",
                        "Seed 基础模型团队",
                        "推荐系统 + LLM 融合",
                    ]
                },
                {
                    "title": "阿里巴巴",
                    "items": [
                        "通义千问（Qwen 系列）",
                        "AgentScope 开源框架",
                        "阿里云百炼 Agent 平台",
                    ]
                },
                {
                    "title": "百度",
                    "items": [
                        "文心大模型 / ERNIE",
                        "千帆 Agent 平台",
                        "AppBuilder 低代码 Agent 构建",
                    ]
                }
            ]
        },
        {
            "id": "resources",
            "title": "学习资源",
            "icon": "📖",
            "type": "list",
            "items": [
                "《Building LLM Powered Applications》- Valentina Alto",
                "LangChain 官方文档：https://python.langchain.com",
                "AutoGen 官方文档：https://microsoft.github.io/autogen",
                "LLM Agents 综述论文：A Survey on Large Language Model based Autonomous Agents",
                "Hugging Face Agents Course：免费在线课程",
                "LangGraph 教程：State Machine for LLM Apps",
                "Andrew Ng AI Agent 系列短课（Coursera/DeepLearning.AI）",
                "牛客网 AI Agent 面经专区",
            ]
        }
    ]
    
    return {
        "sections": sections,
        "updated_at": datetime.datetime.now().isoformat(),
        "stats": {
            "total_interview_questions": len(interviews.get('items', [])),
            "total_experiences": len(experiences.get('items', [])),
            "total_projects": len(projects.get('items', [])),
        }
    }

def main():
    print(f"[knowledge] 开始生成结构化知识 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}...")
    
    interviews = load_json('interviews.json')
    experiences = load_json('experiences.json')
    projects = load_json('projects.json')
    
    knowledge = build_knowledge(interviews, experiences, projects)
    
    with open(KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(knowledge, f, ensure_ascii=False, indent=2)
    
    print(f"[knowledge] ✅ 生成 {len(knowledge['sections'])} 个知识节点")

if __name__ == '__main__':
    main()
