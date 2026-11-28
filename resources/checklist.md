# 译后自检清单（带计数口径）

逐项核对。**能用脚本算的用脚本算，算不出的才人工填**；每项结论写进 `result.json` 的 `verification`，且必须带计数或抽查片段，不能只写"通过"。

| # | 项 | 口径 | 数据来源 |
|---|---|---|---|
| 1 | `term_consistency` | `term_ok / term_total`，附未译/缺译/混用三个计数 | `term_report.json` |
| 2 | `numeric_fidelity` | `number_mismatch_count`（引用编号已剔除，不重复报） | `term_report.json` |
| 3 | `unit_fidelity` | `unit_mismatch_count`；`unit_converted_count` 属"6 h → 6 小时"等价写法，不算差异 | `term_report.json` |
| 4 | `citation_formula_preserved` | `citation_mismatch_count` + `formula_mismatch_count` | `term_report.json` |
| 5 | `paragraph_completeness` | 译文段数 / 原文段数；`title/body/caption/table_head/footnote` 是否都有覆盖 | `term_report.json` 段落计数 |
| 6 | `anchor_spotcheck` | 按锚点回查成功数 / 抽查数（建议 ≥5 处，跨页处必抽） | 人工，附短引片段 |
| 7 | `no_new_facts` | 译文中出现、原文没有的数值/结论条数，应为 0 | `stats` 的 `only_in_target` |
| 8 | `relation_preservation` | 否定/限定/指代/因果让步抽查通过数 / 抽查数 | 人工（脚本测不出） |
| 9 | `uncertainty_disclosure` | 已标注条数 vs 材料实际残缺处数 | 人工对照 |

## 一、术语一致性（脚本 + 人工）

- [ ] `untranslated` 为 0，或每条残留都是 `keep_original: true` 且有 `decision_basis`
- [ ] `missing_terms` 为 0：术语表里每个 `zh` 都在译文中出现过
- [ ] `inconsistent` 为 0：没有 `zh` 与 `variants` 混用
- [ ] `suspected_variants` 已逐条人工判断，确认改或不改并留理由
- [ ] 标题、摘要、正文、图注、结论中同一术语译名一致（跨 `block_type` 抽查）
- [ ] 缩写首次出现给"中文全称（缩写）"，后文统一用缩写

## 二、段落完整性（脚本 + 人工）

- [ ] `para_id` 数量与原文自然段数量一致，无跳号、无复用
- [ ] 无漏段（重点看跨页、跨栏、章节衔接、参考文献前最后一页）
- [ ] 无重复翻译、无段落错位
- [ ] 图注、表头、脚注单独成段，未被并入正文
- [ ] 每段 `target` 与 `source` 一一对应

## 三、关系与事实（人工为主）

- [ ] 否定词（不、未、无、非、never、not、no、lack）逐处保留，未增未减
- [ ] 限定条件（仅、部分、显著、主要、may、can、significantly）强度未变
- [ ] 指代对象（this、these、it、其、该、上述）指向正确
- [ ] 因果、让步、对比关系未被改写或翻转
- [ ] 数字、有效数字、上下标、量纲原样保留
- [ ] 公式、图表编号、文献引用标记原样保留

## 四、可核验性（人工）

- [ ] 每段有 `anchors`，且锚点能在原文里定位到
- [ ] 关键结论能回到具体段落/页/图
- [ ] 译不准、无法判断、材料冲突处写入 `uncertainties` 并给 `handover`
- [ ] `status` 与实际完成情况一致；`partial` 写清了未完成范围
- [ ] `change_log` 记录了每一轮回修（问题、修正、位置）

## 五、交付合规（提交前）

- [ ] `result.json` 的 `case_id` 已从 `case.json` 回填
- [ ] `output_contract` 字段全部存在，未改名、未遗漏
- [ ] `translation_report` 的数值与 `term_report.json` 一致（不是另算一套）
- [ ] 包内无任何 `result.json`、无预制答案、无假造运行日志
