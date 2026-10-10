---
description: 话术自检：对交付目录跑 32 条确定性规则（违禁词 5 类+结构完整性+口语化），blocker 清零才算过。
argument-hint: [脚本目录] [--strict]
---

# /lhg-live-script:live-audit —— 话术自检

用户输入在 `$ARGUMENTS` 中：`[脚本目录] [--strict]`。`--strict` = warning 也算失败（大促前用）。

全程加载 `lhg-ls-compliance` 指导，自检可分派给 `compliance-reviewer` agent。

## 流程

### 1. 跑确定性脚本
```bash
python3 scripts/audit/live_audit.py --target <脚本目录> --format text
# 严格模式：
python3 scripts/audit/live_audit.py --target <脚本目录> --format text --fail-on warning
```

### 2. 分级处理
- **blocker**（违禁词 5 类）：必须改，改完重跑，直到清零。
- **warning**（结构缺件/口语化）：修，或写豁免理由（记在审计报告里）。
- **nit**（节奏/时间轴）：顺手修。

### 3. 人工复核清单（脚本抓不到的）
- 钩子 3 秒能念完吗？（实际念一遍）
- 逼单三件套齐吗？（锚点/倒计时/引导）
- 福利点每 15–20 分钟一轮吗？
- 价格/福利和运营 double check 了吗？

### 4. 交付审计报告
- 规则结果 + warning 豁免理由 + 人工复核结论，三者齐了才算交付完成。

## 硬规则
- blocker 没清零就交付 → 不许。
- 为清零改规则/删词库 → 作弊，不许。
- warning 无豁免理由直接忽略 → 不许。
