#!/usr/bin/env python3
"""
Tab2: 面经采集脚本（无需任何 Cookie）
数据源：
  1. 牛客网（follow-nowcoder skill，search-posts 命令）- 主力
  2. 脉脉（有登录态时额外补充，失败静默跳过）
注意：GitHub 来源已移除（内容质量和合规性难以保证）
"""
import json, os, subprocess, datetime, hashlib, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/experiences.json')
SKILLS_DIR = os.path.expanduser('~/.openclaw/workspace/skills')
NOWCODER_CLI = os.path.join(SKILLS_DIR, 'follow-nowcoder/scripts/cli.py')
MAIMAI_BIN = '/root/.local/bin/maimai'
MAX_ITEMS = 100

# ── 相关性关键词（命中任一才保留）──
AGENT_KEYWORDS = [
    'ai agent', 'llm', 'agent', '大模型', '多模态', 'rag', '向量',
    '人工智能', '机器学习', 'nlp', '自然语言', 'transformer',
    'gpt', 'claude', 'gemini', '推理', '微调', 'fine-tun',
    '算法工程师', '实习', '面经', '面试', '腾讯', '字节', '阿里',
]

# ── 合规黑名单（命中任一则丢弃）──
COMPLIANCE_BLOCKLIST = [
    'dictatorship', 'tiananmen', '天安门', 'ccp', '法轮',
    'falun', '台独', '藏独', '港独', '新疆独',
    '色情', '博彩', '赌博', '代刷', '兼职刷单',
]

def is_relevant(text):
    t = text.lower()
    return any(kw in t for kw in AGENT_KEYWORDS)

def is_compliant(title, summary=''):
    text = (title + ' ' + summary).lower()
    return not any(kw.lower() in text for kw in COMPLIANCE_BLOCKLIST)

COMPANY_MAP = {
    '腾讯': 'tencent', 'tencent': 'tencent', 'wechat': 'tencent',
    '字节': 'bytedance', 'bytedance': 'bytedance', 'tiktok': 'bytedance', '抖音': 'bytedance', '豆包': 'bytedance',
    '阿里': 'alibaba', 'alibaba': 'alibaba', '淘宝': 'alibaba', '蚂蚁': 'alibaba',
    '百度': 'baidu', 'baidu': 'baidu', '文心': 'baidu',
    '美团': 'meituan', '快手': 'kuaishou', '小米': 'xiaomi',
    '华为': 'huawei', '京东': 'jd', '滴滴': 'didi', '网易': 'netease',
}

def detect_company(text):
    t = text.lower()
    for kw, c in COMPANY_MAP.items():
        if kw.lower() in t:
            return c
    return 'other'

def detect_position(text):
    t = text.lower()
    if any(k in t for k in ['大模型', 'llm', 'agent', 'nlp']): return 'LLM/Agent 工程师'
    if any(k in t for k in ['算法', 'algorithm', 'research', '研究员']): return 'AI 算法工程师'
    if any(k in t for k in ['推荐', '搜索']): return '推荐/搜索工程师'
    if any(k in t for k in ['实习', 'intern']): return '实习生'
    return 'AI/技术岗'

def quality_score(item):
    score = 4
    if len(item.get('summary', '')) > 80: score += 1
    if item.get('url'): score += 1
    if item.get('company') != 'other': score += 1
    if item.get('platform') == 'nowcoder': score += 1
    return min(score, 10)

