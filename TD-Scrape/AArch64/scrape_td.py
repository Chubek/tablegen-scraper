#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common.td_scrape_core import run_td_scrape


def main():
    run_td_scrape(default_arch="AArch64", default_output="TD-Scrape/AArch64/td_inventory.json")


if __name__ == "__main__":
    main()
