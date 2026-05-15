import json

questions = [
  {
    "title": "请阐述 AI Agent 的核心架构组成（感知-决策-执行循环），并说明每个模块在实际系统中的实现要点和常见挑战。",
    "difficulty": "medium",
    "domain": "agent-arch",
    "questions": [
      "Agent 的「感知-决策-执行」循环是如何工作的？各模块分别承担什么职责？",
      "Planning 模块常见的实现方式有哪些（如 Chain-of-Thought、Tree-of-Thought、ReAct）？它们各自的优缺点是什么？",
      "如何设计 Agent 的 Memory 模块（短期/长期/情景记忆），使 Agent 能在长对话或跨任务场景下保持上下文一致性？",
      "什么是 Agent 的「幻觉」问题？在架构层面可以采取哪些措施降低幻觉率？"
    ],
    "answer": "<p><strong>Agent 架构核心循环</strong></p><p>AI Agent 的运行基于「感知(Perception) → 决策(Planning) → 执行(Action)」的闭环迭代。感知模块负责接收用户输入、环境状态及工具回调，将多模态信息转换为结构化 Context 送入 LLM；决策模块是 Agent 的核心，LLM 在此结合系统提示、记忆和感知输入进行推理，输出下一步行动计划；执行模块将决策转化为实际的 API 调用、代码运行或数据写入操作。</p><p><strong>Planning 策略对比</strong></p><ul><li><strong>ReAct</strong>：交替输出 Thought/Action/Observation，实现推理与行动的紧耦合，适合需要逐步验证的任务；</li><li><strong>Chain-of-Thought</strong>：鼓励模型在给出答案前先进行多步推理，提高复杂问题准确率；</li><li><strong>Tree-of-Thought</strong>：将搜索空间建模为树，支持回溯与多路径探索，适合高难度规划但计算成本高；</li><li><strong>Plan-and-Execute</strong>：先生成完整执行计划，再逐步执行，减少冗余决策调用。</li></ul><p><strong>Memory 设计</strong></p><p>短期记忆通常以 Context Window 内的消息历史实现，长期记忆借助向量数据库存储 Embedding，情景记忆则记录完整的任务轨迹供事后检索。关键设计点：合理的记忆压缩（Summarization）策略、基于相关性的动态检索，以及写入时的去重与版本控制。</p><p><strong>幻觉缓解</strong></p><p>在架构层面可通过：① 工具回调校验（让 Agent 使用搜索/计算工具验证事实）；② Reflection 机制（Agent 自我批判并修正）；③ 多 Agent 互审（Critic Agent 检查输出）；④ 置信度评估与人工兜底等策略降低幻觉。</p>",
    "tips": "重点考察对 ReAct 和 Plan-and-Execute 范式的深度理解，以及 Memory 的分层设计思路，注意区分不同 Planning 策略的适用场景。"
  },
  {
    "title": "详细解释 PagedAttention 和连续批处理（Continuous Batching）技术，说明它们如何共同提升大模型推理吞吐量。",
    "difficulty": "hard",
    "domain": "inference",
    "questions": [
      "KV Cache 在传统静态分配下会产生哪些内存浪费问题？PagedAttention 是如何解决的？",
      "什么是连续批处理（Continuous Batching / Iteration-level Scheduling）？它相比静态批处理有什么优势？",
      "vLLM 是如何将 PagedAttention 与连续批处理结合，实现高吞吐推理服务的？",
      "在实际部署中，如何平衡推理延迟（Latency）和吞吐量（Throughput）的 trade-off？"
    ],
    "answer": "<p><strong>传统 KV Cache 的问题</strong></p><p>传统实现在请求到达时预先为最大序列长度分配连续 KV 缓存内存，导致：① 内碎片：实际生成长度远短于最大长度时，大量内存闲置；② 外碎片：不同长度请求难以紧凑排列，GPU 显存利用率通常只有 20%-40%。</p><p><strong>PagedAttention</strong></p><p>借鉴操作系统虚拟内存的分页思想，将 KV Cache 拆分为固定大小的 Block（典型值 16 tokens/block），通过块表进行逻辑→物理地址映射。不同请求可非连续共享物理内存页，显存碎片率大幅降低，内存利用率提升至接近 100%。Prefix Sharing 可让共享 System Prompt 的请求复用同一组 KV Block，进一步节省显存。</p><p><strong>连续批处理</strong></p><p>静态批处理等待批次内所有请求全部完成才处理下一批，长请求会阻塞短请求。连续批处理在 Iteration 级别调度：每次前向传播结束后立即移除已完成请求、插入新请求，实现批次动态更新，GPU 利用率提升 2-10 倍。</p><p><strong>vLLM 的整合</strong></p><p>vLLM 将 PagedAttention 作为底层 Attention Kernel，结合连续批处理调度器统一管理物理 Block 分配/释放，支持 Preemption（抢占低优先级请求释放显存）和 Swap（将冷 Block 换出到 CPU）。</p><p><strong>延迟 vs. 吞吐 trade-off</strong></p><p>提高批大小可提升吞吐但增加单请求延迟；降低批大小则降低延迟但吞吐下降。实践中可设置 max_num_seqs、token budget，配合 SLA 目标动态调整调度策略。</p>",
    "tips": "需要深入理解 GPU 显存管理原理，重点对比 PagedAttention 与传统连续内存分配的区别，以及连续批处理在 Iteration 层面的调度机制。"
  },
  {
    "title": "设计一个可靠的 Tool Use（工具调用）框架，使 LLM Agent 能够安全、高效地调用外部工具，包括错误处理、并发控制和结果验证机制。",
    "difficulty": "medium",
    "domain": "tool-use",
    "questions": [
      "如何设计工具的描述（Tool Schema）使 LLM 能够准确理解何时及如何调用工具？",
      "当工具调用返回错误或超时时，Agent 应如何进行重试、回退或替换工具？",
      "如何实现工具的并行调用（Parallel Tool Calls）以提升执行效率，同时保证结果正确汇总？",
      "在安全性方面，如何防止 Prompt Injection 攻击通过工具结果影响 Agent 的后续行为？"
    ],
    "answer": "<p><strong>Tool Schema 设计</strong></p><p>高质量的 Tool Schema 是准确工具调用的基础，应包含：① 精准的 description（说明工具的用途、适用场景和限制）；② 严格的参数定义（类型、枚举、必填/可选、示例值）；③ 清晰的错误返回格式规范。避免模糊表述，优先使用动词+名词格式。参数过多时使用嵌套 Object 分组，减少 LLM 的选择负担。</p><p><strong>错误处理与重试策略</strong></p><p>建议实现分级处理：① 可重试错误（网络超时、限速 429）→ 指数退避重试，最多 3 次；② 参数错误 → 将错误信息反馈给 LLM，让其修正参数后重试；③ 不可恢复错误 → 记录日志，尝试替换同功能工具或向用户报告。Reflection 机制可显著提升 Agent 自愈能力。</p><p><strong>并行工具调用</strong></p><p>OpenAI Function Calling 和 Anthropic Tool Use 均支持单次响应返回多个 tool_call。实现并发时：① 识别无依赖的工具调用集合，使用 asyncio.gather 并发执行；② 有依赖的调用保持串行；③ 全部结果收集后统一构建 tool results message 返回 LLM，避免多次无效 LLM 调用。</p><p><strong>安全防护</strong></p><p>防 Prompt Injection 的关键措施：① 工具结果以结构化 JSON 而非纯文本传入，减少指令注入空间；② 对工具结果进行内容过滤，检测可疑指令模式；③ 限制工具输出长度，防止恶意内容淹没 System Prompt；④ 关键操作需二次确认或人工审核。</p>",
    "tips": "重点考察工具描述的设计质量、错误处理的分级策略，以及并行调用的依赖分析能力。安全部分需要结合 Prompt Injection 的实际攻击向量来回答。"
  }
]

print(json.dumps(questions, ensure_ascii=False))
