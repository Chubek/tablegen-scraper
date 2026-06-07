# GUIDE.md

## 1) Scope

This guide documents the current LLVM target scraping workspace in this repository:

- `LLVM-Targets/` as source tree;
- `TD-Scrape/` as architecture-only mirrored workspace;
- `scrapers` / `TD-Scrapers` as command-line interfaces.

It focuses on:

- deterministic, rerunnable scraping;
- Tree-Sitter-first parsing for TableGen and C++;
- multi-level CLI usage via `python3 -m scrapers` and `python3 -m TD-Scrapers`.

---

## 2) Repository Layout

### 2.1 Source and mirror roots

- Source root: `LLVM-Targets/`
- Scrape mirror root: `TD-Scrape/`

`TD-Scrape/` includes one subdirectory per canonical LLVM target architecture and excludes shared root-level files (for example `Target.cpp`, `TargetMachine.cpp`, etc.).

### 2.2 Canonical architecture set

The canonical architecture set used by the CLI:

- `AArch64`
- `AMDGPU`
- `ARC`
- `ARM`
- `AVR`
- `BPF`
- `CSKY`
- `DirectX`
- `Hexagon`
- `Lanai`
- `LoongArch`
- `M68k`
- `Mips`
- `MSP430`
- `NVPTX`
- `PowerPC`
- `RISCV`
- `Sparc`
- `SPIRV`
- `SystemZ`
- `VE`
- `WebAssembly`
- `X86`
- `XCore`
- `Xtensa`

### 2.3 Current scraper scripts

- TableGen wrappers:
  - `TD-Scrape/AArch64/scrape_td.py`
  - `TD-Scrape/RISCV/scrape_td.py`
  - `TD-Scrape/X86/scrape_td.py`
- Shared TableGen core:
  - `TD-Scrape/_common/td_scrape_core.py`
- C++ scraper:
  - `TD-Scrape/AArch64/scrape_cpp.py`

### 2.4 CLI entrypoints

- Primary package:
  - `scrapers/__main__.py`
  - `scrapers/cli.py`
- Alias package:
  - `TD-Scrapers/__main__.py`

Both entrypoints invoke the same implementation (`scrapers.cli.main`).

---

## 3) Runtime Requirements

### 3.1 Python

- Python 3.x

### 3.2 Parsers

- `tree_sitter`
- `tree_sitter_tablegen`
- `tree_sitter_cpp`

### 3.3 Filesystem expectations

Default `--llvm-root` is `LLVM-Targets` (relative to current working directory unless absolute path is passed).

---

## 4) CLI Entry and Help Model

### 4.1 Invocation forms

Equivalent forms:

- `python3 -m scrapers ...`
- `python3 -m TD-Scrapers ...`

### 4.2 Multi-level help

Help exists at every level:

- root:
  - `python3 -m scrapers -h`
- first level:
  - `python3 -m scrapers arch -h`
  - `python3 -m scrapers td -h`
  - `python3 -m scrapers cpp -h`
- second level:
  - `python3 -m scrapers arch list -h`
  - `python3 -m scrapers arch scan -h`
  - `python3 -m scrapers arch verify -h`
  - `python3 -m scrapers td run -h`
  - `python3 -m scrapers td smoke -h`
  - `python3 -m scrapers cpp run -h`
  - `python3 -m scrapers cpp smoke -h`

All equivalent commands work with `python3 -m TD-Scrapers ...`.

---

## 5) Command Tree

Top-level commands:

- `arch` — architecture inventory/verification
- `td` — TableGen scraping
- `cpp` — C++ scraping

### 5.1 `arch` commands

#### `arch list`

Prints canonical architecture names in fixed order.

Example:

```bash
python3 -m scrapers arch list
```

#### `arch scan`

Scans directories under `--llvm-root`.

Options:

- `--include-noncanonical`: include all directories, not only canonical architecture names.
- `--format {table,json}`: output style.

Examples:

```bash
python3 -m scrapers arch scan
python3 -m scrapers arch scan --include-noncanonical
python3 -m scrapers arch scan --format json
python3 -m scrapers --llvm-root /abs/path/to/LLVM-Targets arch scan
```

