# 使用增益对照协议（质量增益 / 效率增益 / 增益可验证性）

本题"使用增益"占 25 分，其中"增益可验证性 5 分"要求**用证据说明改善**，不能只写"译得更准"。本协议给出可在单次运行内完成的对照记录方法。

## 1. 对照条件（必须一致）

| 项目 | 要求 |
|---|---|
| 原文 | 同一份输入文献（同一 PDF / 同一段文本），不改内容 |
| 术语口径 | 同一份 `glossary.json`，译文对照时不得换术语表 |
| 任务要求 | 同一份 task.md 与输出字段要求 |
| 预算 | 同一模型、同一次运行预算（64 请求 / 900 秒） |
| 度量 | 同一组指标与同一判定口径（见第 3 节） |

不满足以上任一项，增益结论无效，应写 `uncertainties` 说明对照不成立。

## 2. 两种记录方式（按可得性择一）

### 方式 A：同原文两次产出的可对比指标（首选）
若平台提供基础 Agent 的产出，或可复跑一次不加载 Skill 的条件，分别对两份译稿跑 `term_lint.py check`，按第 3 节指标填表，写入 `gain_record.conditions`。

### 方式 B：单次运行内的两版译稿对照（无基础产出时）
在没有对照产出时，用同一运行内的两版译稿作可复核证据：

1. 先按"不查术语表、直接读原文翻译"的方式产出 `/app/work/draft_blind.md`；
2. 再按本 Skill 工作流产出 `/app/output/translation_zh.md`；
3. 两版**用同一份 glossary.json** 分别跑 `check`，比较下列计数的变化。

这种对照不是"跑两次模型"，而是**同一运行内的两版译稿**，成本低、可复核，且直接对应"是否减少了查术语、逐段校对与返工的时间"的效率增益。

## 3. 指标与口径（只报能算出来的）

| 指标 | 定义 | 采集方式 |
|---|---|---|
| 术语一致率 | `term_ok / term_total` | `term_report.json` |
| 原文残留未译数 | 约定应译却仍保留原文写法的术语数 | `term_report.json.untranslated_count`，越低越好 |
| 译名缺失数 | 术语表译名在译文中一次未出现的条数 | `term_report.json.missing_term_count`，应为 0 |
| 术语表内混用数 | `zh` 与 `variants` 混用的术语数 | `term_report.json.inconsistent_count`，应为 0 |
| 数值异值数 | 原文与译文数字多重集差异条数 | `term_report.json.number_mismatch_count`，应为 0 |
| 单位差异数 | 单位出现次数差异（已扣除中文等价写法） | `term_report.json.unit_mismatch_count` |
| 引用标记差异数 | `[n]` / `\cite` 数量或内容不一致数 | `term_report.json.citation_mismatch_count`，应为 0 |
| 段落完整率 | 译文段数 / 原文段数 | `term_report.json` 的段落计数 |
| 返工轮次 | 从初稿到定稿的修正轮数 | `change_log` 条目数 |
| 耗时 | 从读原文到产出定稿的 wall time | 运行日志时间戳 |

## 4. 记录格式（写入 result.json）

```json
"gain_record": {
  "conditions": {"same_source": true, "same_glossary": true, "same_budget": true, "same_task": true},
  "mode": "B_single_run_two_drafts",
  "baseline": {"draft": "/app/work/draft_blind.md", "term_ok": 0, "term_total": 0,
               "untranslated_count": 0, "missing_term_count": 0, "inconsistent_count": 0,
               "number_mismatch_count": 0, "unit_mismatch_count": 0, "citation_mismatch_count": 0},
  "with_skill": {"draft": "/app/output/translation_zh.md", "term_ok": 0, "term_total": 0,
                 "untranslated_count": 0, "missing_term_count": 0, "inconsistent_count": 0,
                 "number_mismatch_count": 0, "unit_mismatch_count": 0, "citation_mismatch_count": 0},
  "delta_note": "术语一致率由 a/b 升至 c/d；未译由 N 降至 M；数值异值由 N 降至 0；段落完整率 x/y → y/y",
  "verifiable_artifacts": ["/app/output/term_report.json", "/app/output/term_report.md", "/app/output/change_log.jsonl"]
}
```

## 5. 诚实性红线

- 不得编造对照数据、耗时或返工轮次；无法测量就写 `na` 并说明原因。
- 不得把平台提供的白板或官方结果写成自己的对照产出。
- 增益结论必须能由 `verifiable_artifacts` 里的文件复算出来；只写结论不附产物，视为不可验证。
- 不得为了让指标好看而缩小术语表：术语表的规模应在第 2 步按原文实际抽取确定，对照时保持不变。
