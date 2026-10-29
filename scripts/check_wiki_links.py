"""Comprueba los enlaces de la wiki (frontend/wiki/<idioma>/): artículos, anclas e imágenes.

    python3 scripts/check_wiki_links.py      → lista lo roto y sale con 1 si hay algo
"""
import re
import sys
import unicodedata
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent / "frontend" / "wiki"
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")


def slugify(text: str) -> str:
    # Igual que slugify() de frontend/src/lib/wiki.ts (sobre el texto ya pintado del título).
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_]", "", text)
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s-]", "", text).strip()
    return re.sub(r"\s+", "-", text)


def anchors(path: Path) -> set[str]:
    out, fence = set(), False
    for line in path.read_text().splitlines():
        if line.startswith("```"):
            fence = not fence
        elif not fence and re.match(r"#{2,4} ", line):
            out.add(slugify(line.lstrip("#").strip()))
    return out


def main() -> int:
    errors = []
    langs = sorted(p for p in WIKI.iterdir() if p.is_dir() and p.name != "img")
    slugs = {lang.name: {p.stem for p in lang.glob("*.md")} for lang in langs}
    for lang in langs:
        others = [s for name, s in slugs.items() if name != lang.name]
        for missing in sorted(set().union(*others) - slugs[lang.name]) if others else []:
            errors.append(f"{lang.name}/: missing {missing}.md")
        for md in sorted(lang.glob("*.md")):
            text = re.sub(r"`[^`\n]*`", "", re.sub(r"```.*?```", "", md.read_text(), flags=re.S))
            for target in LINK.findall(text):
                if re.match(r"(https?:|mailto:)", target):
                    continue
                file, _, anchor = target.partition("#")
                dest = (md.parent / file).resolve() if file else md
                if not dest.exists():
                    errors.append(f"{lang.name}/{md.name}: not found {target}")
                elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
                    errors.append(f"{lang.name}/{md.name}: missing heading {target}")
    print("\n".join(errors) or "✔ Wiki links OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
