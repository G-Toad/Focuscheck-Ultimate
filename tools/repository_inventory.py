"""Build a deterministic static inventory of repository risk surfaces."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "refurbishment" / "repository-inventory.json"
SKIP_PARTS = {".git", "__pycache__", "_archive", "_verify_runtime", "_qa_runtime", "_build"}
REQUIRED_CATEGORIES = {
    "tk_after", "threads", "subprocess", "ctypes", "file_writes", "exception_swallowing",
    "process_exit", "settings", "sql", "user_text_logging", "environment", "feature_gates",
    "dialogs",
}


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except AttributeError:
        return getattr(node, "id", "") or getattr(node, "attr", "")


def _constant_text(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


class InventoryVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, categories: dict[str, list[dict]]) -> None:
        self.path = _relative(path)
        self.categories = categories
        self.imports: list[str] = []
        self.entry_point = False

    def record(self, category: str, node: ast.AST, detail: str) -> None:
        self.categories[category].append({"file": self.path, "line": node.lineno, "detail": detail})

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.extend(alias.name for alias in node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = "." * node.level + (node.module or "")
        self.imports.append(module)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if isinstance(node.test, ast.Compare) and "__name__" in _name(node.test):
            self.entry_point = True
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None or _name(node.type) in {"Exception", "BaseException"}:
            self.record("exception_swallowing", node, _name(node.type) or "bare except")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        called = _name(node.func)
        lower = called.lower()
        if any(token in lower for token in (".after", ".after_idle", ".after_cancel")):
            self.record("tk_after", node, called)
        if any(token in lower for token in ("threading.thread", "threading.timer", ".thread(", ".timer(")):
            self.record("threads", node, called)
        if lower.startswith("subprocess.") or lower in {"os.system", "os.startfile"}:
            self.record("subprocess", node, called)
        if "ctypes" in lower or lower.startswith(("windll.", "windll", "wintypes.")):
            self.record("ctypes", node, called)
        if lower in {"open", "path.open", "path.write_text", "path.write_bytes", "os.replace", "os.rename", "shutil.copy", "shutil.copy2"}:
            self.record("file_writes", node, called)
        if lower in {"sys.exit", "os._exit", "builtins.exit", "exit", "quit"}:
            self.record("process_exit", node, called)
        if "getenv" in lower or lower.startswith("os.environ"):
            self.record("environment", node, called)
        if any(token in lower for token in ("settings", "load_settings", "save_settings")):
            self.record("settings", node, called)
        if lower.startswith("settings.") or lower.endswith(".feature_enabled") or "feature_gate" in lower:
            self.record("feature_gates", node, called)
        if any(token in lower for token in ("dialog", "toplevel", "messagebox", "tkinter.tk")):
            self.record("dialogs", node, called)
        if any(token in lower for token in ("logger.", "logging.", "log.", "print")) and any(
            token in _name(argument).lower() for argument in node.args for token in ("response", "title", "url", "text", "answer", "reason")
        ):
            self.record("user_text_logging", node, called)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in {"environ", "getenv"}:
            self.record("environment", node, _name(node))
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            text = node.value.strip().upper()
            if any(text.startswith(keyword) for keyword in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE ", "ALTER ", "PRAGMA ", "BEGIN ")):
                self.record("sql", node, node.value.splitlines()[0][:120])


def _python_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*.py")
        if not any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts)
    )


def build_inventory() -> dict:
    categories = {name: [] for name in sorted(REQUIRED_CATEGORIES)}
    files = []
    imports = []
    entry_points = []
    for path in _python_files():
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise ValueError(f"cannot parse {_relative(path)}: {exc}") from exc
        visitor = InventoryVisitor(path, categories)
        visitor.visit(tree)
        relative = _relative(path)
        files.append({"file": relative, "lines": len(source.splitlines()), "imports": sorted(visitor.imports)})
        imports.extend({"file": relative, "module": item} for item in visitor.imports)
        if visitor.entry_point:
            entry_points.append(relative)
    risk = []
    counts = {name: len(items) for name, items in categories.items()}
    for item in files:
        score = sum(1 for entries in categories.values() for entry in entries if entry["file"] == item["file"])
        risk.append({"file": item["file"], "lines": item["lines"], "risk_surface_count": score})
    return {
        "schema_version": 1,
        "generated_from": "current Python source via ast",
        "excluded_path_parts": sorted(SKIP_PARTS),
        "files": files,
        "entry_points": sorted(entry_points),
        "imports": sorted(imports, key=lambda item: (item["file"], item["module"])),
        "categories": categories,
        "counts": counts,
        "module_risk": sorted(risk, key=lambda item: (-item["risk_surface_count"], item["file"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = build_inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(payload["files"]), "counts": payload["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
