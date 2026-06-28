"""
export_memo.py — Export or import the memory vault for backup / caregiver handoff.
"""

import argparse
import os

from memory.vault import MemoryVault


def main():
    p = argparse.ArgumentParser(description="Export/import MEMO memory vault")
    sub = p.add_subparsers(dest="cmd", required=True)

    exp = sub.add_parser("export", help="Export vault to zip")
    exp.add_argument("--out", "-o", default="data/memory/vault_export.zip")

    imp = sub.add_parser("import", help="Import vault from zip")
    imp.add_argument("--file", "-f", required=True)

    name = sub.add_parser("set-name", help="Set user name for morning greetings")
    name.add_argument("user_name")

    args = p.parse_args()
    vault = MemoryVault()

    if args.cmd == "export":
        vault.export_vault(args.out)
        print(f"Exported to {args.out}")
    elif args.cmd == "import":
        vault.import_vault(args.file)
        print(f"Imported from {args.file}")
    elif args.cmd == "set-name":
        vault.user_name = args.user_name
        print(f"User name set to: {args.user_name}")


if __name__ == "__main__":
    main()