#### `arch verify`

Verifies canonical architecture set in `--llvm-root`.

Options:

- `--format {table,json}`

Exit behavior:

- `0`: no missing canonical architecture directories;
- `1`: one or more canonical directories missing;
- `2`: invalid `--llvm-root`.

Example:

```bash
python3 -m scrapers arch verify
python3 -m scrapers arch verify --format json
```

---

### 5.2 `td` commands

#### `td run`

Runs TableGen scraper for one architecture.

Options:

- `--arch <ARCH>` (required)
- `--output <PATH>` (optional)

Default output when omitted:

- `TD-Scrape/<ARCH>/td_inventory.json`

Examples:

```bash
python3 -m scrapers td run --arch X86
python3 -m scrapers td run --arch RISCV --output /tmp/riscv_td.json
python3 -m scrapers --llvm-root LLVM-Targets td run --arch AArch64
```

#### `td smoke`

Batch smoke for TableGen scraper.

Mutually exclusive target selection:

- `--arch <ARCH>`
- `--all`
- `--all-found`

Other options:

- `--output-dir <DIR>` (default: `/tmp/td-scrape-smoke`)
- `--format {table,json}`

Behavior:

- runs scrape command(s);
- validates generated JSON shape (`summary` presence);
- prints aggregate status;
- returns nonzero if any architecture fails.

Examples:

```bash
python3 -m scrapers td smoke --arch AArch64
python3 -m scrapers td smoke --all
python3 -m scrapers td smoke --all-found --format json
python3 -m scrapers td smoke --all --output-dir /tmp/td-all
```

---

### 5.3 `cpp` commands

#### `cpp run`

Runs C++ scraper for one architecture.

Options:

- `--arch <ARCH>` (required)
- `--output <PATH>` (optional)

Default output when omitted:

- `TD-Scrape/<ARCH>/cpp_inventory.json`

Notes:

- implementation uses `TD-Scrape/AArch64/scrape_cpp.py` as shared runner;
- it accepts `--arch`, so it can run against other architectures.

Examples:

```bash
python3 -m scrapers cpp run --arch AArch64
python3 -m scrapers cpp run --arch RISCV --output /tmp/riscv_cpp.json
```

#### `cpp smoke`

Batch smoke for C++ scraper.

Mutually exclusive target selection:

- `--arch <ARCH>`
- `--all-found`

Other options:

- `--output-dir <DIR>` (default: `/tmp/cpp-scrape-smoke`)
- `--format {table,json}`

Examples:

```bash
python3 -m scrapers cpp smoke --arch AArch64
python3 -m scrapers cpp smoke --all-found --format json
```

---

### 5.4 `scrape` command

Runs category-driven TableGen scraping with explicit boolean flags.

Examples:

```bash
python3 -m TD-Scrape scrape --instructions --opcodes
python3 -m TD-Scrape scrape --mnemonics
python3 -m TD-Scrape scrape --all
```

Default behavior:

- parses `LLVM-Targets/<arch>/**/*.td` with Tree-Sitter TableGen;
- requires at least one category flag, unless `--all` is used;
- emits deterministic JSON keyed by selected category;
- each category returns:
  - `implemented` (bool),
  - `mode` (`structural` or `heuristic`),
  - `count`,
  - `records` list.

#### Flags

##### `--all`

- expands to every supported scrape category;
- composes with `--arch` (including `--arch ALL`);
- equivalent to passing all category flags explicitly.

##### `--instructions`

- semantic intent: instruction defs and instruction-like records;
- mode: `heuristic` (name keyword matching over parsed record pool);
- includes names containing `inst`, `instruction`, `instalias`, `pseudo`.

##### `--opcodes`

- semantic intent: opcode definitions or opcode-related records;
- mode: `heuristic`;
- includes names containing `opcode`, `opc`, `encoding`.

##### `--mnemonics`

- semantic intent: asm mnemonic / asm string-related records;
- mode: `heuristic`;
- includes names containing `mnemonic`, `asmstring`, `asmstr`.

##### `--registers`

- semantic intent: register definitions;
- mode: `heuristic`;
- includes names containing `register`, `reg`.

##### `--register-classes`

