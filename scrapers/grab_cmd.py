#!/usr/bin/env python3
import json
import re
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_tablegen

RECORD_KINDS = ("def", "defm", "class", "multiclass")
INSTR_TERMS = (
    "instr",
    "instruction",
    "instalias",
    "opcode",
    "asmstring",
    "mnemonic",
    "pseudo",
    "pattern",
    "operand",
    "encoding",
    "format",
)
UARCH_TERMS = (
    "processor",
    "cpu",
    "subtarget",
    "feature",
    "sched",
    "schedule",
    "itinerary",
    "latency",
    "pipeline",
    "resource",
    "issue",
)
OS_TERMS = (
    "callingconv",
    "callconv",
    "ccassign",
    "callee",
    "caller",
    "csr",
    "regmask",
    "abi",
    "stack",
    "libcall",
)
MISSING = "__MISSING__"
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_#]*")
_QUOTE_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
_WS_RE = re.compile(r"\s+")


def _node_text(node):
    return node.text.decode("utf-8", errors="replace")


def _normalize(text):
    return _WS_RE.sub(" ", text).strip()


def _walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _split_top_level(text, sep):
    parts = []
    current = []
    depth = 0
    quote = False
    escaped = False
    openers = {"<", "(", "[", "{"}
    closers = {">", ")", "]", "}"}
    for ch in text:
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == "\\":
            current.append(ch)
            escaped = True
            continue
        if ch == '"':
            current.append(ch)
            quote = not quote
            continue
        if not quote:
            if ch in openers:
                depth += 1
            elif ch in closers and depth > 0:
                depth -= 1
            elif ch == sep and depth == 0:
                parts.append("".join(current))
                current = []
                continue
        current.append(ch)
    parts.append("".join(current))
    return parts


def _extract_name(node):
    named = node.child_by_field_name("name")
    if named is not None:
        value = _normalize(_node_text(named))
        return value or None
    for child in node.children:
        if child.is_named and child.type in ("identifier", "value"):
            value = _normalize(_node_text(child))
            if value:
                return value
    return None


def _extract_parent_info(node):
    parent_node = None
    for child in node.children:
        if child.is_named and child.type == "parent_class_list":
            parent_node = child
            break
    if parent_node is None:
        return "", [], []
    raw = _normalize(_node_text(parent_node))
    text = raw[1:].strip() if raw.startswith(":") else raw
    items = [item.strip() for item in _split_top_level(text, ",") if item.strip()]
    bases = []
    for item in items:
        match = _IDENT_RE.search(item)
        bases.append(match.group(0) if match else item)
    return raw, items, bases


def _extract_fields(node):
    body = node.child_by_field_name("body")
    if body is None:
        return {}, ""
    body_text = _node_text(body).strip()
    inner = body_text
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1]
    fields = {}
    for stmt in _split_top_level(inner, ";"):
        piece = stmt.strip()
        if not piece or "=" not in piece:
            continue
        left, right = piece.split("=", 1)
        ids = _IDENT_RE.findall(left)
        if not ids:
            continue
        fields.setdefault(ids[-1], _normalize(right))
    return dict(sorted(fields.items())), _normalize(body_text)


def _record_blob(record):
    values = [
        record["name"] or "",
        record["file"],
        record["parent_raw"],
        " ".join(record["parents"]),
        " ".join(record["fields"].keys()),
    ]
    return " ".join(values).lower()


def _has_term(blob, terms):
    return any(term in blob for term in terms)


def _record_from_node(node, rel_path):
    parent_raw, parent_items, parents = _extract_parent_info(node)
    fields, body_raw = _extract_fields(node)
    text = _normalize(_node_text(node))
    return {
        "kind": node.type,
        "name": _extract_name(node),
        "file": rel_path,
        "line": node.start_point[0] + 1,
        "parents": parents,
        "parent_items": parent_items,
        "parent_raw": parent_raw,
        "fields": fields,
        "body_raw": body_raw,
        "signature": text[:280],
    }


def _instruction_candidate(record):
    if record["kind"] not in ("def", "defm"):
        return False
    blob = _record_blob(record)
    stem = Path(record["file"]).stem.lower()
    return ("instr" in stem) or _has_term(blob, INSTR_TERMS)


def _uarch_candidate(record):
    return _has_term(_record_blob(record), UARCH_TERMS)


def _os_candidate(record):
    return _has_term(_record_blob(record), OS_TERMS)


def _clean_group(name):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
    return value or "core"


