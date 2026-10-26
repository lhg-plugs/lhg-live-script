<!-- About 简介（推送后填写到仓库 About 栏）：
直播话术专家：开播钩子到逼单成交，直播话术一次写完 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-live-script
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, live-streaming, e-commerce, sales-script -->

# lhg-live-script：直播话术专家

> **一句话介绍**：品类输入→开播 3 秒留人钩子→留人/转粉/逼单五段式脚本→逼单倒计时话术→违禁词/极限词合规审计，一场 2 小时直播的话术一次写完、交付前自动拦截违禁词。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-live-script
> /plugin install lhg-live-script@lhg-plugs
> ```

## 它是什么

`lhg-live-script` 是一个 Claude Code 插件（plugin 为主、skill 为辅），专为"带货主播/商家"设计：

- **4 个命令**（小白入口）：`live-script` 完整开播脚本（品类→结构→话术→审计），`live-hook` 开播钩子单发（3 条让主播选），`live-close` 逼单话术单发（锚点+倒计时+引导），`live-audit` 话术自检
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：3 秒留人钩子公式、五段式话术结构与品类差异、逼单倒计时话术、合规与结构自查
- **3 个专家 agent**：钩子话术师、逼单手、独立合规审查员
- **1 个硬门 hook**：脚本交付前自动跑合规审计，命中违禁词直接拦截（可一键豁免，不骚扰）
- **17 条确定性自查规则**：极限词/虚假承诺/功效宣称/价格欺诈/迷信 5 类违禁词 + 结构完整性（逼单缺倒计时则 warning）+ 口语化，纯 Python、零第三方依赖，秒级出结果

工作流：`live-hook`（钩子先行）→ `live-script`（完整脚本）→ `live-audit`（交付前自检），也可以只用其中一段。

## 4 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-live-script:live-script` | 完整开播脚本：品类→五段式结构→逐段话术→逼单穿插→合规审计 | `/lhg-live-script:live-script 美妆 面霜/精华 --minutes 120` |
| `/lhg-live-script:live-hook` | 开播钩子单发：3 条 3 秒钩子→三问质检→主播拍板 | `/lhg-live-script:live-hook 食品 坚果礼盒` |
| `/lhg-live-script:live-close` | 逼单话术单发：锚点对比+倒计时三阶+下单引导+异议处理 | `/lhg-live-script:live-close 面霜 299 59.9` |
| `/lhg-live-script:live-audit` | 话术自检（脚本 + 人工评审清单） | `/lhg-live-script:live-audit ./delivery/ --strict` |

## 自查说明

自查 = 确定性脚本（机器）+ 人工评审清单（人）：

1. 先跑 `scripts/audit/live_audit.py`（17 条规则：违禁词 5 类、结构 7、口语化 3、节奏 2），零 LLM 成本；
2. 发现分三级：**blocker**（违禁词，必须改，交付前 hook 会拦截）、**warning**（结构缺件，修或写豁免理由）、**nit**（顺手修）；
3. 再按 `lhg-ls-compliance` skill 的人工清单过一遍脚本抓不到的（钩子 3 秒念一遍、福利频率、价格 double check）。

blocker 清零才算做完；为清零改规则算作弊，不许。

## 什么时候用 / 什么时候不用

**用它，当你**：
- 要开一场带货直播，没话术稿，或稿子"有人看没人买"
- 想系统学直播话术结构（留人→转粉→逼单），而不是东拼西凑
- 担心话术踩违禁词被限流/封号，想交付前自动检查一遍

**别用它，当你**：
- 做的是纯聊天/娱乐直播，不卖货——话术结构可参考，但逼单部分用不上
- 已经有成熟话术团队——直接用 `live-audit` 做合规自检即可，不必全流程
- 希望 AI 替你临场发挥、即兴救场——话术稿是"预案"，临场反应还得靠主播自己练

## 目录结构

```
lhg-live-script/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 4 个命令：live-script / live-hook / live-close / live-audit
├── skills/                  # 4 个平台中立 skill（钩子/结构/逼单/合规）
├── agents/                  # 3 个专家 agent（hook-writer / closer / compliance-reviewer）
├── hooks/                   # 1 个硬门（交付前合规审计）+ 豁免说明
├── scripts/audit/           # 17 条确定性自查规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-live-script](https://github.com/lhg-plugs/lhg-live-script) | 直播话术专家：开播钩子到逼单成交，话术一次写完 | `/plugin install lhg-live-script@lhg-plugs` |
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频（+口播脚本子命令） | `/plugin install lhg-video-edit@lhg-plugs` |

> 完整矩阵见组织模板仓 [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack#lhg-plugs-插件矩阵)。

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、17 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-live-script/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
