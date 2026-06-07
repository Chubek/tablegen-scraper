#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_tablegen


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
            value = None
            if node.child_count >= 2:
                value = _decode_text(node.child(1))
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


def run_td_scrape(default_arch, default_output):
    parser = argparse.ArgumentParser(description="Scrape TableGen declarations for one LLVM architecture.")
    parser.add_argument(
        "--llvm-root",
        default="LLVM-Targets",
        help="Path to LLVM target root containing architecture directories (default: LLVM-Targets).",
    )
    parser.add_argument("--arch", default=default_arch, help=f"Architecture directory name (default: {default_arch}).")
    parser.add_argument(
        "--output",
        default=default_output,
        help="Output JSON path ('-' prints to stdout).",
    )
    args = parser.parse_args()

    source_root = Path(args.llvm_root) / args.arch
    if not source_root.is_dir():
        raise SystemExit(f"architecture directory not found: {source_root}")

    td_files = sorted(source_root.rglob("*.td"))
    language = Language(tree_sitter_tablegen.language())
    ts_parser = Parser()
    ts_parser.language = language

    files = [_parse_td_file(ts_parser, path) for path in td_files]
    failed = sum(1 for item in files if item["errors"])
    with_parse_error = sum(1 for item in files if item["parse_error"])

    payload = {
        "architecture": args.arch,
        "source_root": str(source_root),
        "summary": {
            "td_files": len(td_files),
            "files_with_io_or_parse_exception": failed,
            "files_with_tree_sitter_parse_error_nodes": with_parse_error,
            "total_includes": sum(len(item["includes"]) for item in files),
            "total_classes": sum(len(item["classes"]) for item in files),
            "total_defs": sum(len(item["defs"]) for item in files),
            "total_defms": sum(len(item["defms"]) for item in files),
            "total_multiclasses": sum(len(item["multiclasses"]) for item in files),
        },
        "files": files,
    }

    if args.output == "-":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