- semantic intent: register class definitions;
- mode: `heuristic`;
- includes names containing `registerclass`, `regclass`, `register_class`.

##### `--operands`

- semantic intent: operand-related definitions;
- mode: `heuristic`;
- includes names containing `operand`, `opnd`.

##### `--asm-operands`

- semantic intent: assembler operand variants;
- mode: `heuristic`;
- includes names containing `asmoperand`, `asm_operand`.

##### `--patterns`

- semantic intent: selection / matching pattern records;
- mode: `heuristic`;
- includes names containing `pattern`, `patfrag`, `pat`.

##### `--intrinsics`

- semantic intent: intrinsic-related records in target scope;
- mode: `heuristic`;
- includes names containing `intrinsic`.

##### `--scheduling`

- semantic intent: scheduling model entities;
- mode: `heuristic`;
- includes names containing `sched`, `schedule`, `schedmodel`, `schedread`, `schedwrite`.

##### `--itineraries`

- semantic intent: itinerary modeling entities;
- mode: `heuristic`;
- includes names containing `itin`, `itinerary`.

##### `--processors`

- semantic intent: processor/CPU model entities;
- mode: `heuristic`;
- includes names containing `processor`, `cpu`, `proc`.

##### `--features`

- semantic intent: subtarget feature entities;
- mode: `heuristic`;
- includes names containing `feature`, `subtargetfeature`.

##### `--subtargets`

- semantic intent: subtarget modeling entities;
- mode: `heuristic`;
- includes names containing `subtarget`.

##### `--encodings`

- semantic intent: encoding-related entities;
- mode: `heuristic`;
- includes names containing `encoding`, `enc`.

##### `--pseudo-instructions`

- semantic intent: pseudo instruction entities;
- mode: `heuristic`;
- includes names containing `pseudo`.

##### `--aliases`

- semantic intent: instruction aliases;
- mode: `heuristic`;
- includes names containing `alias`, `instalias`.

##### `--formats`

- semantic intent: instruction/record format groupings;
- mode: `heuristic`;
- includes names containing `format`, `frm`.

##### `--dag-patterns`

- semantic intent: DAG fragments and DAG pattern entities;
- mode: `heuristic`;
- includes names containing `dag`, `patfrag`, `pattern`.

##### `--types`

- semantic intent: type modeling entities;
- mode: `heuristic`;
- includes names containing `type`, `valuetype`, `vt`.

##### `--classes`

- semantic intent: raw TableGen `class` declarations;
- mode: `structural` (AST node extraction);
- records contain: `file`, `line`, `name`.

##### `--defs`

- semantic intent: raw TableGen `def` declarations;
- mode: `structural`;
- records contain: `file`, `line`, `name`.

##### `--defms`

- semantic intent: raw TableGen `defm` declarations;
- mode: `structural`;
- records contain: `file`, `line`, `name`.

##### `--multiclasses`

- semantic intent: raw TableGen `multiclass` declarations;
- mode: `structural`;
- records contain: `file`, `line`, `name`.

##### `--includes`

- semantic intent: raw TableGen `include` directives;
- mode: `structural`;
- records contain: `file`, `line`, `value`.

#### `--arch` and category execution

- `--arch ARCH|ALL` selects target backend scope;
- default is `AArch64`;
- with `--arch ALL`, the JSON includes one result object per canonical architecture;
- categories are executed per selected architecture with identical flag set.

#### Validation rules

- no category flags and no `--all` -> command exits with error;
- unknown architecture in `--arch` -> argument validation error;
- missing architecture directory -> error recorded for that architecture result.

#### Output shape (scrape command)

```json
{
  "command": "scrape",
  "requested_arch": "AArch64",
  "selected_categories": ["instructions", "opcodes"],
  "results": {
    "AArch64": {
      "architecture": "AArch64",
      "source_root": ".../LLVM-Targets/AArch64",
      "tablegen_summary": {"td_files": 52},
      "selected_categories": ["instructions", "opcodes"],
      "categories": {
        "instructions": {"implemented": true, "mode": "heuristic", "count": 0, "records": []},
        "opcodes": {"implemented": true, "mode": "heuristic", "count": 0, "records": []}
      }
    }
  }
}
```

