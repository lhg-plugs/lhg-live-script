#!/usr/bin/env python3
"""lhg-live-script 硬门：直播脚本交付前合规检查。

触发：PreToolUse / Bash。脚本先判断本次 Bash 命令是否为"交付"
（命令含 live-script-deliver 标记——这是 /lhg-live-script:live-script
在用户确认交付时插入的标记），不是则 0 开销直接放行；是则对
delivery/ 目录跑 live_audit.py。

命中 blocker（违禁词 5 类）→ 拦截交付；只有 warning/nit → 提醒式放行。

逃生方式（按推荐度排序）：
  1. 修好违禁词后重新交付（推荐）。
  2. 紧急情况：LHG_LS_HOOKS_OFF=1 <交付命令>（单次豁免本次 hook）。
  3. /plugin disable lhg-live-script（整个插件停用，hooks 不再触发）。

设计原则：脚本内部出错（找不到审计脚本、解析失败等）时 fail-open
直接放行，不因插件自身故障骚扰用户；真正的门禁在
/lhg-live-script:live-audit。零第三方依赖。
"""

import json
import os
import re
import subprocess
import sys

DELIVER_RE = re.compile(r"live-script-deliver", re.I)


def main() -> int:
    # 逃生开关
    if os.environ.get("LHG_LS_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # 输入解析失败：fail-open

    tool_input = payload.get("tool_input", {}) or {}
    command = tool_input.get("command", "") or ""

    # 非交付命令：快速放行
    if not DELIVER_RE.search(command):
        return 0

    try:
        return check_delivery(command)
    except Exception:
        return 0  # 校验自身出错：fail-open


def check_delivery(command):
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..")
    audit_py = os.path.join(plugin_root, "scripts", "audit", "live_audit.py")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    # 允许命令里用 --target 指定目录，否则默认 delivery/
    m = re.search(r"--target\s+(\S+)", command)
    target = m.group(1) if m else os.path.join(project_dir, "delivery")
    if not os.path.isabs(target):
        target = os.path.normpath(os.path.join(project_dir, target))

    if not os.path.isdir(target):
        out = {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": (
                "提醒：交付标记已触发，但未找到脚本目录 %s。"
                "请先把开播脚本放入 delivery/ 再交付，否则跳过此提醒。"
                % target)}}
        sys.stdout.write(json.dumps(out, ensure_ascii=False))
        return 0

    if not os.path.isfile(audit_py):
        return 0  # 审计脚本缺失：fail-open

    try:
        r = subprocess.run(
            [sys.executable, audit_py, "--target", target, "--format", "json"],
            capture_output=True, text=True, timeout=60)
        data = json.loads(r.stdout)
    except Exception:
        return 0  # 审计跑不起来：fail-open

    blockers = [f for f in data.get("findings", [])
                if f.get("severity") == "blocker"]
    warnings = [f for f in data.get("findings", [])
                if f.get("severity") == "warning"]

    if not blockers:
        if warnings:
            out = {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": (
                    "提醒：交付脚本有 %d 个 warning（无 blocker，已放行）。"
                    "建议修或写豁免理由，详见 /lhg-live-script:live-audit。"
                    % len(warnings))}}
            sys.stdout.write(json.dumps(out, ensure_ascii=False))
        return 0

    lines = [
        "交付被 lhg-live-script 硬门拦截：合规审计发现 %d 个 blocker（违禁词），"
        "修好再交付。" % len(blockers),
        "脚本目录：%s" % target,
        "",
    ]
    for f in blockers[:10]:
        lines.append("- [%s] %s — %s" % (
            f.get("rule_id"), f.get("title"), f.get("snippet", "")))
    if len(blockers) > 10:
        lines.append("…另有 %d 个" % (len(blockers) - 10))
    lines += [
        "",
        "修复方式：按 lhg-ls-compliance 第 10 节改写表替换违禁词后重新交付；",
        "紧急豁免（单次）：LHG_LS_HOOKS_OFF=1 <交付命令>",
    ]
    out = {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "\n".join(lines)}}
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
