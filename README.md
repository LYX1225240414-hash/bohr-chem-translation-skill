# 化学文献术语一致性翻译 Skill

玻尔科学空间高校挑战赛 · 北京化工大学分站赛 —— 阅读03｜文献翻译 赛题作品。

## 简介

面向化学 / 材料 / 催化方向英文科研论文的英译中 Skill。聚焦"术语表驱动的术语一致性翻译"，解决四个高频失败：同一术语前后译名不一致、长文漏段或错位、数字单位公式引用被译掉、译不准处被含混带过。

两条核心设计：

1. **术语表是执行依据，不是提示词装饰**——每次逐段翻译前重读术语表，译后用脚本逐词比对，不靠印象。
2. **保真靠机械核验，不靠通顺**——数字、单位、引用编号、公式定界符、段落数全部可计数，由 `term_lint.py` 给计数；脚本测不出的（指代、限定强度、因果让步）才人工判断。

## 目录结构

```
SKILL.md                            Skill 定义（YAML frontmatter + 7 步工作流 + 运行环境契约）
environment/resources.yaml          资源清单、依赖、运行时与产物说明
resources/scripts/term_lint.py      执行内核：build / check / stats（纯标准库，可离线）
resources/field_dict.md             字段字典、锚点格式、para_id 与 block_type 规则
resources/gain_protocol.md          使用增益对照协议与 gain_record 记录格式
resources/checklist.md              带计数口径的译后自检清单（对应 verification 九项）
resources/glossary_template.json    术语表模板
resources/output_example.json       输出结构示意（非答案）
examples/README.md                  最小调用示例（含真实实测输出，非虚构）
```

## 执行内核 `term_lint.py`

三个子命令，纯标准库、无第三方依赖、可完全离线：

| 子命令 | 作用 |
|---|---|
| `build` | 从原文抽候选术语（大写缩写、化学式、高频名词短语）→ `glossary_draft.json`，按频次降序最多 120 条 |
| `check` | 译稿 vs 术语表 vs 原文逐条比对 → `term_report.json` + `term_report.md` |
| `stats` | 段落/数字/单位/引用/公式计数摸底，用于判断是否需要分段多轮 |

`check` 检出十类问题：`untranslated`（应译却保留原文）、`missing_terms`（译名未出现）、`inconsistent`（术语表内混用）、`suspected_variants`（疑似另译，仅提示不扣分）、`number_mismatch`、`unit_mismatch`、`citation_mismatch`、`formula_mismatch`、`paragraph_gap`、`negation_drift`。

工程上有四处刻意设计，避免"脚本误报带着人瞎改"：

- 单位只认「数值 + 单位」配对，不做裸字符串匹配——否则 `electrodes` 里的 `s`、`result` 里的 `l` 会被当成单位。
- 内置中英单位等价表，`6 h → 6 小时`、`200 nm → 200 纳米` 判为等价转换（`unit_converted`），不报"单位丢失"。
- 数数字前先剥掉引用标记，避免 `[2,3]` 里的 2、3 被当成被测数值重复报（引用差异由 `citation_mismatch` 单独报）。
- 疑似自造变体先剥结尾虚词/动词再比（`容量保持率为`、`扩散系数提高` 不算变体），且只进"待人工确认"，不计入扣分。

## 使用方式

在支持 Skill 的 Agent 环境中加载本目录，把文献（PDF / TXT / MD）或任务说明作为输入。Agent 按 SKILL.md 的工作流执行：

落盘骨架 → 确认输入边界 → `build` 建术语表并逐条定名 → 按语义边界分段 → 逐段翻译（同时产出 `result.json` 与纯文本译稿）→ `check` 机械核验并回修 → 增益记录 → 输出与复核。

## 输出约定

`/app/output/result.json` 原样回填 `case_id`、完整包含 `output_contract` 全部字段，并提供 `translation`（段落级双语对照 + `anchors`）、`glossary`、`verification`（九项带计数）、`translation_report`（转述 `term_report.json`）、`gain_record`、`uncertainties`、`sources`、`change_log`。同时落盘可编辑译稿 `translation_zh.md`、术语表 `glossary.json` 与核验报告 `term_report.md`。

## 版本

- v1.1.0：接入 `term_lint.py` 执行内核；新增 `environment/resources.yaml`、`field_dict.md`、`gain_protocol.md`；`check` 增补单位等价识别、引用编号剔除、变体去噪。
- v1.0.0：术语表驱动 + 段落对齐 + 自检清单的纯文档版工作流。

## 授权

仅供赛事评审与学习交流使用。