---

## 6) Global Option: `--llvm-root`

All commands share:

- `--llvm-root <PATH>` (default: `LLVM-Targets`)

Resolution rules:

- absolute path remains absolute;
- relative path resolves against repository root computed from `scrapers/cli.py` location.

Recommended usage:

```bash
python3 -m scrapers --llvm-root LLVM-Targets arch verify
python3 -m scrapers --llvm-root /data/llvm/lib/Target td smoke --all-found
```

---

## 7) TableGen Scraper Semantics

### 7.1 Parse target

Input set for a selected architecture:

- `LLVM-Targets/<ARCH>/**/*.td`

### 7.2 Extracted constructs

From Tree-Sitter TableGen AST:

- `include`
- `class`
- `def`
- `defm`
- `multiclass`

### 7.3 Per-file error policy

For each file:

- read failure -> `errors += ["read_error: ..."]`
- parse exception -> `errors += ["parse_exception: ..."]`
- syntax recovery (`root.has_error`) -> `parse_error = true`, extraction still continues

No hard stop on individual file failures.

### 7.4 Output determinism

Determinism sources:

- file iteration uses sorted path list;
- JSON output uses `sort_keys=True` and fixed indentation;
- stable summary field names/order in writer code.

### 7.5 Output structure

Top-level JSON shape:

```json
{
  "architecture": "X86",
  "source_root": ".../LLVM-Targets/X86",
  "summary": {
    "td_files": 62,
    "files_with_io_or_parse_exception": 0,
    "files_with_tree_sitter_parse_error_nodes": 0,
    "total_includes": 123,
    "total_classes": 456,
    "total_defs": 789,
    "total_defms": 101,
    "total_multiclasses": 112
  },
  "files": [
    {
      "file": ".../SomeFile.td",
      "parse_error": false,
      "includes": [{"line": 1, "value": "X.td"}],
      "classes": [{"line": 10, "name": "Foo"}],
      "defs": [{"line": 20, "name": "Bar"}],
      "defms": [{"line": 30, "name": "Baz"}],
      "multiclasses": [{"line": 40, "name": "Qux"}],
      "errors": []
    }
  ]
}
```

---

## 8) C++ Scraper Semantics

### 8.1 Parse target

Input set for selected architecture:

- `LLVM-Targets/<ARCH>/**/*.cpp`

### 8.2 Extracted constructs

From Tree-Sitter C++ AST:

- function definitions with names prefixed by `LLVMInitialize`;
- call expressions containing `TargetRegistry::RegisterTarget`;
- declarations containing `RegisterTarget<`.

### 8.3 Parse-error handling

Per file:

- read and parse exceptions recorded in `errors`;
- `parse_error` set from `root.has_error`;
- extraction still proceeds on recoverable parses.

### 8.4 Output structure

Top-level JSON shape:

```json
{
  "architecture": "AArch64",
  "source_root": ".../LLVM-Targets/AArch64",
  "summary": {
    "cpp_files": 81,
    "files_with_io_or_parse_exception": 0,
    "files_with_tree_sitter_parse_error_nodes": 53,
    "total_init_functions": 6,
    "total_target_registry_calls": 2,
    "total_register_target_declarations": 3
  },
  "files": [
    {
      "file": ".../AArch64TargetMachine.cpp",
      "parse_error": false,
      "init_functions": [{"line": 42, "name": "LLVMInitializeAArch64Target"}],
      "target_registry_calls": [{"line": 99, "snippet": "TargetRegistry::RegisterTarget..."}],
      "register_target_declarations": [{"line": 101, "snippet": "RegisterTarget<...>"}],
      "errors": []
    }
  ]
}
```

---

## 9) CLI Output Formats

### 9.1 Table mode (`--format table`)

Smoke commands emit tabular rows plus summary.

TD smoke columns:

- `arch`
- `status`
- `td_files`
- `parse_error_files`
- `io_or_parse_exceptions`

CPP smoke columns:

- `arch`
- `status`
- `cpp_files`
- `parse_error_files`
- `io_or_parse_exceptions`

### 9.2 JSON mode (`--format json`)

Smoke command payload:

