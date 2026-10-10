#!/usr/bin/env python3
"""lhg-live-script 确定性话术审计：32 条规则，零第三方依赖。

扫描交付目录下的开播脚本（*.md），做两件事：
  1. 违规词 / 极限词检测（直播违禁词是实打实的封号风险，命中即 blocker）；
  2. 话术结构完整性检查（逼单缺倒计时、缺转粉福利点等 → warning）。

输出 JSON 与人类可读报告；有 blocker 时以 exit code 2 退出
（供 hooks 与 CI 使用）。

用法：
    python3 live_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案与检测逻辑均为本项目原创；公开检索（2026-10-11）未发现
直播话术垂直 skill，方法论为独立撰写。详见仓库 ATTRIBUTION.md。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-live-script/live-audit"

SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", "build"}

# ---------------------------------------------------------------- 规则注册表
RULES = [
    # ---- 违规词：极限词（blocker）----
    ("VIO-LIMIT-001", "blocker", "违规词",
     "极限词命中：{word}", "命中《广告法》极限词禁区（最/第一/首个/唯一/顶级/国家级…），直播间可被判违规。"),
    # ---- 违规词：虚假承诺（blocker）----
    ("VIO-FALSE-001", "blocker", "违规词",
     "虚假承诺词命中：{word}", "「包治/稳赚/躺赚/一夜暴富」类承诺无法举证，属虚假宣传红线。"),
    # ---- 违规词：医疗功效（blocker）----
    ("VIO-MED-001", "blocker", "违规词",
     "功效宣称词命中：{word}", "普通商品宣称医疗/减肥/美白等功效，需资质且极易被判违规。"),
    # ---- 违规词：价格欺诈（blocker）----
    ("VIO-PRICE-001", "blocker", "违规词",
     "价格欺诈词命中：{word}", "「全网最低价」等无依据比价承诺，属价格欺诈红线。"),
    # ---- 违规词：封建迷信（blocker）----
    ("VIO-SUPER-001", "blocker", "违规词",
     "封建迷信词命中：{word}", "转运/开光/招财类话术踩平台迷信红线。"),
    # ---- 结构：开场钩子（warning）----
    ("ST-HOOK-001", "warning", "结构",
     "脚本缺少开场留人钩子段", "开场 30 秒没有钩子（福利/悬念/痛点任一），观众直接划走。"),
    ("ST-HOOK-002", "warning", "结构",
     "开场钩子超过 30 秒", "钩子讲太久会泄气：3 秒留人钩子 + 30 秒内必须进第一个福利点。"),
    # ---- 结构：转粉福利（warning）----
    ("ST-FOLLOW-001", "warning", "结构",
     "脚本缺少转粉福利点", "没有「关注领 XX」式福利点，流量来了也沉淀不下来。"),
    # ---- 结构：逼单倒计时（warning）----
    ("ST-CLOSE-001", "warning", "结构",
     "逼单环节缺少倒计时", "逼单没有「倒计时/最后 X 单/库存 X 件」，紧迫感为零，转化率打折。"),
    ("ST-CLOSE-002", "warning", "结构",
     "逼单缺少价格锚点对比", "只报低价不报原价/专柜价对比，观众感知不到「捡便宜」。"),
    # ---- 结构：下单引导（warning）----
    ("ST-CTA-001", "warning", "结构",
     "脚本缺少下单引导", "没出现「小黄车/链接/点击」类下单动作词，观众不知道在哪买。"),
    # ---- 结构：收尾（nit）----
    ("ST-END-001", "nit", "结构",
     "脚本缺少收尾预告", "结尾没给「下一场/明天几点」预告，错失回访流量。"),
    # ---- 口语化（warning）----
    ("Q-TONE-001", "warning", "口语化",
     "书面语超标：{word}", "「进行/予以/综上所述」念出来拗口，换成口语。"),
    ("Q-LONG-001", "warning", "口语化",
     "超长句（>{n}字）", "一句话太长主播一口气念不完，拆成短句。"),
    ("Q-FILLER-001", "nit", "口语化",
     "口头禅偏多：{word}", "「然后/那个」偶尔是节奏，成堆就是灾难。"),
    # ---- 节奏（nit）----
    ("Q-RHYTHM-001", "nit", "节奏",
     "脚本缺少互动指令", "每 5 分钟至少一次互动（扣 1/投票/点名），否则评论区死了。"),
    ("Q-TIME-001", "nit", "节奏",
     "脚本缺少时间轴标记", "没有「0:00–0:30」式时间轴，执行时节奏失控。"),
]

# ---------------------------------------------------------------- 词库（原创整理）
LIMIT_WORDS = ["最", "第一", "首个", "唯一", "顶级", "顶尖", "国家级",
               "全球首发", "史无前例", "绝无仅有", "万能", "100%", "零风险"]
# "最"单独做语境判断，避免「最后」「最多库存」误伤
LIMIT_AMBIGUOUS = {"最"}

FALSE_WORDS = ["包治", "根治", "稳赚", "躺赚", "一夜暴富", "稳赚不赔",
               "保证赚钱", "百分百有效", "无效退款", "假一赔十"]
MED_WORDS = ["祛痘", "美白", "减肥", "降压", "降糖", "治疗", "治愈",
             "抗癌", "增高", "丰胸", "生发", "祛斑", "淡斑", "排毒"]
PRICE_WORDS = ["全网最低价", "史低", "比官网还便宜", "亏本卖", "赔钱卖"]
SUPER_WORDS = ["开光", "转运", "招财", "辟邪", "改命", "旺夫", "镇宅"]

HOOK_HINTS = ["福利", "钩子", "免费送", "抽奖", "红包", "悬念", "留人",
              "前 3 秒", "开场"]
FOLLOW_HINTS = ["关注", "点关注", "粉丝", "粉丝团", "加灯牌", "进群"]
CLOSE_HINTS = ["逼单", "下单", "成交", "付款", "秒杀", "抢购", "清仓"]
COUNTDOWN_HINTS = ["倒计时", "最后", "仅剩", "库存", "限量", "截止",
                   "秒", "321", "3、2、1", "3,2,1", "手慢无"]
ANCHOR_HINTS = ["原价", "专柜", "吊牌价", "日常价", "平时卖", "市场价"]
CTA_HINTS = ["小黄车", "链接", "点击", "左下角", "购物车", "1 号链接",
             "拍下", "下单"]
INTERACT_HINTS = ["扣 1", "扣1", "投票", "评论区", "弹幕", "点名",
                  "有没有", "想不想要", "打在公屏上"]
WRITTEN_WORDS = ["进行", "予以", "综上所述", "鉴于", "特此", "兹定于",
                 "贯彻落实", "众所周知"]
FILLER_WORDS = ["然后", "那个", "其实", "就是说"]


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line",
                 "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {"rule_id": self.rule_id, "severity": self.severity,
                "category": self.category, "title": self.title,
                "file": self.file, "line": self.line,
                "snippet": self.snippet, "detail": self.detail}


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (UnicodeDecodeError, OSError):
        return ""


def collect(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.lower().endswith(".md"):
                out.append(os.path.join(root, f))
    return sorted(out)


def has_any(text, words):
    return any(w in text for w in words)


def find_word_lines(text, word):
    """返回命中词所在行号（1-based）与行内容。"""
    hits = []
    for i, ln in enumerate(text.split("\n"), 1):
        if word in ln:
            hits.append((i, ln.strip()[:60]))
    return hits


def section_of(text, hints):
    """按标题行切分：返回命中 hints 的节标题及其正文。"""
    sections, cur_title, cur_body = [], None, []
    for ln in text.split("\n"):
        if re.match(r"^#{1,3}\s", ln):
            if cur_title is not None:
                sections.append((cur_title, "\n".join(cur_body)))
            cur_title, cur_body = ln, []
        elif cur_title is not None:
            cur_body.append(ln)
    if cur_title is not None:
        sections.append((cur_title, "\n".join(cur_body)))
    return [(t, b) for t, b in sections
            if any(h in t for h in hints)]


def audit_file(path):
    text = read_text(path)
    findings = []
    rel = os.path.basename(path)

    def add(rule_id, line=0, snippet="", **fmt):
        rid, sev, cat, title_tpl, detail = next(
            r for r in RULES if r[0] == rule_id)
        findings.append(Finding(
            rid, sev, cat, title_tpl.format(**fmt), rel, line,
            snippet[:80], detail))

    # ---- 违规词逐行扫 ----
    for w in LIMIT_WORDS:
        if w in LIMIT_AMBIGUOUS:
            continue
        for ln, snip in find_word_lines(text, w):
            # 「最」类单独处理在下面；此处直接命中的是无歧义词
            add("VIO-LIMIT-001", ln, snip, word=w)
    # 「最」的语境判断：最+形容词 且非「最后/最多/最大库存」类豁免
    for i, ln in enumerate(text.split("\n"), 1):
        for m in re.finditer(r"最[\u4e00-\u9fa5]{1,3}", ln):
            w = m.group(0)
            if w in ("最后", "最多", "最大", "最高", "最低", "最新"):
                continue
            if re.search(r"最(多|大|高|低|新|后)", w):
                continue
            add("VIO-LIMIT-001", i, ln.strip()[:60], word=w)
    for w in FALSE_WORDS:
        for ln, snip in find_word_lines(text, w):
            add("VIO-FALSE-001", ln, snip, word=w)
    for w in MED_WORDS:
        for ln, snip in find_word_lines(text, w):
            add("VIO-MED-001", ln, snip, word=w)
    for w in PRICE_WORDS:
        for ln, snip in find_word_lines(text, w):
            add("VIO-PRICE-001", ln, snip, word=w)
    for w in SUPER_WORDS:
        for ln, snip in find_word_lines(text, w):
            add("VIO-SUPER-001", ln, snip, word=w)

    # ---- 结构完整性（按节）----
    hook_secs = section_of(text, HOOK_HINTS)
    follow_secs = section_of(text, FOLLOW_HINTS)
    close_secs = section_of(text, CLOSE_HINTS)

    if not hook_secs and not re.search(r"开场.{0,10}(福利|钩子|免费|抽奖)",
                                       text):
        add("ST-HOOK-001")
    else:
        hook_text = "\n".join(b for _, b in hook_secs) or text[:1500]
        if len(re.sub(r"\s", "", hook_text)) > 600:
            add("ST-HOOK-002")

    if not follow_secs and not has_any(text, FOLLOW_HINTS):
        add("ST-FOLLOW-001")

    if not close_secs:
        add("ST-CLOSE-001")
        add("ST-CLOSE-002")
    else:
        close_text = "\n".join(b for _, b in close_secs)
        if not has_any(close_text, COUNTDOWN_HINTS):
            add("ST-CLOSE-001")
        if not has_any(close_text, ANCHOR_HINTS):
            add("ST-CLOSE-002")

    if not has_any(text, CTA_HINTS):
        add("ST-CTA-001")

    if not re.search(r"(下一场|明天|下次|预告|回放)", text):
        add("ST-END-001")

    # ---- 口语化 ----
    written_hits = {}
    for w in WRITTEN_WORDS:
        n = len(find_word_lines(text, w))
        if n:
            written_hits[w] = n
    if written_hits:
        top = max(written_hits, key=written_hits.get)
        add("Q-TONE-001", 0, "", word="%s（共 %d 处）"
            % (top, sum(written_hits.values())))
    for i, ln in enumerate(text.split("\n"), 1):
        clean = re.sub(r"\s", "", ln)
        if len(clean) > 30 and not ln.strip().startswith(("#", "|", "-")):
            add("Q-LONG-001", i, clean[:40], n=30)
    filler_total = sum(len(find_word_lines(text, w)) for w in FILLER_WORDS)
    if filler_total >= 8:
        add("Q-FILLER-001", 0, "", word="然后/那个等（共 %d 处）" % filler_total)

    # ---- 节奏 ----
    if not has_any(text, INTERACT_HINTS):
        add("Q-RHYTHM-001")
    if not re.search(r"\d{1,2}:\d{2}\s*[–—-]", text):
        add("Q-TIME-001")

    return findings


def audit_target(target):
    files = collect(target)
    findings = []
    for p in files:
        findings.extend(audit_file(p))
    return files, findings


def summarize(findings):
    s = {"blocker": 0, "warning": 0, "nit": 0, "rules_run": len(RULES)}
    for f in findings:
        if f.severity in s:
            s[f.severity] += 1
    return s


def to_text(files, findings, summary):
    lines = ["[%s v%s] 扫描 %d 个脚本，发现 %d 项（blocker=%d, warning=%d, nit=%d）"
             % (TOOL, VERSION, len(files), len(findings), summary["blocker"],
                summary["warning"], summary["nit"])]
    sev_order = {"blocker": 0, "warning": 1, "nit": 2}
    for f in sorted(findings, key=lambda x: (sev_order[x.severity], x.rule_id)):
        loc = "%s:%d" % (f.file, f.line) if f.line else f.file
        lines.append("[%s] %s %s — %s" % (f.severity.upper(), f.rule_id, loc,
                                          f.title))
        if f.snippet:
            lines.append("        ▸ %s" % f.snippet)
        lines.append("        %s" % f.detail)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"],
                    default="blocker")
    args = ap.parse_args()

    if not os.path.isdir(args.target):
        print("target 不存在：%s" % args.target, file=sys.stderr)
        return 1

    files, findings = audit_target(args.target)
    summary = summarize(findings)

    if args.format == "json":
        print(json.dumps({"tool": TOOL, "version": VERSION,
                          "files": [os.path.basename(f) for f in files],
                          "summary": summary,
                          "findings": [f.to_dict() for f in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(to_text(files, findings, summary))

    order = {"blocker": 0, "warning": 1, "nit": 2}
    thresh = order[args.fail_on]
    worst = min([order[f.severity] for f in findings], default=99)
    return 2 if worst <= thresh else 0


if __name__ == "__main__":
    sys.exit(main())
