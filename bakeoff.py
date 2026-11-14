# ai-generated: 80% - Claude Code implemented CI-SPEC.md section 3 (P-14..P-22) on the course skeleton; I checked it against the practice set's expected.json
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23).

Standard library only - it runs as `python3 -S -E bakeoff.py`.

    python3 bakeoff.py --labels labels.json a.sarif b.sarif > bakeoff.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote

# P-19: the course's classes and the CWE numbers that give each of them
CLASS_CWES = {
    "secret": (259, 260, 321, 798),
    "injection": (74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336),
    "deserialization": (502,),
    "weak-crypto": (261, 326, 327, 328, 330, 331, 338, 759, 760, 916),
    "insecure-transport": (295, 297, 319, 322, 757),
    "path-traversal": (22, 23, 35, 36, 73),
    "ssrf": (918,),
    "vulnerable-dependency": (937, 1035, 1104, 1395),
    "misconfiguration": (16, 215, 250, 489, 668, 732, 1188),
    "access-control": (284, 285, 639, 862, 863),
}
CLASSES = frozenset(CLASS_CWES)
VULNERABLE_DEPENDENCY = "vulnerable-dependency"

# P-15: driver names with a fixed tool id (compared lower-cased, surrounding whitespace removed)
FIXED_TOOL_IDS = {
    "trivy": "trivy",
    "grype": "grype",
    "osv-scanner": "osv-scanner",
    "gitleaks": "gitleaks",
    "semgrep": "semgrep",
    "semgrep oss": "semgrep",
    "semgrep ce": "semgrep",
    "semgrep community edition": "semgrep",
    "semgrep pro": "semgrep",
}
TRIVY_TAG_CLASSES = {"vulnerability": VULNERABLE_DEPENDENCY, "secret": "secret", "misconfiguration": "misconfiguration"}

CWE_PATTERN = re.compile(r"(?<![A-Za-z0-9])[Cc][Ww][Ee]-([0-9]+)")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
PEP503_SEPARATORS = re.compile(r"[-_.]+")
NON_ALNUM = re.compile(r"[^a-z0-9]+")

NO_RULE = object()  # P-21: a result without a ruleId string differs from every string, "" included


def _get(obj, key):
    """A member of an object; null, absent or a non-object parent all give None."""
    if isinstance(obj, dict):
        return obj.get(key)
    return None


def _entries(value) -> list:
    """An array member's entries; a member that is not an array has none."""
    return value if isinstance(value, list) else []


def _is_int(value) -> bool:
    return type(value) is int


def tool_id(run: dict) -> str:
    """P-15: the tool id of a run, from tool.driver.name."""
    name = _get(_get(_get(run, "tool"), "driver"), "name")
    if not isinstance(name, str):
        return "unknown"
    key = name.strip().lower()
    if key in FIXED_TOOL_IDS:
        return FIXED_TOOL_IDS[key]
    normalised = NON_ALNUM.sub("-", key).strip("-")
    return normalised or "unknown"


def _is_empty_suppressions(value) -> bool:
    """P-16: absent, null, [], {}, false, 0 and "" keep a result; anything else drops it."""
    if value is None or value is False:
        return True
    if isinstance(value, (list, dict, str)):
        return len(value) == 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    return False


def result_path(uri: str) -> str:
    """P-17: decode %XX escapes, drop a file:// prefix (any case), then one leading ./"""
    path = unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    return path


def file_in_set(path: str, root: str) -> str | None:
    """P-17: the path from the last component equal to the set root, or None outside the set."""
    components = path.split("/")
    last = None
    for index, component in enumerate(components):
        if component == root:
            last = index
    if last is None:
        return None
    return "/".join(components[last:])


def result_lines(physical: dict) -> tuple[int, int] | None:
    """P-18: (start, end) from region.startLine and region.endLine, or None when the result has no lines."""
    region = _get(physical, "region")
    start = _get(region, "startLine")
    if not _is_int(start) or start < 1:
        return None
    end = _get(region, "endLine")
    if not _is_int(end) or end < start:
        end = start
    return start, end


def _string_tags(holder) -> list[str]:
    return [tag for tag in _entries(_get(_get(holder, "properties"), "tags")) if isinstance(tag, str)]


def _find_rule(run: dict, rule_id):
    """P-19: the first entry of the run's tool.driver.rules[] whose id equals the result's ruleId."""
    if rule_id is None:
        return None
    for rule in _entries(_get(_get(_get(run, "tool"), "driver"), "rules")):
        if isinstance(rule, dict) and rule.get("id") is not None and rule.get("id") == rule_id \
                and type(rule.get("id")) is type(rule_id):
            return rule
    return None


