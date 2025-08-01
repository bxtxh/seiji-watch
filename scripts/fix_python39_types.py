#!/usr/bin/env python3
"""Fix Python 3.10+ type annotations for Python 3.9 compatibility."""

import os
import re
from pathlib import Path


def fix_type_annotations(file_path):
    """Fix type annotations in a single Python file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Fix union types (str | None -> Optional[str])
    # Match: word | None
    content = re.sub(r"\b(\w+)\s*\|\s*None\b", r"Optional[\1]", content)

    # Fix list types (list[str] | None -> Optional[List[str]])
    content = re.sub(
        r"\blist\[([^\]]+)\]\s*\|\s*None\b", r"Optional[List[\1]]", content
    )

    # Fix dict types (dict[str, Any] | None -> Optional[Dict[str, Any]])
    content = re.sub(
        r"\bdict\[([^\]]+)\]\s*\|\s*None\b", r"Optional[Dict[\1]]", content
    )

    # Fix standalone list[T] -> List[T]
    content = re.sub(r"\blist\[", "List[", content)

    # Fix standalone dict[K, V] -> Dict[K, V]
    content = re.sub(r"\bdict\[", "Dict[", content)

    # Fix return type annotations (-> type | None)
    content = re.sub(r"->\s*(\w+)\s*\|\s*None\b", r"-> Optional[\1]", content)

    # Add imports if needed
    if "Optional[" in content or "List[" in content or "Dict[" in content:
        # Check if typing imports exist
        import_match = re.search(r"^from typing import (.*)$", content, re.MULTILINE)

        needed_imports = set()
        if "Optional[" in content:
            needed_imports.add("Optional")
        if "List[" in content:
            needed_imports.add("List")
        if "Dict[" in content:
            needed_imports.add("Dict")

        if import_match:
            # Parse existing imports
            existing_imports = [imp.strip() for imp in import_match.group(1).split(",")]

            # Add missing imports
            for imp in needed_imports:
                if imp not in existing_imports:
                    existing_imports.append(imp)

            # Sort imports
            existing_imports.sort()

            # Replace import line
            new_import_line = f"from typing import {', '.join(existing_imports)}"
            content = re.sub(
                r"^from typing import .*$", new_import_line, content, flags=re.MULTILINE
            )
        else:
            # No typing import exists, add one
            imports_to_add = sorted(list(needed_imports))
            import_line = f"from typing import {', '.join(imports_to_add)}\n"

            # Try to add after other imports
            if "import " in content:
                # Find the last import
                import_lines = []
                for i, line in enumerate(content.split("\n")):
                    if line.startswith("import ") or line.startswith("from "):
                        import_lines.append(i)

                if import_lines:
                    lines = content.split("\n")
                    insert_pos = import_lines[-1] + 1
                    lines.insert(insert_pos, import_line.rstrip())
                    content = "\n".join(lines)
            else:
                # Add at the beginning after docstring/comments
                lines = content.split("\n")
                insert_pos = 0
                for i, line in enumerate(lines):
                    if (
                        line.strip()
                        and not line.startswith("#")
                        and not line.startswith('"""')
                        and not line.startswith("'''")
                    ):
                        insert_pos = i
                        break
                lines.insert(insert_pos, import_line.rstrip())
                content = "\n".join(lines)

    # Only write if changed
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def process_directory(directory_path, prefix=""):
    """Process all Python files in a directory."""
    fixed_files = []

    for py_file in Path(directory_path).glob("*.py"):
        if py_file.name == "__pycache__":
            continue

        print(f"{prefix}Processing {py_file.name}...", end="")
        if fix_type_annotations(py_file):
            fixed_files.append(py_file)
            print(" FIXED")
        else:
            print(" OK")

    return fixed_files


def main():
    """Fix type annotations in all shared files."""
    shared_base_dir = Path("/Users/shogen/KIRO/seiji-watch/shared/src/shared")

    if not shared_base_dir.exists():
        print(f"Directory not found: {shared_base_dir}")
        return

    all_fixed_files = []

    # Process different directories
    directories = [
        shared_base_dir / "models",
        shared_base_dir / "types",
        shared_base_dir / "clients",
        shared_base_dir / "database",
        shared_base_dir / "utils",
    ]

    for directory in directories:
        if directory.exists():
            print(f"\nProcessing {directory.name} directory:")
            fixed_files = process_directory(directory, "  ")
            all_fixed_files.extend(fixed_files)

    print(f"\n\nTotal fixed {len(all_fixed_files)} files:")
    for f in all_fixed_files:
        print(f"  - {f.relative_to(shared_base_dir)}")


if __name__ == "__main__":
    main()
