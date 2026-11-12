"""Bounded trusted-local JSON and path operations; no executable model loading."""
import json
from pathlib import Path


def relative_file(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or len(name) > 240 or ":" in name or "\\" in name:
        raise ValueError("invalid local relative path")
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("path traversal rejected")
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("symlink escapes local root")
    return result


def parse_json(text: str):
    depth=0; quoted=False; escaped=False
    for char in text:
        if quoted:
            if escaped: escaped=False
            elif char=="\\": escaped=True
            elif char=='"': quoted=False
        elif char=='"': quoted=True
        elif char in "[{":
            depth+=1
            if depth>64: raise ValueError("JSON nesting exceeds 64-level metadata budget")
        elif char in "]}": depth-=1
    try:
        return json.loads(text, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds parser budget") from exc


def read_json(path: Path, limit=5_000_000):
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("JSON missing/oversized")
    return parse_json(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    content = json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    stream=path.open("x", encoding="utf-8")  # exclusive: existing user data never owned here
    try:
        with stream:
            stream.write(content)
    except BaseException:
        path.unlink(missing_ok=True)  # only the file exclusively created by this call
        raise