def result_classes(tool: str, result: dict, rule) -> set[str]:
    """P-19 (a) to (d): the classes of one result."""
    own = _get(_get(result, "properties"), "class")
    if isinstance(own, str) and own in CLASSES:
        return {own}
    if tool == "gitleaks":
        return {"secret"}
    if tool in ("grype", "osv-scanner"):
        return {VULNERABLE_DEPENDENCY}
    rule_tags = _string_tags(rule)
    if tool == "trivy":
        found = {TRIVY_TAG_CLASSES[tag.lower()] for tag in rule_tags if tag.lower() in TRIVY_TAG_CLASSES}
        if found:
            return found
    numbers = set()
    for tag in _string_tags(result) + rule_tags:
        for digits in CWE_PATTERN.findall(tag):
            numbers.add(int(digits))
    found = {name for name, cwes in CLASS_CWES.items() if numbers.intersection(cwes)}
    return found or {"other"}


def _pep503(name: str) -> str:
    return PEP503_SEPARATORS.sub("-", name.lower())


def message_tokens(result: dict) -> set[str]:
    """P-20: the PEP 503-normalised tokens of message.text (none without a text string)."""
    text = _get(_get(result, "message"), "text")
    if not isinstance(text, str):
        return set()
    tokens = set()
    for raw in TOKEN_PATTERN.findall(text):
        token = raw.strip("._-")
        if token:
            tokens.add(_pep503(token))
    return tokens


def collect(labels: dict, sarif_documents: list) -> dict[str, list[dict]]:
    """P-15..P-19: every tool id with a run, and its results in the set as plain records."""
    root = labels["set"]
    tools: dict[str, list[dict]] = {}
    for document in sarif_documents:
        for run in _entries(_get(document, "runs")):
            if not isinstance(run, dict):
                continue
            tool = tool_id(run)
            records = tools.setdefault(tool, [])
            for result in _entries(run.get("results")):
                if not isinstance(result, dict):
                    continue
                kind = result.get("kind")
                if kind is not None and kind != "fail":
                    continue
                if not _is_empty_suppressions(result.get("suppressions")):
                    continue
                locations = _entries(result.get("locations"))
                if not locations:
                    continue
                physical = _get(locations[0], "physicalLocation")
                uri = _get(_get(physical, "artifactLocation"), "uri")
                if not isinstance(uri, str) or not uri:
                    continue
                file = file_in_set(result_path(uri), root)
                if file is None:
                    continue
                rule_id = result.get("ruleId")
                rule = _find_rule(run, rule_id)
                records.append({
                    "rule": rule_id if isinstance(rule_id, str) else NO_RULE,
                    "file": file,
                    "lines": result_lines(physical),
                    "classes": result_classes(tool, result, rule),
                    "tokens": message_tokens(result),
                })
    return tools


def matches(record: dict, defect: dict) -> bool:
    """P-20: one result against one defect."""
    if record["file"] != defect.get("file") or defect.get("class") not in record["classes"]:
        return False
    if defect["class"] == VULNERABLE_DEPENDENCY:
        package = defect.get("package")
        return isinstance(package, str) and _pep503(package) in record["tokens"]
    if record["lines"] is None:
        return False
    start, end = record["lines"]
    return start <= defect["end_line"] and defect["start_line"] <= end


def _ratio(numerator: int, denominator: int):
    return None if denominator == 0 else round(numerator / denominator, 4)


def confusion_matrix(labels: dict, sarif_documents: list) -> dict:
    """The matrix of P-21 and P-22 for the labels (P-14) and the parsed SARIF documents."""
    defects = _entries(labels.get("defects"))
    tools = {}
    for tool, records in sorted(collect(labels, sarif_documents).items()):
        found = set()
        false_positives = set()
        for record in records:
            hit = False
            for index, defect in enumerate(defects):
                if matches(record, defect):
                    found.add(index)
                    hit = True
            if not hit:
                lines = record["lines"] or (None, None)
                false_positives.add((record["rule"], record["file"], lines[0], lines[1]))
        tp, fp = len(found), len(false_positives)
        fn = len(defects) - tp
        tools[tool] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": _ratio(tp, tp + fp),
            "recall": _ratio(tp, tp + fn),
            "f1": _ratio(2 * tp, 2 * tp + fp + fn),
        }
    return {"set": labels["set"], "defects": len(defects), "tools": tools}


def _load(path: str):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    labels = _load(args.labels)
    documents = [_load(path) for path in args.sarif]
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