```json
{
  "total": 1,
  "ok": 1,
  "failed": 0,
  "rows": [
    {
      "architecture": "AArch64",
      "status": "OK",
      "td_files": 52,
      "parse_error_files": 0,
      "io_or_parse_exceptions": 0
    }
  ]
}
```

Failure row shape:

```json
{
  "architecture": "<ARCH>",
  "status": "FAIL",
  "error": "<stderr/stdout or shape error>"
}
```

---

## 10) Exit Codes

Common conventions in current implementation:

- `0`: success
- `1`: logical check/smoke failure (for example missing architecture in verify, smoke failures)
- `2`: invalid root path or missing scraper script path
- subprocess return code passthrough for `td run` / `cpp run`

---

## 11) Typical Workflows

### 11.1 Environment sanity check

```bash
python3 -m scrapers arch verify
python3 -m scrapers arch scan --format json
```

### 11.2 Generate one architecture TD inventory

```bash
python3 -m scrapers td run --arch RISCV
cat TD-Scrape/RISCV/td_inventory.json | head
```

### 11.3 Generate one architecture C++ inventory

```bash
python3 -m scrapers cpp run --arch AArch64
cat TD-Scrape/AArch64/cpp_inventory.json | head
```

### 11.4 Full TD sweep over canonical set

```bash
python3 -m scrapers td smoke --all --output-dir /tmp/td-sweep --format table
```

### 11.5 Sweep only architectures present in a custom source root

```bash
python3 -m scrapers --llvm-root /path/to/LLVM-Targets td smoke --all-found --format json
python3 -m scrapers --llvm-root /path/to/LLVM-Targets cpp smoke --all-found --format json
```

### 11.6 Alias entrypoint equivalence check

```bash
python3 -m TD-Scrapers td smoke --arch X86
python3 -m TD-Scrapers cpp smoke --arch RISCV
```

---

## 12) Direct Script Usage (Without CLI)

### 12.1 TableGen wrappers

```bash
python3 TD-Scrape/AArch64/scrape_td.py
python3 TD-Scrape/RISCV/scrape_td.py --output /tmp/riscv_td.json
python3 TD-Scrape/X86/scrape_td.py --arch X86 --llvm-root LLVM-Targets
```

### 12.2 C++ scraper

```bash
python3 TD-Scrape/AArch64/scrape_cpp.py
python3 TD-Scrape/AArch64/scrape_cpp.py --arch RISCV --output /tmp/riscv_cpp.json
```

### 12.3 Stdout output

Both scrapers support `--output -` for stdout JSON.

---

## 13) Internal Design Notes

### 13.1 Why shared TD core

`TD-Scrape/_common/td_scrape_core.py` deduplicates identical logic for:

- parser setup;
- AST walk;
- extraction and summary;
- JSON rendering.

Per-architecture scripts remain thin wrappers with architecture-specific defaults.

### 13.2 Why CLI dispatches through one TD and one CPP script

Current CLI uses:

- `TD-Scrape/AArch64/scrape_td.py` as generic TD entry script;
- `TD-Scrape/AArch64/scrape_cpp.py` as generic CPP entry script.

Both accept `--arch`, allowing one command path for all architectures.

---

## 14) Robustness and Failure Modes

### 14.1 Known benign parse-noise behavior

- Tree-Sitter may mark `parse_error=true` for some files while still yielding useful partial nodes.
- This is expected and reported as metric, not fatal failure.

### 14.2 Common operational failures

1) `llvm root not found`

- Cause: wrong `--llvm-root`
- Fix: pass absolute path or run from repo root

2) `scraper script not found`

- Cause: missing `TD-Scrape/.../scrape_*.py`
- Fix: restore scripts; verify repository checkout

3) `invalid_json_or_shape`

- Cause: generated JSON truncated/invalid or schema changed unexpectedly
- Fix: rerun single architecture with `run`; inspect generated file

4) empty or near-empty extraction

- Cause: architecture has few matching source files or sparse declarations
- Fix: inspect actual source tree; this may be valid

---

## 15) Validation Recipes

### 15.1 Determinism check

