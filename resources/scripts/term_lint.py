#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
term_lint.py — 术语一致性与译文保真度核验器（chem-literal-translation Skill 执行内核）

解决的问题：科研翻译最容易失分的不是"读起来顺不顺"，而是
  同一术语前后两种译法、数字/单位被译错或漏掉、引用编号丢号、
  公式被改写、原文漏段。这些都能机械核对。

子命令：
  build   从原文与译文抽取候选术语对，生成 glossary 骨架（供人工/Agent 定名）
  check   用 glossary 核验译文 → term_report.json + term_report.md
  stats   快速给出原文/译文的段落、数字、单位、引用、公式计数对比

glossary.json 约定：
{
  "terms": [
    {"term": "LiFePO4", "zh": "磷酸铁锂", "variants": ["磷酸铁锂材料"],
     "decision_basis": "领域通用译名", "keep_original": false},
    {"term": "capacity retention", "zh": "容量保持率", "keep_original": false}
  ]
}
  keep_original=true 表示该术语按约定保留原文不译（缩写、基因名、软件名等）。

检出类别：
  untranslated      术语原文仍出现在译文中（且约定为"应译"）
  missing_term      术语的目标译法在译文中一次都没出现
  inconsistent      同一术语出现多种译法（术语表内 zh 与 variants 混用，客观可判）
  suspected_variant 疑似另有译法（自动提示，需人工确认后才改，不计入扣分）
  number_mismatch   原文与译文数字多重集不一致
  unit_mismatch     单位符号出现次数不一致（已识别中文单位写法的等价转换）
  citation_mismatch 引用标记（[n] / \\cite）序列不一致
  formula_mismatch  公式定界符数量不一致
  paragraph_gap     段落数差异过大（疑似漏段或合并段）
  negation_drift    否定表达数量差异（粗略提示，需人工确认）

计数口径（verification_hint 可直接引用）：
  term_consistency 以 untranslated / missing / inconsistent 三类为扣分项；
  suspected_variant 与 negation_drift 只提示、不扣分，避免自动误改。

用法：
  python3 term_lint.py build --source src.txt --target zh.md --out /app/work
  python3 term_lint.py check --source src.txt --target zh.md --glossary /app/work/glossary.json --out /app/work
  python3 term_lint.py stats --source src.txt --target zh.md
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?%?")

# 单位只认「数值 + 单位」的形式。纯字母单位（s / h / L / K）若不加数字前置约束，
# 会在 electrodes、results、cell 这类单词内部产生大量误报。
_UNITS = ["mA·cm⁻²", "mA·cm-2", "mA·cm", "wt%", "at%", "vol%", "mol%", "℃", "°C",
          "μg", "µg", "ng", "mL", "ml", "μL", "µL", "mM", "μM", "µM", "nM",
          "mol", "mmol", "mg", "kg", "km", "nm", "μm", "µm", "mm", "cm",
          "kV", "mV", "mA", "μA", "µA", "Hz", "kHz", "MHz", "GHz", "min", "ms",
          "h", "s", "K", "eV", "keV", "MeV", "GPa", "MPa", "kPa", "Pa",
          "rpm", "ppm", "ppb", "mAh", "Wh", "kWh", "L", "%"]
UNIT_ALT = "|".join(sorted(set(_UNITS), key=len, reverse=True))
UNIT = re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s*(" + UNIT_ALT + r")(?![\w])")

