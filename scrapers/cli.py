#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

from .scrape_cmd import (
    SCRAPE_CATEGORY_SPECS,
    SCRAPE_CATEGORY_NAMES,
    build_scrape_payload,
    payload_to_json,
)

ARCHITECTURES = (
    "AArch64",
    "AMDGPU",
    "ARC",
    "ARM",
    "AVR",
    "BPF",
    "CSKY",
    "DirectX",
    "Hexagon",
    "Lanai",
    "LoongArch",
    "M68k",
    "Mips",
    "MSP430",
    "NVPTX",
    "PowerPC",
    "RISCV",
    "Sparc",
    "SPIRV",
    "SystemZ",
    "VE",
    "WebAssembly",
    "X86",
    "XCore",
    "Xtensa",
)
ARCH_SET = set(ARCHITECTURES)
COMBINABLE_SCRAPE_CATEGORIES = {name for name, _flag, _desc, mode in SCRAPE_CATEGORY_SPECS if mode == "heuristic"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _llvm_root(args) -> Path:
    path = Path(args.llvm_root)
    return (_repo_root() / path).resolve() if not path.is_absolute() else path.resolve()


def _td_scrape_script() -> Path:
    return _repo_root() / "TD-Scrape" / "AArch64" / "scrape_td.py"


def _cpp_scrape_script() -> Path:
    return _repo_root() / "TD-Scrape" / "AArch64" / "scrape_cpp.py"


def _default_td_output(arch: str) -> str:
    return str(_repo_root() / "output" / arch / "td_inventory.json")


def _default_cpp_output(arch: str) -> str:
    return str(_repo_root() / "output" / arch / "cpp_inventory.json")


def _resolve_output_path(path: str) -> Path:
    raw = Path(path)
    resolved = (_repo_root() / raw).resolve() if not raw.is_absolute() else raw.resolve()
    td_scrape_root = (_repo_root() / "TD-Scrape").resolve()
    if resolved == td_scrape_root or td_scrape_root in resolved.parents:
        raise ValueError(f"refusing to write inside TD-Scrape: {resolved}")
    return resolved


def _scan_dirs(root: Path):
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def _scan_arch_dirs(root: Path):
    return [name for name in _scan_dirs(root) if name in ARCH_SET]


def _arch_arg(value: str) -> str:
    if value == "ALL" or value in ARCH_SET:
        return value
    raise argparse.ArgumentTypeError(
        f"invalid architecture: {value!r}; use `arch list` to see valid names, or ALL"
    )


def _run_subprocess(cmd):
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout)
        return proc.returncode
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    return 0


def _category_file_name(category: str) -> str:
    return f"{category}.json"


def _default_combine_file_name(categories):
    parts = [item.replace("-", " ").title().replace(" ", "-") for item in categories]
    return "-".join(parts) + ".json"


def _parse_csv_categories(raw: str):
    out = []
    for part in raw.split(","):
        item = part.strip()
        if item:
            out.append(item)
    return out


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_arch_list(_args):
    for arch in ARCHITECTURES:
        print(arch)
    return 0


def cmd_arch_scan(args):
    root = _llvm_root(args)
    if not root.is_dir():
        print(f"llvm root not found: {root}", file=sys.stderr)
        return 2
    found = _scan_dirs(root) if args.include_noncanonical else _scan_arch_dirs(root)
    if args.format == "json":
        print(json.dumps({"llvm_root": str(root), "architectures": found}, indent=2, sort_keys=True))
        return 0
    for arch in found:
        print(arch)
    return 0


def cmd_arch_verify(args):
    root = _llvm_root(args)
    if not root.is_dir():
        print(f"llvm root not found: {root}", file=sys.stderr)
        return 2
    found = set(_scan_arch_dirs(root))
    expected = set(ARCHITECTURES)
    payload = {
        "llvm_root": str(root),
        "expected_count": len(ARCHITECTURES),
        "found_count": len(found),
        "missing": sorted(expected - found),
        "extra_canonical": sorted(found - expected),
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"expected={payload['expected_count']} found={payload['found_count']}")
        print(f"missing={payload['missing']}")
    return 1 if payload["missing"] else 0


def cmd_td_run(args):
    script = _td_scrape_script()
    if not script.is_file():
        print(f"scraper script not found: {script}", file=sys.stderr)
        return 2
    root = _llvm_root(args)
    if args.arch == "ALL":
        if args.output:
            print("--output is not supported with --arch ALL; use defaults under output/<arch>/", file=sys.stderr)
            return 2
        failures = 0
        for arch in ARCHITECTURES:
            try:
                output = _resolve_output_path(_default_td_output(arch))
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            cmd = [sys.executable, str(script), "--llvm-root", str(root), "--arch", arch, "--output", str(output)]
            rc = _run_subprocess(cmd)
            if rc != 0:
                failures += 1
        return 1 if failures else 0
    try:
        output = _resolve_output_path(args.output or _default_td_output(args.arch))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    cmd = [sys.executable, str(script), "--llvm-root", str(root), "--arch", args.arch, "--output", str(output)]
    return _run_subprocess(cmd)


