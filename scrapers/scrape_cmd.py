#!/usr/bin/env python3
import json
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_tablegen


SCRAPE_CATEGORY_SPECS = (
    ("instructions", "--instructions", "Instruction defs and related records.", "heuristic"),
    ("opcodes", "--opcodes", "Opcode-like defs/fields where present.", "heuristic"),
    ("mnemonics", "--mnemonics", "Asm mnemonic/asm string related records.", "heuristic"),
    ("registers", "--registers", "Register definitions.", "heuristic"),
    ("register-classes", "--register-classes", "Register class definitions.", "heuristic"),
    ("operands", "--operands", "Operand-related definitions.", "heuristic"),
    ("asm-operands", "--asm-operands", "Assembler operand variants.", "heuristic"),
    ("patterns", "--patterns", "Selection pattern-related records.", "heuristic"),
    ("intrinsics", "--intrinsics", "Target intrinsic records.", "heuristic"),
    ("scheduling", "--scheduling", "Scheduling model records.", "heuristic"),
    ("itineraries", "--itineraries", "Instruction itinerary records.", "heuristic"),
    ("processors", "--processors", "CPU/processor model records.", "heuristic"),
    ("features", "--features", "Subtarget feature records.", "heuristic"),
    ("subtargets", "--subtargets", "Subtarget modeling records.", "heuristic"),
    ("encodings", "--encodings", "Encoding-related records.", "heuristic"),
    ("pseudo-instructions", "--pseudo-instructions", "Pseudo instruction records.", "heuristic"),
    ("aliases", "--aliases", "Instruction alias records.", "heuristic"),
    ("formats", "--formats", "Format/grouping records.", "heuristic"),
    ("dag-patterns", "--dag-patterns", "DAG/pattern fragments.", "heuristic"),
    ("types", "--types", "Type-related records.", "heuristic"),
    ("classes", "--classes", "Raw TableGen class declarations.", "structural"),
    ("defs", "--defs", "Raw TableGen def declarations.", "structural"),
    ("defms", "--defms", "Raw TableGen defm declarations.", "structural"),
    ("multiclasses", "--multiclasses", "Raw TableGen multiclass declarations.", "structural"),
    ("includes", "--includes", "Raw TableGen include directives.", "structural"),
)

SCRAPE_CATEGORY_NAMES = tuple(spec[0] for spec in SCRAPE_CATEGORY_SPECS)
_CATEGORY_MODES = {spec[0]: spec[3] for spec in SCRAPE_CATEGORY_SPECS}

_KEYWORDS = {
    "instructions": ("inst", "instruction", "instalias", "pseudo"),
    "opcodes": ("opcode", "opc", "encoding"),
    "mnemonics": ("mnemonic", "asmstring", "asmstr"),
    "registers": ("register", " reg", "reg"),
    "register-classes": ("registerclass", "regclass", "register_class"),
    "operands": ("operand", "opnd"),
    "asm-operands": ("asmoperand", "asm_operand"),
    "patterns": ("pattern", "patfrag", "pat"),
    "intrinsics": ("intrinsic",),
    "scheduling": ("sched", "schedule", "schedmodel", "schedread", "schedwrite"),
    "itineraries": ("itin", "itinerary"),
    "processors": ("processor", "cpu", "proc"),
    "features": ("feature", "subtargetfeature"),
    "subtargets": ("subtarget",),
    "encodings": ("encoding", "enc"),
    "pseudo-instructions": ("pseudo",),
    "aliases": ("alias", "instalias"),
    "formats": ("format", "frm"),
    "dag-patterns": ("dag", "patfrag", "pattern"),
    "types": ("type", "valuetype", "vt"),
}


def _decode_text(node):
    if node is None:
        return None
    text = node.text.decode("utf-8", errors="replace").strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _extract_name(node):
    named = node.child_by_field_name("name")
    if named is not None:
        return _decode_text(named)
    for child in node.children:
        if child.type in ("identifier", "value"):
            return _decode_text(child)
    return None


