"""把 awesome-ruankao 上游新增的 2026 内容追加进练题台的 data/bank.json。

用法: python -I add_2026.py <bank.json> <upstream根目录> <上游commit> <报告输出>
- 2026年上半年真题（回忆版）：综合知识、案例分析、论文
- 2026年10月模拟卷3-5：只收与已有题库题干不重复的选择题
已有题目和 ID 一律不动，只追加。
"""
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path

bank_path, up_root, up_commit, report_path = (Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
REAL_TERM = "2026年上半年"
REAL_DIR = up_root / "真题" / "系统架构设计师" / REAL_TERM
MOCK_DIR = up_root / "模拟题" / "系统架构设计师" / "2026年10月"
report = []

bank = json.loads(bank_path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def dedupe_key(q):
    # 完整题干 + 选项；只比前缀会把英语题（都以 According to the passage 开头）误判为重复
    text = q["stem"].split("\n\n")[-1] + "|" + "|".join(q["options"].values())
    return re.sub(r"[\s（）()，。、,.：:“”\"'；;？?！!]", "", text).lower()


def clean(text):
    text = re.sub(r"^\s*-{3,}\s*$", "", text, flags=re.M)  # 去掉 Markdown 分隔线，保留列表的 "- "
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------- 选择题模块归类（关键词，按顺序命中第一个） ----------
MODULE_RULES = [
    ("legal_ip", r"著作权|专利|商标|知识产权|合同|招投标|招标|侵权|标准化|法律|条例"),
    ("security", r"加密|密钥|数字签名|签名|认证|防火墙|SSL|TLS|访问控制|入侵|病毒|攻击|安全|PKI|证书|ACM"),
    ("database", r"数据库|SQL|范式|关系模式|事务|索引|视图|NoSQL|Redis|候选键|主键|函数依赖|数据仓库|分库|元组"),
    ("new_technology", r"Transformer|大模型|人工智能|机器学习|深度学习|神经网络|区块链|物联网|边缘计算|数字孪生|RAG|向量|智能体|Agent|AIGC|生成式"),
    ("architecture", r"架构|风格|微服务|CQRS|SOA|ESB|构件|中间件|质量属性|ATAM|SAAM|DSSA|设计模式|模式|MVC|管道|黑板|事件驱动|ABSD|云原生|Serverless|负载均衡|服务网格"),
    ("network", r"TCP|UDP|IP地址|路由|网络|协议|带宽|DNS|HTTP|子网|交换机|5G|以太网|IPv6"),
    ("embedded", r"嵌入式|实时操作系统|RTOS|实时系统"),
    ("software_engineering", r"需求|测试|UML|用例|敏捷|开发模型|软件过程|CMMI|瀑布|螺旋|维护|重构|配置管理|编译|语法|词法|结构化|面向对象|类图|耦合|内聚|软件|程序"),
    ("computer_foundation", r"进程|线程|调度|存储|Cache|内存|分页|磁盘|RAID|CPU|流水线|指令|操作系统|文件系统|死锁|信号量|中断|总线|计算机"),
    ("project_management", r"进度|关键路径|成本|项目|挣值|决策|线性规划|运筹|利润|最大|最小"),
]
# 关键词分错时按题号手工改正（审阅报告后填写）
REAL_MODULE_OVERRIDES = {
    6: "new_technology", 8: "legal_ip", 12: "new_technology", 14: "new_technology",
    20: "new_technology", 21: "new_technology", 23: "new_technology", 26: "software_engineering",
    27: "network", 29: "computer_foundation", 30: "computer_foundation", 31: "computer_foundation",
    33: "architecture", 34: "software_engineering", 37: "database", 38: "architecture",
    47: "security", 48: "computer_foundation", 49: "architecture", 52: "database",
    57: "architecture", 62: "architecture", 63: "architecture", 64: "project_management",
}


def classify(stem, options):
    text = stem + " " + " ".join(options.values())
    for module, pattern in MODULE_RULES:
        if re.search(pattern, text, re.I):
            return module
    return "other"


# ---------- 2026上半年 综合知识 ----------
def parse_real_choices():
    path = REAL_DIR / "综合知识.md"
    text = path.read_text(encoding="utf-8").split("\n## 未收录题目")[0]
    parts = re.split(r"\n## 第(\d+)题\n", text)[1:]
    items = []
    for no, body in zip(parts[0::2], parts[1::2]):
        no = int(no)
        body = body.split("\n---")[0]
        answer = re.search(r"\*\*验证答案：([A-D])\*\*", body).group(1)
        analysis = re.search(r"\*\*验证依据：\*\*\s*(.+)", body, re.S).group(1)
        head = body.split("**验证答案")[0].strip().splitlines()
        options, stem_lines = OrderedDict(), []
        for line in head:
            m = re.match(r"^([A-D])[.．、]\s*(.*)$", line.strip())
            if m:
                options[m.group(1)] = m.group(2).strip()
            elif not options:
                stem_lines.append(line)
        stem = clean("\n".join(stem_lines))
        module = REAL_MODULE_OVERRIDES.get(no) or classify(stem, options)
        items.append(OrderedDict([
            ("id", f"real-{REAL_TERM}-{no:03d}"), ("sourceType", "real"), ("term", REAL_TERM),
            ("paper", REAL_TERM), ("questionNo", no), ("module", module), ("knowledge", ""),
            ("difficulty", ""), ("stem", stem), ("options", options), ("answer", answer),
            ("analysis", clean(analysis)), ("sourceFile", f"真题/系统架构设计师/{REAL_TERM}/综合知识.md"),
        ]))
    return items


# ---------- 2026上半年 案例分析 ----------
CASE_META = {
    1: ("智慧养老物联网系统（时序数据库、MQTT QoS）", "architecture"),
    2: ("自适应学习与智能辅导系统（冷启动、知识图谱）", "new_technology"),
    3: ("电商秒杀并发控制（悲观锁、乐观锁、Redis）", "database"),
    4: ("AIoT 智能安防四层架构", "architecture"),
    5: ("实时网络入侵检测系统（质量属性、管道-过滤器）", "architecture"),
}


def split_questions(text):
    text = re.sub(r"^(\d)\.（(\d+)分）", r"【问题\1】（\2分）", text, flags=re.M)
    parts = re.split(r"【问题(\d)】(?:（\d+分）)?", text)
    return parts[0], {int(k): clean(v) for k, v in zip(parts[1::2], parts[2::2])}


def parse_real_cases():
    text = (REAL_DIR / "案例分析.md").read_text(encoding="utf-8")
    text = text.split("\n## 答案验证说明")[0]
    blocks = re.split(r"\n# 试题(\d+)\n", text)[1:]
    items = []
    for no, body in zip(blocks[0::2], blocks[1::2]):
        no = int(no)
        body = re.sub(r"^选项内容\.空\s*$", "", body, flags=re.M)
        question_part, answer_part = body.split("## 参考答案")
        desc, prompts = split_questions(question_part)
        _, answers = split_questions(answer_part)
        desc = clean(desc.replace("【说明】", ""))
        subs = []
        for k in sorted(prompts):
            prompt, ref = prompts[k], answers.get(k, "")
            if prompt.startswith("暂缺"):
                continue
            subs.append(OrderedDict([("question_label", f"问题{k}"), ("prompt", prompt),
                                     ("reference_answer", "参考答案:\n\n" + ref if ref else "")]))
        title, module = CASE_META[no]
        items.append(OrderedDict([
            ("id", f"case-real-{REAL_TERM}-{no}"), ("sourceType", "real"), ("term", REAL_TERM),
            ("paper", REAL_TERM), ("module", module), ("title", title), ("description", desc),
            ("subQuestions", subs), ("sourceFile", f"真题/系统架构设计师/{REAL_TERM}/案例分析.md"),
        ]))
    return items


# ---------- 2026上半年 论文 ----------
ESSAY_MODULE = {"一": "database", "二": "architecture", "三": "architecture", "四": "new_technology"}


def parse_real_essays():
    text = (REAL_DIR / "论文.md").read_text(encoding="utf-8")
    blocks = re.split(r"\n## 试题([一二三四])：(.+)\n", text)[1:]
    items = []
    for idx, (cn, title, body) in enumerate(zip(blocks[0::3], blocks[1::3], blocks[2::3]), start=1):
        prompt, points = body.split("### 经验证的核心答题要点")
        items.append(OrderedDict([
            ("id", f"essay-real-{REAL_TERM}-{idx}"), ("sourceType", "real"), ("term", REAL_TERM),
            ("paper", REAL_TERM), ("module", ESSAY_MODULE[cn]), ("title", title.strip()),
            ("prompt", f"请围绕“{title.strip()}”论题，依次从以下三个方面进行论述：\n\n" + clean(prompt)),
            ("writingPoints", clean(points)), ("sourceFile", f"真题/系统架构设计师/{REAL_TERM}/论文.md"),
        ]))
    return items


# ---------- 2026年10月 模拟卷3-5 ----------
SECTION_MODULE = [
    ("计算机基础", "computer_foundation"), ("软件工程", "software_engineering"),
    ("架构", "architecture"), ("信息安全", "security"), ("数据库", "database"),
    ("新技术", "new_technology"), ("可靠性", "computer_foundation"),
    ("知识产权", "legal_ip"), ("英语", "english"),
]


def section_module(name):
    for key, module in SECTION_MODULE:
        if key in name:
            return module
    return "other"


def parse_mock(paper):
    qdir = MOCK_DIR / paper
    qtext = (qdir / "综合知识_题目.md").read_text(encoding="utf-8")
    atext = (qdir / "综合知识_答案.md").read_text(encoding="utf-8")
    answers = {}
    for no, body in re.findall(r"\n### 第(\d+)题\n(.*?)(?=\n### 第\d+题\n|\n## |\Z)", atext, re.S):
        def field(name):
            m = re.search(rf"\*\*{name}\*\*[:：]\s*(.*?)(?=\n\*\*[^*\n]+\*\*[:：]|\n---|\Z)", body, re.S)
            return clean(m.group(1)) if m else ""

        ans = re.search(r"\*\*答案\*\*[:：]\s*([A-D])", body).group(1)
        why = field("押题理由")
        analysis = field("解析") + (f"\n\n押题理由：{why}" if why else "")
        answers[int(no)] = (ans, analysis, field("考点"), field("难度"))
    items, section, intro = [], "", ""
    for chunk in re.split(r"\n(?=## |### 第\d+题\n)", qtext):
        if chunk.startswith("## "):
            section = re.sub(r"^## [一二三四五六七八九十]+、|（.*$", "", chunk.splitlines()[0])
            intro = clean("\n".join(chunk.splitlines()[1:]))
            continue
        m = re.match(r"### 第(\d+)题\n(.*)", chunk, re.S)
        if not m:
            continue
        no, body = int(m.group(1)), m.group(2).split("\n---")[0]
        stem = re.split(r"\n(?:\*\*选项\*\*.*\n)?- A\.", "\n" + body, maxsplit=1)[0]
        options = OrderedDict(re.findall(r"^- ([A-D])\.\s*(.+)$", body, re.M))
        ans, analysis, knowledge, difficulty = answers[no]
        if section_module(section) == "english" and intro:
            stem = intro + "\n\n" + clean(stem)  # 英语阅读题带上文章原文
        items.append(OrderedDict([
            ("id", f"mock-2026年10月-{paper}-{no:03d}"), ("sourceType", "mock"),
            ("term", f"2026年10月 {paper}"), ("paper", paper), ("questionNo", no),
            ("module", section_module(section)), ("knowledge", knowledge or section), ("difficulty", difficulty),
            ("stem", clean(stem)), ("options", options), ("answer", ans), ("analysis", analysis),
            ("sourceFile", f"模拟题/系统架构设计师/2026年10月/{paper}/综合知识_题目.md"),
        ]))
    return items


# ---------- 组装 ----------
existing_ids = {q["id"] for key in ("choices", "cases", "essays") for q in bank[key]}
assert not any(q["term"] == REAL_TERM for q in bank["choices"]), "题库里已有 2026年上半年，脚本不重复追加"

real_choices = parse_real_choices()
real_cases = parse_real_cases()
real_essays = parse_real_essays()

seen_stems = {dedupe_key(q): q for q in bank["choices"]}
mock_new, mock_dup, answer_diff = [], 0, []
for paper in ("模拟卷3", "模拟卷4", "模拟卷5"):
    for q in parse_mock(paper):
        key = dedupe_key(q)
        if key in seen_stems:
            mock_dup += 1
            old = seen_stems[key]
            if old["answer"] != q["answer"]:
                answer_diff.append(f"{q['id']} 答案 {q['answer']} ≠ 已有 {old['id']} 的 {old['answer']}")
            continue
        seen_stems[key] = q
        mock_new.append(q)

# 校验
for q in real_choices + mock_new:
    assert q["stem"] and q["analysis"], q["id"]
    assert list(q["options"]) == ["A", "B", "C", "D"], (q["id"], q["options"])
    assert q["answer"] in q["options"], q["id"]
for item in real_cases:
    assert item["description"] and item["subQuestions"], item["id"]
new_ids = [x["id"] for x in real_choices + mock_new + real_cases + real_essays]
assert len(new_ids) == len(set(new_ids)) and not existing_ids & set(new_ids), "ID 冲突"

bank["choices"].extend(real_choices + mock_new)
bank["cases"].extend(real_cases)
bank["essays"].extend(real_essays)

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
bank["generatedAt"] = now
man = bank["manifest"]
man["generated_at"] = now
man.setdefault("supplemental_sources", []).append(OrderedDict([
    ("name", "awesome-ruankao"), ("url", "https://github.com/wujiaming88/awesome-ruankao.git"),
    ("commit", up_commit),
    ("scope", "2026年上半年真题（考生回忆版：综合知识、案例分析、论文）"
              + (f" + 2026年10月模拟卷3-5中与已有题库不重复的选择题 {len(mock_new)} 道" if mock_new else "")),
    ("choices", len(real_choices) + len(mock_new)), ("cases", len(real_cases)), ("essays", len(real_essays)),
    ("note", "由 add_2026.py 从上游 Markdown 转换追加；已有题目未改动。"),
]))
man["scope"]["real_terms"].append(REAL_TERM)
for term in dict.fromkeys(q["term"] for q in mock_new):
    man["scope"]["mock_terms"].append(term)
choices = bank["choices"]
man["counts"] = OrderedDict([
    ("choice", len(choices)), ("choice_real", sum(q["sourceType"] == "real" for q in choices)),
    ("choice_mock", sum(q["sourceType"] == "mock" for q in choices)),
    ("case", len(bank["cases"])), ("essay", len(bank["essays"])),
])
man["choice_real_by_term"][REAL_TERM] = len(real_choices)
man["module_counts"] = dict(Counter(q["module"] for q in choices))

bank_path.write_text(json.dumps(bank, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

report.append(f"真题选择 {len(real_choices)}，真题案例 {len(real_cases)}（子问题 {sum(len(c['subQuestions']) for c in real_cases)}），真题论文 {len(real_essays)}")
report.append(f"模拟卷新增 {len(mock_new)}（按卷 {dict(Counter(q['paper'] for q in mock_new))}），跳过重复 {mock_dup}")
report.append(f"重复题答案不一致 {len(answer_diff)} 条：" + "；".join(answer_diff[:20]))
report.append("counts: " + json.dumps(man["counts"], ensure_ascii=False))
report.append("\n# 真题模块归类（审阅用）")
for q in real_choices:
    report.append(f"{q['questionNo']:>2} {q['module']:<20} {q['stem'][:46].replace(chr(10), ' ')}")
report.append("\n# 案例")
for c in real_cases:
    report.append(f"{c['id']} {c['title']} 子问题: {[s['question_label'] for s in c['subQuestions']]}")
report.append("\n# 论文")
for e in real_essays:
    report.append(f"{e['id']} {e['title']}")
report_path.write_text("\n".join(report), encoding="utf-8")