# 中文译文中以汉字表达的同一单位，视为「已等价转换」而非丢失
CN_UNIT = {
    "h": "小时", "min": "分钟", "s": "秒", "ms": "毫秒", "K": "开尔文", "℃": "摄氏度", "°C": "摄氏度",
    "mg": "毫克", "kg": "千克", "ng": "纳克", "μg": "微克", "µg": "微克",
    "L": "升", "mL": "毫升", "ml": "毫升", "μL": "微升", "µL": "微升",
    "nm": "纳米", "mm": "毫米", "cm": "厘米", "km": "千米", "μm": "微米", "µm": "微米",
    "mol": "摩尔", "mmol": "毫摩尔", "mM": "毫摩尔", "μM": "微摩尔", "µM": "微摩尔", "nM": "纳摩尔",
    "Pa": "帕", "kPa": "千帕", "MPa": "兆帕", "GPa": "吉帕",
    "eV": "电子伏", "kV": "千伏", "mV": "毫伏", "Hz": "赫兹", "kHz": "千赫", "MHz": "兆赫", "GHz": "吉赫",
    "mAh": "毫安时", "Wh": "瓦时", "kWh": "千瓦时", "rpm": "转每分",
}
CITE = re.compile(r"\[\d{1,3}(?:\s*[,\-–]\s*\d{1,3})*\]|\\cite[a-z]*\{[^}]+\}")
FORMULA = re.compile(r"\$\$?[^$]+\$\$?|\\\([^)]*\\\)|\\\[[^\]]*\\\]|\\begin\{(equation|align)\*?\}")
NEG_SRC = re.compile(r"\b(not|no|never|none|without|lack|absence|cannot|fail(?:ed|s)?)\b", re.I)
NEG_TGT = re.compile(r"(不|未|无|没有|并非|非|缺|未能|无法|不能|不曾)")


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def paragraphs(text):
    """按空行分块，忽略纯标题/纯空白块"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    return blocks


def count_nums(text):
    # 引用标记里的编号（[2,3]）不是被测数值，先剥掉，避免与 citation_mismatch 重复报
    return Counter(n.rstrip("%") for n in NUM.findall(CITE.sub(" ", text)))


def norm_unit(u):
    return u.replace("µ", "μ").replace("°C", "℃")


def count_units(text):
    return Counter(norm_unit(m.group(1)) for m in UNIT.finditer(text))


def norm(s):
    return re.sub(r"[\s\-_/]+", " ", str(s or "")).strip().lower()


def load_glossary(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    return data.get("terms") or data.get("glossary") or []


def cmd_stats(args):
    src, tgt = read(args.source), read(args.target)
    if not src or not tgt:
        print(json.dumps({"ok": False, "error": "原文或译文为空/路径不存在"}, ensure_ascii=False))
        return 1
    s_nums, t_nums = count_nums(src), count_nums(tgt)
    out = {
        "ok": True,
        "paragraphs": {"source": len(paragraphs(src)), "target": len(paragraphs(tgt))},
        "numbers": {"source_total": sum(s_nums.values()), "target_total": sum(t_nums.values()),
                    "only_in_source": dict((s_nums - t_nums)),
                    "only_in_target": dict((t_nums - s_nums))},
        "units": {"source_total": sum(count_units(src).values()),
                  "target_total": sum(count_units(tgt).values()),
                  "only_in_source": dict(count_units(src) - count_units(tgt))},
        "citations": {"source": len(CITE.findall(src)), "target": len(CITE.findall(tgt))},
        "formulas": {"source": len(FORMULA.findall(src)), "target": len(FORMULA.findall(tgt))},
        "negation": {"source": len(NEG_SRC.findall(src)), "target": len(NEG_TGT.findall(tgt))},
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_build(args):
    """从原文抽取候选术语（大写缩写、含数字化学式、高频名词短语），生成骨架"""
    src = read(args.source)
    if not src:
        print(json.dumps({"ok": False, "error": "原文为空"}, ensure_ascii=False))
        return 1
    cands = {}
    # 1) 全大写/混合缩写：LiFePO4, XRD, SEM, TEM, EIS
    for m in re.finditer(r"\b(?:[A-Z]{2,6}|[A-Z][a-z]?[A-Z][A-Za-z0-9]{1,10})\b", src):
        w = m.group(0)
        if len(w) >= 2 and not w.isdigit():
            cands[w] = cands.get(w, 0) + 1
    # 2) 领域高频名词短语（两词以上，含小写，出现 ≥3 次）
    words = re.findall(r"[a-z][a-z\-]{3,}(?:\s+[a-z][a-z\-]{3,}){1,2}", src.lower())
    for w in words:
        if len(w) >= 10:
            cands[w] = cands.get(w, 0) + 1
    items = sorted(cands.items(), key=lambda x: -x[1])
    terms = [{"term": t, "zh": "", "variants": [], "count": c,
              "decision_basis": "", "keep_original": bool(re.match(r"^[A-Z0-9]+$", t) and len(t) <= 6)}
             for t, c in items[:120]]
    out = {"terms": terms,
           "note": "zh 与 decision_basis 需人工/Agent 填写；keep_original=true 表示按约定保留原文（缩写、软件名）。"}
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "glossary_draft.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "candidates": len(terms), "out": str(Path(args.out) / "glossary_draft.json")}, ensure_ascii=False))
    return 0


FUNC_CHARS = set("的了为是和与及或在时后前内外上下等都就将被把对从到由于而且至达有无未已可会能"
                 "应需该其此这那各每些个种更最很较并却则即若如使让给向朝往按依着过之")
VERB_SUFFIX = ("提高", "降低", "增加", "减少", "上升", "下降", "增大", "减小", "达到", "出现",
               "存在", "显示", "表明", "说明", "认为", "提出", "采用", "使用", "进行", "具有",
               "属于", "包括", "以及", "因此", "从而", "进而", "并且", "但是", "然而", "因为",
               "如果", "虽然", "通过", "根据", "依据", "对于", "关于", "之一", "方面", "情况",
               "过程", "作用", "结果", "条件", "程度", "范围", "水平", "趋势", "变化")


def trim_func(s):
    """剥离结尾的虚词/动词短语，用于判断两个串是否「实质同一个术语」"""
    changed = True
    while changed and len(s) > 2:
        changed = False
        for v in VERB_SUFFIX:
            if s.endswith(v) and len(s) - len(v) >= 2:
                s, changed = s[:-len(v)], True
                break
        if changed:
            continue
        if s[-1] in FUNC_CHARS:
            s, changed = s[:-1], True
    return s


def scan_variants(tgt, zh, max_extra=6):
    """在译文中找与 zh 高度相似但实质不同的串（疑似自造变体）

    原文常见误报来源：把「容量保持率为」「扩散系数提高」当成变体。
    这里用 trim_func 剥掉结尾虚词/动词后再比，实质相同的一律不算变体。
    """
    if len(zh) < 3:
        return []
    base = trim_func(zh)
    found = []
    anchor = zh[:2]
    for m in re.finditer(re.escape(anchor) + r"[\u4e00-\u9fff]{0,4}", tgt):
        cand = m.group(0)
        if len(cand) < 3 or cand == zh or abs(len(cand) - len(zh)) > 2:
            continue
        if trim_func(cand) == base or trim_func(cand) == zh:
            continue  # 剥掉虚词后就是同一个术语，不是变体
        if cand not in found:
            found.append(cand)
        if len(found) >= max_extra:
            break
    return found


def cmd_check(args):
    src, tgt = read(args.source), read(args.target)
    if not src or not tgt:
        print(json.dumps({"ok": False, "error": "原文或译文为空/路径不存在"}, ensure_ascii=False))
        return 1
    terms = load_glossary(args.glossary) if args.glossary else []
    if not terms:
        print(json.dumps({"ok": False, "error": "未读取到术语表（glossary 的 terms 数组为空）"}, ensure_ascii=False))
        return 1

    untranslated, missing, inconsistent, kept_ok, suspected = [], [], [], [], []
    for t in terms:
        term = str(t.get("term") or "").strip()
        zh = str(t.get("zh") or "").strip()
        variants = [str(v).strip() for v in (t.get("variants") or []) if str(v).strip()]
        keep = bool(t.get("keep_original"))
        if not term:
            continue
        # 原文术语是否原样残留
        occurrences = len(re.findall(re.escape(term), tgt, flags=re.I))
        if keep:
            if occurrences > 0:
                kept_ok.append({"term": term, "occurrences": occurrences})
            continue
        if occurrences > 0:
            untranslated.append({"term": term, "zh": zh, "occurrences": occurrences,
                                 "action": "该术语约定应译，译文中仍保留原文写法（或仅在首次出现后应改为译名）"})
        if not zh:
            missing.append({"term": term, "reason": "术语表未给出目标译名",
                            "action": "补 zh 字段"})
            continue
        zh_count = tgt.count(zh)
        v_counts = {v: tgt.count(v) for v in variants}
        used = {zh: zh_count} if zh_count else {}
        for v, c in v_counts.items():
            if c:
                used[v] = c
        if not used:
            missing.append({"term": term, "zh": zh, "reason": "译文中未出现该译名",
                            "action": "确认是否漏译，或术语表译名与实际用法不符"})
            continue
        if len(used) > 1:
            inconsistent.append({"term": term, "zh": zh, "usages": used,
                                 "action": f"统一为「{zh}」，其余写法替换或加入 variants 并说明"})
        else:
            only = next(iter(used))
            # 自造变体只作「待人工确认」提示，不计入 term_ok 的扣分
            extra = [c for c in scan_variants(tgt, only) if c not in variants]
            if extra:
                suspected.append({"term": term, "zh": zh,
                                  "usages": {only: used[only], **{e: tgt.count(e) for e in extra}},
                                  "action": f"疑似另有译法（需人工确认是否应统一为「{zh}」）：{extra}"})

    s_nums, t_nums = count_nums(src), count_nums(tgt)
    num_only_src, num_only_tgt = s_nums - t_nums, t_nums - s_nums
    number_mismatch = [{"value": k, "source_count": s_nums.get(k, 0), "target_count": t_nums.get(k, 0),
                        "action": "核对原文该数值是否被漏译或译错"}
                       for k in list(num_only_src.keys())[:40]]

    s_units, t_units = count_units(src), count_units(tgt)
    unit_mismatch, unit_converted = [], []
    for k in list((s_units - t_units).keys())[:60]:
        deficit = s_units[k] - t_units.get(k, 0)
        cn = CN_UNIT.get(k)
        # 译文用汉字表达同一单位（6 h → 6 小时）属等价转换，不算缺失
        if cn and tgt.count(cn) >= deficit:
            unit_converted.append({"unit": k, "cn_form": cn, "count": deficit})
            continue
        unit_mismatch.append({"unit": k, "source_count": s_units.get(k, 0),
                              "target_count": t_units.get(k, 0),
                              "cn_form": cn,
                              "action": "单位应原样保留（或统一改为中文单位写法），核对是否被译错或丢失"})
    unit_mismatch = unit_mismatch[:30]

    s_cite = [c for c in CITE.findall(src)]
    t_cite = [c for c in CITE.findall(tgt)]
    citation_mismatch = []
    if len(s_cite) != len(t_cite):
        citation_mismatch.append({"source_count": len(s_cite), "target_count": len(t_cite),
                                  "action": "引用标记数量不一致：核对是否漏引或重复"})
    if Counter(s_cite) != Counter(t_cite):
        diff_src = Counter(s_cite) - Counter(t_cite)
        if diff_src:
            citation_mismatch.append({"missing_in_target": dict(list(diff_src.items())[:20]),
                                      "action": "这些引用标记在译文中缺失或被改写"})

    s_f, t_f = len(FORMULA.findall(src)), len(FORMULA.findall(tgt))
    formula_mismatch = []
    if s_f != t_f:
        formula_mismatch.append({"source_count": s_f, "target_count": t_f,
                                 "action": "公式定界符数量不一致：公式应原样保留，不翻译不改写"})

    s_p, t_p = len(paragraphs(src)), len(paragraphs(tgt))
    paragraph_gap = []
    if s_p and abs(s_p - t_p) > max(2, s_p * 0.3):
        paragraph_gap.append({"source": s_p, "target": t_p,
                              "action": "段落数差异过大：核对是否漏译或把多段合并"})

    s_n, t_n = len(NEG_SRC.findall(src)), len(NEG_TGT.findall(tgt))
    negation_drift = []
    if s_n and t_n and abs(s_n - t_n) > max(3, s_n * 0.5):
        negation_drift.append({"source": s_n, "target": t_n,
                               "action": "否定表达数量差异较大（粗略提示）：核对是否有否定被译丢或误加"})

    total_terms = len([t for t in terms if str(t.get("term") or "").strip()])
    bad_terms = len({x["term"] for x in untranslated} | {x["term"] for x in missing} |
                    {x["term"] for x in inconsistent})
    report = {
        "ok": True, "source": str(args.source), "target": str(args.target),
        "term_total": total_terms, "term_ok": max(0, total_terms - bad_terms),
        "untranslated_count": len(untranslated), "missing_term_count": len(missing),
        "inconsistent_count": len(inconsistent), "kept_as_is": len(kept_ok),
        "suspected_variant_count": len(suspected),
        "number_mismatch_count": len(number_mismatch), "unit_mismatch_count": len(unit_mismatch),
        "unit_converted_count": len(unit_converted),
        "citation_mismatch_count": len(citation_mismatch), "formula_mismatch_count": len(formula_mismatch),
        "paragraph_gap_count": len(paragraph_gap), "negation_drift_count": len(negation_drift),
        "untranslated": untranslated[:40], "missing_terms": missing[:40],
        "inconsistent": inconsistent[:40], "suspected_variants": suspected[:40],
        "number_mismatch": number_mismatch, "unit_mismatch": unit_mismatch,
        "unit_converted": unit_converted[:30],
        "citation_mismatch": citation_mismatch, "formula_mismatch": formula_mismatch,
        "paragraph_gap": paragraph_gap, "negation_drift": negation_drift,
        "verification_hint": {
            "term_consistency": f"术语一致 {max(0, total_terms - bad_terms)} / {total_terms}"
                                f"（不一致 {len(inconsistent)}；未译 {len(untranslated)}；漏译 {len(missing)}）",
            "numeric_fidelity": f"数字异值 {len(number_mismatch)} 项；单位差异 {len(unit_mismatch)} 项"
                                f"（已等价转中文单位 {len(unit_converted)} 项）",
            "citation_formula_preserved": f"引用差异 {len(citation_mismatch)} 项；公式差异 {len(formula_mismatch)} 项",
            "structure_parity": f"段落 原文 {len(paragraphs(src))} / 译文 {len(paragraphs(tgt))}；差异告警 {len(paragraph_gap)}",
            "needs_human_review": f"疑似另译 {len(suspected)} 条；否定表达差异告警 {len(negation_drift)} 条——这两类只作提示，需人工确认后再改",
        },
    }
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "term_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# 术语一致性与译文保真报告", "",
          f"- 术语 {total_terms} 条｜一致 {report['term_ok']}｜不一致 {len(inconsistent)}｜未译 {len(untranslated)}｜漏译 {len(missing)}",
          f"- 数字异值 {len(number_mismatch)}｜单位差异 {len(unit_mismatch)}（等价转中文单位 {len(unit_converted)}）"
          f"｜引用差异 {len(citation_mismatch)}｜公式差异 {len(formula_mismatch)}",
          f"- 段落 原文 {len(paragraphs(src))} / 译文 {len(paragraphs(tgt))}",
          f"- 待人工确认：疑似另译 {len(suspected)} 条｜否定表达告警 {len(negation_drift)} 条", ""]
    for label, items in [("术语未译（保留原文）", untranslated),
                         ("术语漏译（译名未出现）", missing),
                         ("译法不一致（术语表内混用）", inconsistent),
                         ("疑似另有译法（需人工确认）", suspected),
                         ("数字不一致", number_mismatch),
                         ("单位差异", unit_mismatch),
                         ("单位等价转换（无需修改）", unit_converted),
                         ("引用标记差异", citation_mismatch),
                         ("公式差异", formula_mismatch),
                         ("段落数差异", paragraph_gap),
                         ("否定表达差异（需人工核）", negation_drift)]:
        if items:
            md += [f"## {label}（{len(items)}）", ""]
            for it in items[:20]:
                md.append(f"- {json.dumps(it, ensure_ascii=False)[:240]}")
            md.append("")
    md += ["## 自检口径建议", ""] + [f"- `{k}`：{v}" for k, v in report["verification_hint"].items()]
    (outdir / "term_report.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["term_total", "term_ok", "untranslated_count",
                                            "missing_term_count", "inconsistent_count",
                                            "suspected_variant_count",
                                            "number_mismatch_count", "unit_mismatch_count",
                                            "unit_converted_count",
                                            "citation_mismatch_count", "formula_mismatch_count"]},
                     ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser(description="术语一致性与译文保真度核验器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--source", required=True)
    b.add_argument("--target"); b.add_argument("--out", required=True)
    c = sub.add_parser("check"); c.add_argument("--source", required=True)
    c.add_argument("--target", required=True); c.add_argument("--glossary")
    c.add_argument("--out", required=True)
    s = sub.add_parser("stats"); s.add_argument("--source", required=True); s.add_argument("--target", required=True)
    a = ap.parse_args()
    return {"build": cmd_build, "check": cmd_check, "stats": cmd_stats}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
