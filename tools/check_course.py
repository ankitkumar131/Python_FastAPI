"""Read-only checks for course navigation, Python syntax and printed example drift.

Run: python tools/check_course.py (from any working directory).
This does not claim runtime verification for every illustrative snippet.
"""
from pathlib import Path
import ast
import re
import textwrap
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "notes"
errors = []
files = sorted(NOTES.glob("[0-9][0-9]-*.md"))
expected = [f"{index:02d}" for index in range(25)]
if [path.name[:2] for path in files] != expected:
    errors.append("Expected one sequential chapter for every number 00 through 24")
blocks = 0
printed = 0
for path in files:
    text = path.read_text(encoding="utf-8")
    if text.count("```") % 2:
        errors.append(f"{path.name}: unbalanced code fences")
    prose = re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.S)
    for link in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", prose):
        if "://" in link or link.startswith(("#", "mailto:")):
            continue
        target = unquote(link.split("#", 1)[0])
        if not (path.parent / target).exists():
            errors.append(f"{path.name}: missing local link {link}")
    for number, match in enumerate(re.finditer(r"```python\n(.*?)```", text, re.S), 1):
        blocks += 1
        try:
            ast.parse(textwrap.dedent(match.group(1)))
        except SyntaxError as error:
            errors.append(f"{path.name}: Python block {number}: {error}")
    for match in re.finditer(r"### File: `([^`]+\.py)`\s*\n\s*```python\n(.*?)```", text, re.S):
        name, code = match.groups()
        target = ROOT / name
        if not target.exists():
            errors.append(f"{path.name}: missing complete runnable file {name}")
        elif target.read_text().strip() != code.strip():
            errors.append(f"{path.name}: printed code differs from {name}")
        printed += 1
for path in list((ROOT / "examples").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")):
    try:
        ast.parse(path.read_text())
    except SyntaxError as error:
        errors.append(f"{path.relative_to(ROOT)}: {error}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"OK: {len(files)} sequential chapters, local links, {blocks} Python blocks, {printed} printed files, and example/test syntax")