def dedup(items):
    seen, out = set(), []
    for item in items:
        key = item.get('id') or hashlib.md5(item.get('title', '').encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out

def load_existing():
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except: return {"items": [], "updated_at": ""}

def verify_nowcoder_url(url):
    """验证牛客 URL 是否真实可访问（过滤内容不存在的帖子）"""
    if not url:
        return False
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0'}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            # 读足够多以覆盖嵌入JSON中的错误信息
            html = r.read(65536).decode('utf-8', errors='replace')
            if '内容不存在' in html or '帖子不存在' in html:
                return False
            return True
    except:
        return False

# ── 牛客（主力，无需 Cookie）──
def fetch_nowcoder():
    if not os.path.exists(NOWCODER_CLI):
        print('[exp] 牛客 CLI 未找到，跳过')
        return []

    items = []
    queries = ['AI Agent', '大模型 面经', 'LLM 工程师', 'RAG 向量数据库']

    for query in queries:
        try:
            result = subprocess.run(
                ['python3', NOWCODER_CLI, 'search-posts', query],
                capture_output=True, text=True, timeout=20
            )
            if result.returncode != 0 or not result.stdout:
                continue
            data = json.loads(result.stdout)
            records = data.get('results', {}).get(query, {}).get('records', [])
            for rec in records:
                title = rec.get('title', '')
                # 相关性 + 合规双重过滤
                if not title or not is_relevant(title):
                    continue
                if not is_compliant(title):
                    continue
                # 阅读量 >= 30 初步过滤刚发即删帖
                if rec.get('view_count', 0) < 30:
                    continue
                uuid = rec.get('uuid', '')
                content_id = rec.get('content_id', '')
                rc_type = rec.get('rc_type', 0)
                # rc_type=201: 面经帖，uuid -> /feed/main/detail/{uuid}
                # rc_type=207: 动态帖，content_id -> /discuss/{content_id}
                if rc_type == 201 and uuid:
                    url = f'https://www.nowcoder.com/feed/main/detail/{uuid}'
                elif rc_type == 207 and content_id:
                    url = f'https://www.nowcoder.com/discuss/{content_id}'
                elif uuid:
                    url = f'https://www.nowcoder.com/feed/main/detail/{uuid}'
                elif content_id:
                    url = f'https://www.nowcoder.com/discuss/{content_id}'
                else:
                    continue
                ts = rec.get('created_at', 0)
                created = datetime.datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d') if ts else datetime.datetime.now().strftime('%Y-%m-%d')
                item = {
                    'id': hashlib.md5((title + uuid + content_id).encode()).hexdigest()[:12],
                    'title': title,
                    'url': url,
                    'summary': f'阅读: {rec.get("view_count",0)} | 评论: {rec.get("comment_count",0)} | 来源: 牛客网',
                    'company': detect_company(title + rec.get('company', '')),
                    'platform': 'nowcoder',
                    'position': rec.get('job_title', '') or detect_position(title),
                    'created_at': created,
                }
                item['quality'] = quality_score(item)
                if item['quality'] >= 4:
                    items.append(item)
        except Exception:
            pass

    items = dedup(items)

    # 并行验证 URL 可访问性
    if items:
        valid = []
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(verify_nowcoder_url, it['url']): it for it in items}
            for fut in as_completed(futures):
                if fut.result():
                    valid.append(futures[fut])
        items = valid

    print(f'[exp] 牛客获取 {len(items)} 条（已验证可访问）')
    return items

# ── 脉脉（可选，有登录态时使用）──
def fetch_maimai():
    if not os.path.exists(MAIMAI_BIN):
        return []
    try:
        check = subprocess.run(
            [MAIMAI_BIN, 'status', '--json'],
            capture_output=True, text=True, timeout=8,
            env={**os.environ, 'PATH': '/root/.local/bin:' + os.environ.get('PATH', '')}
        )
        status = json.loads(check.stdout)
        if not status.get('data', {}).get('looks_logged_in'):
            print('[exp] 脉脉未登录，跳过')
            return []
    except:
        return []
    items = []
    try:
        for kw in ['AI Agent', '大模型 面试']:
            result = subprocess.run(
                [MAIMAI_BIN, 'search', kw, '--section', 'gossips', '--limit', '10', '--json'],
                capture_output=True, text=True, timeout=20,
                env={**os.environ, 'PATH': '/root/.local/bin:' + os.environ.get('PATH', '')}
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                for post in data.get('data', {}).get('gossips', []):
                    text = post.get('text', post.get('content', ''))
                    if not is_relevant(text) or not is_compliant(text):
                        continue
                    title = text[:80]
                    item = {
                        'id': hashlib.md5((title + str(post.get('id', ''))).encode()).hexdigest()[:12],
                        'title': title,
                        'url': post.get('url', ''),
                        'summary': text[:300],
                        'company': detect_company(post.get('company', '') + ' ' + text),
                        'platform': 'maimai',
                        'position': detect_position(text),
                        'created_at': datetime.datetime.now().strftime('%Y-%m-%d'),
                    }
                    item['quality'] = quality_score(item)
                    if item['quality'] >= 4:
                        items.append(item)
    except Exception as e:
        print(f'[exp] 脉脉采集失败: {e}')
    print(f'[exp] 脉脉获取 {len(items)} 条')
    return items

def main():
    print(f'[exp] 开始采集 {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}...')
    existing = load_existing()
    existing_ids = {item['id'] for item in existing.get('items', [])}

    all_items = []
    all_items += fetch_nowcoder()
    all_items += fetch_maimai()

    all_items = dedup(all_items)
    new_items = [i for i in all_items if i.get('id') not in existing_ids]

    merged = new_items + existing.get('items', [])
    merged = dedup(merged)[:MAX_ITEMS]

    if not new_items:
        print('[exp] 本次未获取到新内容')
    else:
        print(f'[exp] ✅ 新增 {len(new_items)} 条，共 {len(merged)} 条')

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "items": merged,
            "updated_at": datetime.datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