def cmd_cpp_run(args):
    script = _cpp_scrape_script()
    if not script.is_file():
        print(f"scraper script not found: {script}", file=sys.stderr)
        return 2
    root = _llvm_root(args)
    if args.arch == "ALL":
        if args.output:
            print("--output is not supported with --arch ALL; use defaults under output/<arch>/", file=sys.stderr)
            return 2
        failures = 0
        for arch in ARCHITECTURES:
            try:
                output = _resolve_output_path(_default_cpp_output(arch))
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            cmd = [sys.executable, str(script), "--llvm-root", str(root), "--arch", arch, "--output", str(output)]
            rc = _run_subprocess(cmd)
            if rc != 0:
                failures += 1
        return 1 if failures else 0
    try:
        output = _resolve_output_path(args.output or _default_cpp_output(args.arch))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    cmd = [sys.executable, str(script), "--llvm-root", str(root), "--arch", args.arch, "--output", str(output)]
    return _run_subprocess(cmd)


def cmd_td_smoke(args):
    script = _td_scrape_script()
    if not script.is_file():
        print(f"scraper script not found: {script}", file=sys.stderr)
        return 2
    root = _llvm_root(args)
    archs = ARCHITECTURES if args.all or args.arch == "ALL" else _scan_arch_dirs(root) if args.all_found else [args.arch]
    try:
        out_dir = _resolve_output_path(args.output_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    failures = 0
    for arch in archs:
        out_path = out_dir / f"{arch}.json"
        cmd = [sys.executable, str(script), "--llvm-root", str(root), "--arch", arch, "--output", str(out_path)]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if proc.returncode != 0:
            failures += 1
            rows.append({"architecture": arch, "status": "FAIL", "error": (proc.stderr or proc.stdout).strip()})
            continue
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            summary = data["summary"]
        except Exception as exc:
            failures += 1
            rows.append({"architecture": arch, "status": "FAIL", "error": f"invalid_json_or_shape: {exc}"})
            continue
        rows.append(
            {
                "architecture": arch,
                "status": "OK",
                "td_files": summary["td_files"],
                "parse_error_files": summary["files_with_tree_sitter_parse_error_nodes"],
                "io_or_parse_exceptions": summary["files_with_io_or_parse_exception"],
            }
        )

    if args.format == "json":
        print(
            json.dumps(
                {
                    "total": len(rows),
                    "ok": sum(1 for row in rows if row["status"] == "OK"),
                    "failed": failures,
                    "rows": rows,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("arch\tstatus\ttd_files\tparse_error_files\tio_or_parse_exceptions")
        for row in rows:
            print(
                f"{row['architecture']}\t{row['status']}\t"
                f"{row.get('td_files', '-')}\t{row.get('parse_error_files', '-')}\t"
                f"{row.get('io_or_parse_exceptions', '-')}"
            )
        print(f"\nsummary: total={len(rows)} ok={len(rows)-failures} failed={failures}")
        if failures:
            print("failed_details:")
            for row in rows:
                if row["status"] == "FAIL":
                    print(f"- {row['architecture']}: {row['error']}")
    return 1 if failures else 0


def cmd_cpp_smoke(args):
    script = _cpp_scrape_script()
    if not script.is_file():
        print(f"scraper script not found: {script}", file=sys.stderr)
        return 2
    root = _llvm_root(args)
    archs = ARCHITECTURES if args.arch == "ALL" else _scan_arch_dirs(root) if args.all_found else [args.arch]
    try:
        out_dir = _resolve_output_path(args.output_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    failures = 0
    for arch in archs:
        out_path = out_dir / f"{arch}.cpp.json"
        cmd = [sys.executable, str(script), "--llvm-root", str(root), "--arch", arch, "--output", str(out_path)]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if proc.returncode != 0:
            failures += 1
            rows.append({"architecture": arch, "status": "FAIL", "error": (proc.stderr or proc.stdout).strip()})
            continue
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            summary = data["summary"]
        except Exception as exc:
            failures += 1
            rows.append({"architecture": arch, "status": "FAIL", "error": f"invalid_json_or_shape: {exc}"})
            continue
        rows.append(
            {
                "architecture": arch,
                "status": "OK",
                "cpp_files": summary["cpp_files"],
                "parse_error_files": summary["files_with_tree_sitter_parse_error_nodes"],
                "io_or_parse_exceptions": summary["files_with_io_or_parse_exception"],
            }
        )

    if args.format == "json":
        print(
            json.dumps(
                {
                    "total": len(rows),
                    "ok": sum(1 for row in rows if row["status"] == "OK"),
                    "failed": failures,
                    "rows": rows,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("arch\tstatus\tcpp_files\tparse_error_files\tio_or_parse_exceptions")
        for row in rows:
            print(
                f"{row['architecture']}\t{row['status']}\t"
                f"{row.get('cpp_files', '-')}\t{row.get('parse_error_files', '-')}\t"
                f"{row.get('io_or_parse_exceptions', '-')}"
            )
        print(f"\nsummary: total={len(rows)} ok={len(rows)-failures} failed={failures}")
        if failures:
            print("failed_details:")
            for row in rows:
                if row["status"] == "FAIL":
                    print(f"- {row['architecture']}: {row['error']}")
    return 1 if failures else 0


def _selected_scrape_categories(args):
    selected = [name for name in SCRAPE_CATEGORY_NAMES if getattr(args, f"scrape_{name.replace('-', '_')}", False)]
    if args.all:
        return list(SCRAPE_CATEGORY_NAMES)
    return selected


def cmd_scrape(args):
    selected = _selected_scrape_categories(args)
    if not selected:
        print("at least one scrape target must be selected; pass --all or one/more scrape flags", file=sys.stderr)
        return 2
    if args.merge and args.combine:
        print("--merge and --combine are mutually exclusive", file=sys.stderr)
        return 2
    if args.combine_file and not args.combine:
        print("--combine-file requires --combine", file=sys.stderr)
        return 2
    combine = _parse_csv_categories(args.combine) if args.combine else []
    if combine:
        unknown = sorted(item for item in combine if item not in SCRAPE_CATEGORY_NAMES)
        if unknown:
            print(f"--combine has unknown categories: {', '.join(unknown)}", file=sys.stderr)
            return 2
        non_combinable = sorted(item for item in combine if item not in COMBINABLE_SCRAPE_CATEGORIES)
        if non_combinable:
            print(
                f"--combine only supports semantically combinable categories: {', '.join(non_combinable)}",
                file=sys.stderr,
            )
            return 2
        missing = sorted(item for item in combine if item not in selected)
        if missing:
            print(
                f"--combine categories must be selected by flags/--all first: {', '.join(missing)}",
                file=sys.stderr,
            )
            return 2
        if len(combine) < 2:
            print("--combine requires at least two categories", file=sys.stderr)
            return 2
    if (args.merge or combine or args.combine_file) and not args.output:
        print("--output/-o is required when using --merge/--combine/--combine-file", file=sys.stderr)
        return 2
    root = _llvm_root(args)
    archs = ARCHITECTURES if args.arch == "ALL" else [args.arch]
    payload = {
        "command": "scrape",
        "requested_arch": args.arch,
        "selected_categories": selected,
        "results": {},
    }
    failures = 0
    written = []
    output_root = _resolve_output_path(args.output) if args.output else None
    for arch in archs:
        try:
            arch_payload = build_scrape_payload(root, arch, selected)
            payload["results"][arch] = arch_payload
            if output_root:
                arch_dir = output_root / arch
                categories = arch_payload["categories"]
                if args.merge:
                    name = args.merge if isinstance(args.merge, str) else "Collection.json"
                    out_path = arch_dir / name
                    _write_json(
                        out_path,
                        {
                            "architecture": arch,
                            "selected_categories": selected,
                            "categories": {name: categories[name] for name in selected},
                        },
                    )
                    written.append(str(out_path))
                elif combine:
                    combine_set = set(combine)
                    combine_name = args.combine_file or _default_combine_file_name(combine)
                    combine_path = arch_dir / combine_name
                    _write_json(
                        combine_path,
                        {
                            "architecture": arch,
                            "selected_categories": combine,
                            "categories": {name: categories[name] for name in combine},
                        },
                    )
                    written.append(str(combine_path))
                    for name in selected:
                        if name in combine_set:
                            continue
                        out_path = arch_dir / _category_file_name(name)
                        _write_json(out_path, categories[name])
                        written.append(str(out_path))
                else:
                    for name in selected:
                        out_path = arch_dir / _category_file_name(name)
                        _write_json(out_path, categories[name])
                        written.append(str(out_path))
        except Exception as exc:
            failures += 1
            payload["results"][arch] = {"error": str(exc)}
    if output_root:
        print(payload_to_json({"command": "scrape", "written_files": written, "failed_architectures": failures}))
    else:
        print(payload_to_json(payload))
    return 1 if failures else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="scrapers",
        description="CLI for TD-Scrape architecture scrapers.",
    )
    parser.add_argument(
        "--llvm-root",
        default="LLVM-Targets",
        help="Path to LLVM targets root (default: LLVM-Targets).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    arch = sub.add_parser("arch", help="Architecture inventory commands.")
    arch_sub = arch.add_subparsers(dest="arch_command", required=True)

    arch_list = arch_sub.add_parser("list", help="List canonical architecture set.")
    arch_list.set_defaults(func=cmd_arch_list)

    arch_scan = arch_sub.add_parser("scan", help="List architecture directories found in llvm-root.")
    arch_scan.add_argument(
        "--include-noncanonical",
        action="store_true",
        help="Include non-canonical directories found in llvm-root.",
    )
    arch_scan.add_argument("--format", choices=("table", "json"), default="table", help="Report format.")
    arch_scan.set_defaults(func=cmd_arch_scan)

    arch_verify = arch_sub.add_parser("verify", help="Verify canonical architecture set in llvm-root.")
    arch_verify.add_argument("--format", choices=("table", "json"), default="table", help="Report format.")
    arch_verify.set_defaults(func=cmd_arch_verify)

    td = sub.add_parser("td", help="TableGen scraper commands.")
    td_sub = td.add_subparsers(dest="td_command", required=True)

    td_run = td_sub.add_parser("run", help="Run TD scraper for one architecture.")
    td_run.add_argument(
        "--arch",
        required=True,
        type=_arch_arg,
        metavar="ARCH|ALL",
        help="Architecture name, or ALL.",
    )
    td_run.add_argument("--output", help="Output JSON path (default: output/<arch>/td_inventory.json).")
    td_run.set_defaults(func=cmd_td_run)

    td_smoke = td_sub.add_parser("smoke", help="Smoke test TD scraper for one/all architectures.")
    td_group = td_smoke.add_mutually_exclusive_group(required=True)
    td_group.add_argument(
        "--arch",
        type=_arch_arg,
        metavar="ARCH|ALL",
        help="Single architecture, or ALL.",
    )
    td_group.add_argument("--all", action="store_true", help="Run all canonical architectures.")
    td_group.add_argument("--all-found", action="store_true", help="Run canonical architectures present in llvm-root.")
    td_smoke.add_argument("--output-dir", default="output/td-smoke", help="Directory for generated JSON.")
    td_smoke.add_argument("--format", choices=("table", "json"), default="table", help="Report format.")
    td_smoke.set_defaults(func=cmd_td_smoke)

    cpp = sub.add_parser("cpp", help="C++ scraper commands.")
    cpp_sub = cpp.add_subparsers(dest="cpp_command", required=True)

    cpp_run = cpp_sub.add_parser("run", help="Run C++ scraper for one architecture.")
    cpp_run.add_argument(
        "--arch",
        required=True,
        type=_arch_arg,
        metavar="ARCH|ALL",
        help="Architecture name, or ALL.",
    )
    cpp_run.add_argument("--output", help="Output JSON path (default: output/<arch>/cpp_inventory.json).")
    cpp_run.set_defaults(func=cmd_cpp_run)

    cpp_smoke = cpp_sub.add_parser("smoke", help="Smoke test C++ scraper.")
    cpp_group = cpp_smoke.add_mutually_exclusive_group(required=True)
    cpp_group.add_argument(
        "--arch",
        type=_arch_arg,
        metavar="ARCH|ALL",
        help="Single architecture, or ALL.",
    )
    cpp_group.add_argument("--all-found", action="store_true", help="Run canonical architectures present in llvm-root.")
    cpp_smoke.add_argument("--output-dir", default="output/cpp-smoke", help="Directory for generated JSON.")
    cpp_smoke.add_argument("--format", choices=("table", "json"), default="table", help="Report format.")
    cpp_smoke.set_defaults(func=cmd_cpp_smoke)

    scrape = sub.add_parser("scrape", help="Scrape selected TableGen categories.")
    scrape.add_argument(
        "--arch",
        default="AArch64",
        type=_arch_arg,
        metavar="ARCH|ALL",
        help="Architecture name, or ALL (default: AArch64).",
    )
    scrape.add_argument(
        "--output",
        "-o",
        help="Output directory root. Writes category files under <output>/<arch>/.",
    )
    scrape.add_argument(
        "--merge",
        nargs="?",
        const="Collection.json",
        metavar="FILE",
        help="Write all selected categories into one merged file (default name: Collection.json).",
    )
    scrape.add_argument(
        "--combine",
        metavar="CAT1,CAT2,...",
        help="Combine only selected categories into one file; others remain separate.",
    )
    scrape.add_argument(
        "--combine-file",
        metavar="FILE",
        help="Output file name for --combine (default: title-cased category names).",
    )
    scrape.add_argument("--all", action="store_true", help="Enable all scrape categories.")
    for name, flag, description, _mode in SCRAPE_CATEGORY_SPECS:
        scrape.add_argument(
            flag,
            action="store_true",
            dest=f"scrape_{name.replace('-', '_')}",
            help=description,
        )
    scrape.set_defaults(func=cmd_scrape)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
