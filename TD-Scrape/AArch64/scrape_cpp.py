#!/usr/bin/env python3
import argparse
import json
import warnings
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_cpp


def walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def decode(text):
    return text.decode("utf-8", errors="replace")


def extract_func_name(function_node):
    declarator = None
    for child in function_node.children:
        if "declarator" in child.type:
            declarator = child
            break
    if declarator is None:
        return None
    for node in walk(declarator):
        if node.type in ("identifier", "field_identifier"):
            return decode(node.text)
    return None


def parse_cpp_file(parser, path):
    result = {
        "file": str(path),
        "parse_error": False,
        "init_functions": [],
        "target_registry_calls": [],
        "register_target_declarations": [],
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

    for node in walk(root):
        line = node.start_point[0] + 1
        if node.type == "function_definition":
            name = extract_func_name(node)
            if name and name.startswith("LLVMInitialize"):
                result["init_functions"].append({"line": line, "name": name})
        elif node.type == "call_expression":
            text = decode(node.text)
            if "TargetRegistry::RegisterTarget" in text:
                result["target_registry_calls"].append(
                    {"line": line, "snippet": " ".join(text.split())[:240]}
                )
        elif node.type == "declaration":
            text = decode(node.text)
            if "RegisterTarget<" in text:
                result["register_target_declarations"].append(
                    {"line": line, "snippet": " ".join(text.split())[:240]}
                )
    return result


def main():
    ap = argparse.ArgumentParser(description="Scrape AArch64 C++ registration hooks using Tree-Sitter C++.")
    ap.add_argument("--llvm-root", default="LLVM-Targets")
    ap.add_argument("--arch", default="AArch64")
    ap.add_argument("--output", default="TD-Scrape/AArch64/cpp_inventory.json")
    args = ap.parse_args()

    src_root = Path(args.llvm_root) / args.arch
    if not src_root.is_dir():
        raise SystemExit(f"architecture directory not found: {src_root}")

    files = sorted(src_root.rglob("*.cpp"))
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    language = Language(tree_sitter_cpp.language())
    parser = Parser()
    parser.language = language

    parsed = [parse_cpp_file(parser, path) for path in files]
    payload = {
        "architecture": args.arch,
        "source_root": str(src_root),
        "summary": {
            "cpp_files": len(files),
            "files_with_io_or_parse_exception": sum(1 for item in parsed if item["errors"]),
            "files_with_tree_sitter_parse_error_nodes": sum(1 for item in parsed if item["parse_error"]),
            "total_init_functions": sum(len(item["init_functions"]) for item in parsed),
            "total_target_registry_calls": sum(len(item["target_registry_calls"]) for item in parsed),
            "total_register_target_declarations": sum(
                len(item["register_target_declarations"]) for item in parsed
            ),
        },
        "files": parsed,
    }

    if args.output == "-":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