def _family_from_file(arch, file_rel):
    stem = Path(file_rel).stem
    if stem.lower().startswith(arch.lower()):
        stem = stem[len(arch) :]
    for marker in ("Instr", "Instruction"):
        if marker in stem:
            suffix = stem.split(marker, 1)[1]
            if suffix:
                return _clean_group(suffix)
    return _clean_group(stem or "core")


def _instruction_group(arch, record):
    for parent in record["parents"]:
        low = parent.lower()
        if any(token in low for token in ("instr", "inst", "pseudo", "alias", "format")) and low not in {
            "instruction",
            "instr",
            "inst",
            "i",
        }:
            return _clean_group(parent)
    return _family_from_file(arch, record["file"])


def _uarch_group(record):
    blob = _record_blob(record)
    if "processor" in blob or "cpu" in blob:
        return "processors"
    if "feature" in blob or "subtarget" in blob:
        return "features"
    if "itinerary" in blob:
        return "itineraries"
    if any(term in blob for term in ("sched", "schedule", "latency", "pipeline", "resource", "issue")):
        return "scheduling"
    return "misc"


def _os_group(record):
    blob = _record_blob(record)
    if any(term in blob for term in ("callingconv", "callconv", "ccassign")):
        return "calling_conventions"
    if any(term in blob for term in ("callee", "caller", "csr", "regmask")):
        return "register_conventions"
    if any(term in blob for term in ("abi", "stack", "libcall")):
        return "abi"
    return "misc"


def _first_quoted(text):
    match = _QUOTE_RE.search(text or "")
    if not match:
        return None
    return match.group(1).encode("utf-8").decode("unicode_escape")


def _first_word(text):
    if not text:
        return None
    match = re.search(r"[A-Za-z][A-Za-z0-9_.+-]*", text)
    return match.group(0) if match else None


def _pick_field_value(fields, names, contains):
    lowered = {key.lower(): value for key, value in fields.items()}
    for name in names:
        if name in lowered:
            return lowered[name]
    for key, value in lowered.items():
        if contains in key:
            return value
    return None


def _extract_opcode(record):
    value = _pick_field_value(
        record["fields"],
        ("opcode", "opc", "baseopcode", "opcodevalue", "op"),
        "opcode",
    )
    if value:
        return value[:120]
    parent = record["parent_raw"]
    match = re.search(r"\b(0x[0-9A-Fa-f]+|0b[01]+|[0-9]+)\b", parent)
    return match.group(1) if match else None


def _extract_mnemonic(record):
    value = _pick_field_value(
        record["fields"],
        ("mnemonic", "asmstring", "asmstr", "asmname", "opcodestr"),
        "asm",
    )
    if value:
        quoted = _first_quoted(value)
        return _first_word(quoted or value)
    quoted = _first_quoted(record["parent_raw"]) or _first_quoted(record["signature"])
    return _first_word(quoted)


def _instruction_record(arch, record):
    group = _instruction_group(arch, record)
    opcode = _extract_opcode(record)
    mnemonic = _extract_mnemonic(record)
    missing = []
    if not opcode:
        missing.append("opcode")
        opcode = MISSING
    if not mnemonic:
        missing.append("mnemonic")
        mnemonic = MISSING
    return group, {
        "name": record["name"] or MISSING,
        "kind": record["kind"],
        "opcode": opcode,
        "mnemonic": mnemonic,
        "file": record["file"],
        "line": record["line"],
        "parents": record["parents"],
        "parent_expr": record["parent_raw"],
        "fields": record["fields"],
        "missing": missing,
    }


def _generic_record(record):
    return {
        "name": record["name"] or MISSING,
        "kind": record["kind"],
        "file": record["file"],
        "line": record["line"],
        "parents": record["parents"],
        "parent_expr": record["parent_raw"],
        "fields": record["fields"],
    }


def _sort_records(records):
    records.sort(
        key=lambda row: (
            row.get("file", ""),
            row.get("line", 0),
            row.get("name", ""),
            row.get("kind", ""),
        )
    )
    return records


def _sorted_grouped_map(grouped):
    out = {}
    for key in sorted(grouped):
        out[key] = _sort_records(grouped[key])
    return out


def _schema_summary(grouped_instructions):
    summary = {}
    missing_opcode = 0
    missing_mnemonic = 0
    for group, rows in grouped_instructions.items():
        record_fields = set()
        td_fields = set()
        for row in rows:
            record_fields.update(row.keys())
            td_fields.update(row.get("fields", {}).keys())
            missing_opcode += int("opcode" in row.get("missing", ()))
            missing_mnemonic += int("mnemonic" in row.get("missing", ()))
        summary[group] = {
            "count": len(rows),
            "record_fields": sorted(record_fields),
            "tablegen_field_inventory": sorted(td_fields),
        }
    return summary, missing_opcode, missing_mnemonic