def _walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _parse_td_file(parser, path):
    result = {
        "file": str(path),
        "parse_error": False,
        "includes": [],
        "classes": [],
        "defs": [],
        "defms": [],
        "multiclasses": [],
        "errors": [],
    }
    try:
        source = path.read_bytes()
    except Exception as exc:
        result["errors"].append(f"read_error: {exc}")
        return result
    try:
        tree = parser.parse(source)
    except Exception as exc:
        result["errors"].append(f"parse_exception: {exc}")
        return result

    root = tree.root_node
    result["parse_error"] = bool(root.has_error)
    for node in _walk(root):
        line = node.start_point[0] + 1
        if node.type == "include":
            value = _decode_text(node.child(1)) if node.child_count >= 2 else None
            result["includes"].append({"line": line, "value": value})
        elif node.type == "class":
            result["classes"].append({"line": line, "name": _extract_name(node)})
        elif node.type == "def":
            result["defs"].append({"line": line, "name": _extract_name(node)})
        elif node.type == "defm":
            result["defms"].append({"line": line, "name": _extract_name(node)})
        elif node.type == "multiclass":
            result["multiclasses"].append({"line": line, "name": _extract_name(node)})
    return result


def parse_td_inventory(llvm_root: Path, arch: str):
    source_root = llvm_root / arch
    if not source_root.is_dir():
        raise FileNotFoundError(f"architecture directory not found: {source_root}")

    td_files = sorted(source_root.rglob("*.td"))
    parser = Parser()
    parser.language = Language(tree_sitter_tablegen.language())
    files = [_parse_td_file(parser, path) for path in td_files]
    return {
        "architecture": arch,
        "source_root": str(source_root),
        "summary": {
            "td_files": len(td_files),
            "files_with_io_or_parse_exception": sum(1 for item in files if item["errors"]),
            "files_with_tree_sitter_parse_error_nodes": sum(1 for item in files if item["parse_error"]),
            "total_includes": sum(len(item["includes"]) for item in files),
            "total_classes": sum(len(item["classes"]) for item in files),
            "total_defs": sum(len(item["defs"]) for item in files),
            "total_defms": sum(len(item["defms"]) for item in files),
            "total_multiclasses": sum(len(item["multiclasses"]) for item in files),
        },
        "files": files,
    }


def _flat_records(files, key, value_field):
    rows = []
    for item in files:
        file_path = item["file"]
        for row in item[key]:
            rows.append({"file": file_path, "line": row["line"], value_field: row.get(value_field)})
    rows.sort(key=lambda row: (row["file"], row["line"], str(row.get(value_field) or "")))
    return rows


def _named_pool(files):
    pool = []
    for item in files:
        file_path = item["file"]
        for kind in ("classes", "defs", "defms", "multiclasses"):
            for row in item[kind]:
                name = row.get("name")
                if not name:
                    continue
                pool.append({"file": file_path, "line": row["line"], "kind": kind[:-1], "name": name})
    pool.sort(key=lambda row: (row["file"], row["line"], row["kind"], row["name"]))
    return pool


def _keyword_records(pool, keywords):
    words = tuple(word.lower() for word in keywords)
    rows = [row for row in pool if any(word in row["name"].lower() for word in words)]
    return rows


def _category_records(category, files, pool):
    if category == "includes":
        return _flat_records(files, "includes", "value")
    if category == "classes":
        return _flat_records(files, "classes", "name")
    if category == "defs":
        return _flat_records(files, "defs", "name")
    if category == "defms":
        return _flat_records(files, "defms", "name")
    if category == "multiclasses":
        return _flat_records(files, "multiclasses", "name")
    return _keyword_records(pool, _KEYWORDS.get(category, ()))


def build_scrape_payload(llvm_root: Path, arch: str, categories):
    inventory = parse_td_inventory(llvm_root, arch)
    files = inventory["files"]
    pool = _named_pool(files)
    out = {}
    for category in categories:
        records = _category_records(category, files, pool)
        out[category] = {
            "implemented": True,
            "mode": _CATEGORY_MODES.get(category, "heuristic"),
            "count": len(records),
            "records": records,
        }
    return {
        "architecture": arch,
        "source_root": inventory["source_root"],
        "tablegen_summary": inventory["summary"],
        "selected_categories": list(categories),
        "categories": out,
    }


def payload_to_json(payload):
    return json.dumps(payload, indent=2, sort_keys=True)

