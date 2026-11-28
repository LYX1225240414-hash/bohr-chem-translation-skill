# 字段字典、锚点格式与术语表规范

## 1. 锚点格式（`anchors` / `positions` / `uncertainties.anchor`）

| 形式 | 用法 | 示例 |
|---|---|---|
| `p<页>:<段>` | PDF 有页码时首选，段号为该页内第几段（从 1 起） | `p3:2` |
| `para:<编号>` | 纯文本 / 无页码材料，用分段后的 `para_id` | `para:p007` |
| `sec:<章节名>` | 章节结构清楚的 Markdown | `sec:Results/3.2` |
| `fig<号>` | 图注、图内文字 | `fig2` |
| `tab<号>` | 表头、表内数值 | `tab1` |
| `eq<号>` | 公式及其编号 | `eq4` |
| `ref:[n]` | 参考文献条目与正文引用标记 | `ref:[12]` |
| `line:<起>-<止>` | 代码、日志、配置类补充材料 | `line:41-58` |

规则：锚点必须指向**输入材料里真实存在的位置**，不得用"摘要附近""大约第 2 页"这类模糊描述；一个段落可给多个锚点（正文 + 图注）。

## 2. `para_id` 与 `block_type`

- `para_id` 形如 `p001`、`p002`，三位补零，按原文出现顺序递增，**不复用、不跳号**。
- `block_type` 取值：`title`（标题）/ `body`（正文）/ `caption`（图注）/ `table_head`（表头）/ `footnote`（脚注）/ `reference`（参考文献条目）。
- 图注、表头、脚注必须**单独成段**，不并入正文段落——这是"结果完整性"里图表题注与表头覆盖的判定依据。
- 跨页、跨栏时按语义续接，同一自然段不因分页被拆成两个 `para_id`。

## 3. 术语表 `glossary.json` 规范

```json
{
  "terms": [
    {"term": "oxygen vacancy", "zh": "氧空位", "variants": ["氧空位缺陷"],
     "keep_original": false, "positions": ["p2:1", "fig3"], "decision_basis": "催化领域通行译法"},
    {"term": "XRD", "zh": "X 射线衍射（XRD）", "variants": [], "keep_original": true,
     "positions": ["p3:2"], "decision_basis": "缩写按惯例保留，首次出现给全称"}
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `term` | 是 | 原文术语，**必须与原文写法一致**（大小写、连字符会影响脚本匹配） |
| `zh` | 是 | 唯一锁定译名；脚本据此判断译名是否出现 |
| `variants` | 否 | 同一概念的**可接受异体**；若译文同时用了 `zh` 和 `variants`，脚本判 `inconsistent` 要求统一 |
| `keep_original` | 否 | `true` 表示按约定保留原文不译；脚本对它只核"是否保留"，不判未译 |
| `positions` | 否 | 出现位置锚点，用于"全篇回填"核查 |
| `decision_basis` | 是 | 定名依据；空值等于不能用，评审会视为"术语表未被真正执行" |

### 定名的三条硬规则

1. **一词一译**：同一 `term` 全篇只允许一个 `zh`。正文、图注、结论都不例外。
2. **缩写分两步**：首次出现写"中文全称（缩写）"，后文统一用缩写；术语表里 `zh` 记中文全称，`keep_original` 记 `true` 或另立一条缩写条目。
3. **不拿近义当异体**：`variants` 只收同一概念的另一种说法；把"容量保持率"和"循环稳定性"这类不同指标填成异体会污染术语表。

## 4. `verification` 各项的计数口径

| 键 | 口径 | 数据来源 |
|---|---|---|
| `term_consistency` | `term_ok / term_total`，附三处扣分来源计数 | `term_report.json` |
| `numeric_fidelity` | `number_mismatch_count` 必须为 0；不为 0 要逐条给理由 | `term_report.json` |
| `unit_fidelity` | `unit_mismatch_count`；同时说明 `unit_converted_count` 属等价写法 | `term_report.json` |
| `citation_formula_preserved` | `citation_mismatch_count` + `formula_mismatch_count` | `term_report.json` |
| `paragraph_completeness` | 译文段数 / 原文段数；`block_type` 各类是否覆盖 | `term_report.json` 段落计数 |
| `anchor_spotcheck` | 按锚点回查成功数 / 抽查数，附短引片段 | 人工抽查，建议 ≥5 处 |
| `no_new_facts` | 译文中新增了原文没有的数值/结论条数，应为 0 | `stats` 的 `only_in_target` |
| `relation_preservation` | 否定/限定/指代/因果抽查通过数 / 抽查数 | 人工核对，脚本测不出 |
| `uncertainty_disclosure` | 已标注入 `uncertainties` 的条数，对照材料实际残缺处数量 | 人工核对 |

## 5. `status` 判定

| 值 | 条件 |
|---|---|
| `success` | 全文段落译完，脚本五类硬指标（未译/缺译/混用/数值/引用）为 0 或有书面理由 |
| `partial` | 部分段落未译、或公式/表格为图片无法读取、或材料残缺；必须写出范围与人工接管位置 |
| `unable` | 整篇不可读（文字层缺失且 OCR 失败、文件损坏），未产出任何译文 |
| `refused` | 输入被判定不属于本 Skill 适用范围（非科研文本、要求编造数据） |
