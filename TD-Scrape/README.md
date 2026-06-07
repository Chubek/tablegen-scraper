# TD-Scrape

Architecture-only mirror workspace for target scrapers over `LLVM-Targets`.

Mirrored architecture directories:
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

Initial scraper:
- `AArch64/scrape_td.py`
  - Inputs: `LLVM-Targets/AArch64/**/*.td`
  - Parser: Tree-Sitter TableGen grammar (`tree_sitter_tablegen`)
  - Output: JSON inventory of `include`, `class`, `def`, `defm`, `multiclass` declarations
  - Default output path: `TD-Scrape/AArch64/td_inventory.json`
- `RISCV/scrape_td.py`
  - Inputs: `LLVM-Targets/RISCV/**/*.td`
  - Parser: Tree-Sitter TableGen grammar (`tree_sitter_tablegen`)
  - Output: JSON inventory of `include`, `class`, `def`, `defm`, `multiclass` declarations
  - Default output path: `TD-Scrape/RISCV/td_inventory.json`
- `X86/scrape_td.py`
  - Inputs: `LLVM-Targets/X86/**/*.td`
  - Parser: Tree-Sitter TableGen grammar (`tree_sitter_tablegen`)
  - Output: JSON inventory of `include`, `class`, `def`, `defm`, `multiclass` declarations
  - Default output path: `TD-Scrape/X86/td_inventory.json`
- `AArch64/scrape_cpp.py`
  - Inputs: `LLVM-Targets/AArch64/**/*.cpp`
  - Parser: Tree-Sitter C++ grammar (`tree_sitter_cpp`)
  - Output: JSON inventory of init functions (`LLVMInitialize*`), `TargetRegistry::RegisterTarget(...)` calls, and `RegisterTarget<...>` declarations
  - Default output path: `TD-Scrape/AArch64/cpp_inventory.json`

Example run:
- `python TD-Scrape/AArch64/scrape_td.py --llvm-root LLVM-Targets --arch AArch64 --output TD-Scrape/AArch64/td_inventory.json`
- `python TD-Scrape/RISCV/scrape_td.py --llvm-root LLVM-Targets --arch RISCV --output TD-Scrape/RISCV/td_inventory.json`
- `python TD-Scrape/X86/scrape_td.py --llvm-root LLVM-Targets --arch X86 --output TD-Scrape/X86/td_inventory.json`
- `python TD-Scrape/AArch64/scrape_cpp.py --llvm-root LLVM-Targets --arch AArch64 --output TD-Scrape/AArch64/cpp_inventory.json`
