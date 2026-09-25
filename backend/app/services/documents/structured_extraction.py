"""Deterministic extraction of BIS-style technical structures.

The extractor is deliberately evidence-first: it only emits structures that can
be identified from the source text using conservative patterns. It never asks an
LLM to invent missing clauses, tables, formulas, or requirement classifications.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import re
from typing import Any


CLAUSE_RE = re.compile(r"^(?P<number>\d+(?:\.\d+)*(?:\([a-z0-9]+\))?)\s*[.)-]?\s+(?P<title>.+?)\s*$", re.I)
ANNEX_RE = re.compile(r"^(?:ANNEX|Annex)\s+([A-Z0-9]+)\s*(?:[-–—:]\s*(.*))?$", re.I)
TABLE_TITLE_RE = re.compile(r"^(?:Table|TABLE)\s+([A-Z0-9.\-]+)\s*(?:[-–—:.]\s*)?(.*)$", re.I)
FORMULA_LINE_RE = re.compile(r"^(?:formula|equation|where)\s*[:.]?\s*(.+)$", re.I)


@dataclass(frozen=True)
class ClauseRecord:
    clause_number: str
    title: str | None
    parent_clause: str | None
    page_number: int
    section: str | None
    text_content: str


@dataclass(frozen=True)
class DefinitionRecord:
    term: str
    definition: str
    clause_number: str | None
    page_number: int


@dataclass(frozen=True)
class TableRecord:
    title: str | None
    table_number: str | None
    headers: list[str]
    rows: list[list[str]]
    footnotes: list[str]
    units: list[str]
    clause_number: str | None
    page_number: int
    raw_text: str


@dataclass(frozen=True)
class FormulaRecord:
    expression_plain: str
    expression_latex: str
    variables: list[dict[str, str]]
    units: list[str]
    clause_number: str | None
    page_number: int
    source_text: str


@dataclass(frozen=True)
class RequirementRecord:
    statement: str
    classification: str
    clause_number: str | None
    page_number: int
    evidence: str
    requirement_kind: str | None = None


def _clean(value: str) -> str:
    value = value.replace("\x00", " ")
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def _normalize_latex(raw: str) -> str:
    s = raw.strip().strip("$ ")
    s = s.replace("\\times", " \\times ").replace("\\cdot", " \\cdot ")
    s = re.sub(r"\\text\s*\{([^{}]*)\}", r"\\mathrm{\1}", s)
    s = re.sub(r"\\left|\\right", "", s)
    return s.strip()


def _latex_to_plain(latex: str) -> str:
    """Readable fallback for environments that cannot render LaTeX."""
    s = _normalize_latex(latex)
    s = s.replace("\\\\", "\\")
    # Fractions: recursively convert simple \frac{a}{b}.
    for _ in range(4):
        s2 = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1 / \2)", s)
        if s2 == s:
            break
        s = s2
    replacements = {
        r"\times": " × ", r"\cdot": " · ", r"\pm": " ± ",
        r"\leq": " ≤ ", r"\geq": " ≥ ", r"\neq": " ≠ ",
        r"\approx": " ≈ ", r"\sqrt": "√", r"\pi": "π",
        r"\rho": "ρ", r"\sigma": "σ", r"\Delta": "Δ",
        r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
        r"\mu": "μ", r"\lambda": "λ", r"\theta": "θ",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    s = re.sub(r"[{}]", "", s)
    s = s.replace("\\,", " ")
    s = re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", s)
    s = re.sub(r"\\text\{([^{}]+)\}", r"\1", s)
    s = re.sub(r"_\{([^{}]+)\}", lambda m: "₍" + m.group(1) + "₎", s)
    s = re.sub(r"\^\{([^{}]+)\}", lambda m: "⁽" + m.group(1) + "⁾", s)
    s = re.sub(r"_([A-Za-z0-9]+)", lambda m: "₍" + m.group(1) + "₎", s)
    s = re.sub(r"\^([A-Za-z0-9]+)", lambda m: "⁽" + m.group(1) + "⁾", s)
    s = re.sub(r"\\([A-Za-z]+)", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_formula(raw: str, *, units: list[str] | None = None) -> dict[str, Any]:
    """Return safe dual representations; raw parser artifacts are not exposed."""
    text = _clean(raw)
    # Strip common markdown math fences only; never invent an expression.
    latex = _normalize_latex(text)
    if not latex:
        return {"plain_text": "", "latex": "", "variables": [], "units": units or []}
    plain = _latex_to_plain(latex)
    variables: list[dict[str, str]] = []
    # Capture common "where x = description" definitions adjacent to formula.
    for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9]*)\s*=\s*([^,;]+)", plain):
        name, definition = m.group(1), _clean(m.group(2))
        if len(definition) <= 120 and name.lower() not in {"http", "https"}:
            variables.append({"symbol": name, "definition": definition})
    detected_units = list(units or [])
    for u in re.findall(r"\b(?:kN|N|Pa|kPa|MPa|GPa|mm|cm|m|kg|kg/m3|N/mm2|kN/m2|%)\b", plain):
        if u not in detected_units:
            detected_units.append(u)
    return {"plain_text": plain, "latex": latex, "variables": variables, "units": detected_units}


def _looks_like_formula(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 500:
        return False
    if FORMULA_LINE_RE.match(s):
        return True
    if "\\frac" in s or "\\times" in s or "\\cdot" in s:
        return True
    # Equation-like line: variable/operator = expression, but avoid ordinary prose.
    return bool(re.match(r"^[A-Za-zα-ωΑ-Ω][A-Za-z0-9_{}()]*\s*(?:=|≤|≥)\s*[-+*/().A-Za-z0-9α-ωΑ-Ω{}_\\ ]+[A-Za-z0-9)]$", s))


def _extract_units(text: str) -> list[str]:
    seen = []
    for unit in re.findall(r"\b(?:kN|N|Pa|kPa|MPa|GPa|mm|cm|m|kg|kg/m3|N/mm2|kN/m2|%)\b", text):
        if unit not in seen:
            seen.append(unit)
    return seen


def extract_structures(pages) -> dict[str, list[dict[str, Any]]]:
    clauses: list[dict[str, Any]] = []
    definitions: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    formulas: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    context_items: list[dict[str, Any]] = []

    current_clause: str | None = None
    for page in pages:
        raw_lines = page.text.splitlines()
        lines = [_clean(x) for x in raw_lines]
        lines = [x for x in lines if x]
        i = 0
        while i < len(lines):
            line = lines[i]
            ann = ANNEX_RE.match(line)
            if ann:
                context_items.append({"section_number": ann.group(1), "title": ann.group(2), "section_type": "ANNEXURE", "text_content": line, "page_number": page.page_number, "clause_number": current_clause})
            low_line = line.lower()
            if low_line.startswith(("note:", "note ", "notes:", "example:", "example ", "examples:", "references", "reference")):
                kind = "NOTE" if low_line.startswith(("note:", "note ", "notes:")) else "EXAMPLE" if low_line.startswith(("example:", "example ", "examples:")) else "REFERENCE"
                context_items.append({"section_number": None, "title": line.split(":", 1)[0], "section_type": kind, "text_content": line, "page_number": page.page_number, "clause_number": current_clause})
            cm = CLAUSE_RE.match(line)
            if cm:
                number = cm.group("number").rstrip(".")
                title = cm.group("title")
                # Page headers such as "1 Scope" are useful; contents rows are filtered later.
                current_clause = number
                parent = ".".join(number.split(".")[:-1]) or None
                clauses.append(asdict(ClauseRecord(number, title, parent, page.page_number, page.section, line)))

            definition_line = re.sub(r"^\d+(?:\.\d+)*[.)-]?\s+", "", line)
            dm = re.match(r"^([A-Za-z][A-Za-z0-9 /()\-]{1,80})\s+(?:means|is defined as|shall mean)\s+(.+)$", definition_line, re.I)
            if dm and not line.lower().startswith(("note", "example")):
                definitions.append(asdict(DefinitionRecord(_clean(dm.group(1)), _clean(dm.group(2)), current_clause, page.page_number)))

            tm = TABLE_TITLE_RE.match(line)
            if tm:
                table_number = tm.group(1)
                title = tm.group(2).strip() or None
                block = []
                j = i + 1
                while j < len(lines) and j < i + 40:
                    nxt = lines[j]
                    if CLAUSE_RE.match(nxt) or ANNEX_RE.match(nxt) or TABLE_TITLE_RE.match(nxt):
                        break
                    if nxt.lower().startswith(("note", "source", "notes", "*")):
                        break
                    raw_idx = j if j < len(raw_lines) else j
                    block.append(raw_lines[raw_idx].strip() if raw_idx < len(raw_lines) else nxt)
                    j += 1
                if block:
                    headers, rows = _parse_table_rows(block)
                    footnotes = [x for x in block if x.lower().startswith(("note", "notes", "*"))]
                    tables.append(asdict(TableRecord(title, table_number, headers, rows, footnotes, _extract_units(" ".join(block)), current_clause, page.page_number, "\n".join(_clean(x) for x in block))))

            if _looks_like_formula(line):
                candidate = FORMULA_LINE_RE.sub(r"\1", line, count=1).strip()
                formula = normalize_formula(candidate, units=_extract_units(line))
                if formula["latex"] and ("=" in formula["plain_text"] or "≤" in formula["plain_text"] or "≥" in formula["plain_text"]):
                    formulas.append(asdict(FormulaRecord(formula["plain_text"], formula["latex"], formula["variables"], formula["units"], current_clause, page.page_number, line)))

            classification, kind = classify_requirement(line)
            if classification:
                requirements.append(asdict(RequirementRecord(line, classification, current_clause, page.page_number, line, kind)))
            i += 1

    # Deduplicate identical structures produced by page headers/repeated table text.
    return {
        "context_items": _dedupe(context_items, ("section_type", "text_content", "page_number")),
        "clauses": _dedupe(clauses, ("clause_number", "page_number", "text_content")),
        "definitions": _dedupe(definitions, ("term", "definition", "page_number")),
        "tables": _dedupe(tables, ("table_number", "page_number", "raw_text")),
        "formulas": _dedupe(formulas, ("expression_latex", "page_number")),
        "requirements": _dedupe(requirements, ("statement", "page_number")),
    }


def _parse_table_rows(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    # Prefer explicit pipe/tab structure. Otherwise accept repeated 2+ spaces as columns.
    split_rows = []
    for line in lines:
        if "|" in line:
            cells = [_clean(c) for c in line.strip("|").split("|")]
        elif "\t" in line:
            cells = [_clean(c) for c in line.split("\t")]
        else:
            cells = [_clean(c) for c in re.split(r"\s{2,}", line) if _clean(c)]
        if len(cells) >= 2:
            split_rows.append(cells)
    if not split_rows:
        return [], []
    # Only call the first row a header when it has the same/compatible width as data.
    width = max(len(r) for r in split_rows)
    normalized = [r + [""] * (width - len(r)) for r in split_rows]
    return normalized[0], normalized[1:]


def classify_requirement(statement: str) -> tuple[str | None, str | None]:
    s = statement.strip()
    low = s.lower()
    if re.search(r"\b(shall not|must not|not permitted|prohibited|limitation|limit)\b", low):
        return "LIMITATION", None
    if re.search(r"\b(test|testing|test method|test specimen|test procedure|tested)\b", low) and re.search(r"\b(shall|must|required|should|is carried out|be tested)\b", low):
        return "TESTING", None
    if re.search(r"\b(shall|must|is required to|required to|mandatory)\b", low):
        kind = "acceptance_criterion" if "acceptance" in low or "acceptable" in low else None
        return "MANDATORY", kind
    if re.search(r"\b(should|recommended|it is recommended|preferably)\b", low):
        return "RECOMMENDED", None
    if re.search(r"\b(note|informative|for information|example|may)\b", low):
        return "INFORMATIONAL", None
    if re.search(r"\b(shall not|must not|not permitted|prohibited|limitation|limit)\b", low):
        return "LIMITATION", None
    return None, None


def _dedupe(items: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    out, seen = [], set()
    for item in items:
        key = tuple(json.dumps(item.get(k), sort_keys=True, ensure_ascii=False) for k in keys)
        if key not in seen:
            seen.add(key); out.append(item)
    return out