```bash
python3 -m scrapers td run --arch X86 --output /tmp/x86_a.json
python3 -m scrapers td run --arch X86 --output /tmp/x86_b.json
sha256sum /tmp/x86_a.json /tmp/x86_b.json
```

### 15.2 Shape check with Python

```bash
python3 - <<'PY'
import json
p='TD-Scrape/X86/td_inventory.json'
d=json.load(open(p))
assert 'summary' in d
assert d['summary']['td_files'] == len(d['files'])
print('ok')
PY
```

### 15.3 Help coverage check

```bash
python3 -m scrapers -h
python3 -m scrapers arch -h
python3 -m scrapers td -h
python3 -m scrapers td run -h
python3 -m scrapers td smoke -h
python3 -m scrapers cpp -h
python3 -m scrapers cpp run -h
python3 -m scrapers cpp smoke -h
```

---

## 16) Extending the Workspace

### 16.1 Add TD wrapper for another architecture

Pattern:

1. Create `TD-Scrape/<Arch>/scrape_td.py`.
2. Add thin wrapper importing `run_td_scrape` from `_common`.
3. Set defaults:
   - `default_arch="<Arch>"`
   - `default_output="TD-Scrape/<Arch>/td_inventory.json"`

Minimal wrapper template:

```python
#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common.td_scrape_core import run_td_scrape


def main():
    run_td_scrape(default_arch="<Arch>", default_output="TD-Scrape/<Arch>/td_inventory.json")


if __name__ == "__main__":
    main()
```

### 16.2 Add richer extractors safely

Guidelines:

- prefer AST node types over regex for syntax structure;
- keep output additive (new keys), avoid breaking existing keys;
- preserve deterministic sorting and JSON formatting;
- continue on per-file errors; record failures in `errors`.

### 16.3 Add new CLI command families

Recommended steps:

1. Add handler function in `scrapers/cli.py`.
2. Add parser/subparser wiring in `build_parser()`.
3. Provide `--format table|json` for machine-friendly output.
4. Ensure command has `-h/--help` at every depth.

---

## 17) Data Consumers

Consumers should treat JSON as versionless-but-stable in current state.

Defensive consumption recommendations:

- check key presence before strict access;
- tolerate unknown additional keys;
- use `summary` as quick metrics;
- use `files[]` for traceability and per-file diagnostics.

---

## 18) Security and Safety Notes

- Scrapers are read-only with respect to `LLVM-Targets`.
- Outputs are explicit (`--output` or default under `TD-Scrape/<Arch>/`).
- Smoke output dirs are explicit and created with `mkdir(parents=True, exist_ok=True)`.
- No network usage required.

---

## 19) Quick Command Reference

```bash
# entrypoints
python3 -m scrapers -h
python3 -m TD-Scrapers -h

# architecture inventory
python3 -m scrapers arch list
python3 -m scrapers arch scan
python3 -m scrapers arch scan --include-noncanonical --format json
python3 -m scrapers arch verify

# td scraping
python3 -m scrapers td run --arch X86
python3 -m scrapers td run --arch RISCV --output /tmp/riscv_td.json
python3 -m scrapers td smoke --arch AArch64
python3 -m scrapers td smoke --all
python3 -m scrapers td smoke --all-found --format json

# cpp scraping
python3 -m scrapers cpp run --arch AArch64
python3 -m scrapers cpp run --arch RISCV --output /tmp/riscv_cpp.json
python3 -m scrapers cpp smoke --arch AArch64
python3 -m scrapers cpp smoke --all-found --format json
```

---

## 20) Current Limitations

- TD wrappers exist for `AArch64`, `RISCV`, `X86`; CLI still supports all 25 through `--arch` dispatch.
- C++ scraping logic currently targets registration-relevant patterns only.
- C++ parse-error counts can be high in some architectures; this is reported but non-fatal.
- Output formats are currently JSON-focused for structured extraction.

---

## 21) Maintenance Checklist

When changing scraper behavior:

1. Run help checks for both entrypoints.
2. Run `arch verify`.
3. Run at least one `td run` and one `cpp run`.
4. Run one smoke command per family.
5. Confirm output files are valid JSON.
6. Update this `GUIDE.md` and `TD-Scrape/README.md` when command surface or schema changes.