def _parse_arch_records(source_root):
    parser = Parser()
    parser.language = Language(tree_sitter_tablegen.language())
    td_files = sorted(source_root.rglob("*.td"))
    records = []
    parse_issues = []
    files_with_error_nodes = 0
    for td_path in td_files:
        rel = td_path.relative_to(source_root).as_posix()
        try:
            source = td_path.read_bytes()
        except Exception as exc:
            parse_issues.append({"file": rel, "error": f"read_error: {exc}"})
            continue
        try:
            tree = parser.parse(source)
        except Exception as exc:
            parse_issues.append({"file": rel, "error": f"parse_exception: {exc}"})
            continue
        root = tree.root_node
        if root.has_error:
            files_with_error_nodes += 1
        for node in _walk(root):
            if node.is_named and node.type in RECORD_KINDS:
                records.append(_record_from_node(node, rel))
    records.sort(key=lambda row: (row["file"], row["line"], row["kind"], row["name"] or ""))
    return td_files, records, parse_issues, files_with_error_nodes


def build_grab_payload(llvm_root: Path, arch: str):
    source_root = llvm_root / arch
    if not source_root.is_dir():
        raise FileNotFoundError(f"architecture directory not found: {source_root}")

    td_files, records, parse_issues, files_with_error_nodes = _parse_arch_records(source_root)
    instructions = {}
    uarch = {}
    os_interop = {}

    for record in records:
        if _instruction_candidate(record):
            group, row = _instruction_record(arch, record)
            instructions.setdefault(group, []).append(row)
        if _uarch_candidate(record):
            uarch.setdefault(_uarch_group(record), []).append(_generic_record(record))
        if _os_candidate(record):
            os_interop.setdefault(_os_group(record), []).append(_generic_record(record))

    instructions = _sorted_grouped_map(instructions)
    uarch = _sorted_grouped_map(uarch)
    os_interop = _sorted_grouped_map(os_interop)

    schema, missing_opcode, missing_mnemonic = _schema_summary(instructions)
    relevant_files = sorted(
        {
            row["file"]
            for rows in list(instructions.values()) + list(uarch.values()) + list(os_interop.values())
            for row in rows
        }
    )
    notes = []
    if files_with_error_nodes:
        notes.append(f"{files_with_error_nodes} td files contain Tree-Sitter error nodes.")
    if parse_issues:
        notes.append(f"{len(parse_issues)} td files had read/parse exceptions.")
    if missing_opcode or missing_mnemonic:
        notes.append(
            f"instruction missing fields: opcode={missing_opcode}, mnemonic={missing_mnemonic}."
        )

    header = {
        "arch": arch,
        "source_root": str(source_root),
        "td_files_scanned": len(td_files),
        "record_count": len(records),
        "relevant_td_files": relevant_files,
        "instruction_groups": sorted(instructions.keys()),
        "instruction_group_schema": schema,
        "instruction_kind_hints": sorted(
            {
                parent
                for rows in instructions.values()
                for row in rows
                for parent in row.get("parents", [])
                if parent
            }
        ),
        "partial_parse": {
            "files_with_error_nodes": files_with_error_nodes,
            "files_with_read_or_parse_exceptions": len(parse_issues),
            "samples": parse_issues[:8],
        },
        "notes": notes,
    }

    return {
        "header": header,
        "uArch": {
            "summary": {
                "group_count": len(uarch),
                "record_count": sum(len(rows) for rows in uarch.values()),
            },
            "groups": uarch,
        },
        "os_interop": {
            "summary": {
                "group_count": len(os_interop),
                "record_count": sum(len(rows) for rows in os_interop.values()),
            },
            "groups": os_interop,
        },
        "instructions": {
            "summary": {
                "group_count": len(instructions),
                "record_count": sum(len(rows) for rows in instructions.values()),
                "missing_opcode_records": missing_opcode,
                "missing_mnemonic_records": missing_mnemonic,
            },
            "groups": instructions,
        },
    }


def write_grab_payload(path: Path, payload):
    suffix = path.suffix.lower()
    if suffix not in ("", ".json"):
        raise ValueError(f"unsupported output extension: {path.suffix} (supported: .json)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
