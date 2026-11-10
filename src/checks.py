"""Проверка ограничений ЦАП: длины, имена, docstring и PEP8."""

import ast
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path


line_limit = 80
function_limit = 40
argument_limit = 7
file_limit = 1000
snake_case = re.compile(r"[a-z_][a-z0-9_]*\Z")
class_case = re.compile(r"[A-Z][A-Za-z0-9]*\Z")


def check_function(node: ast.FunctionDef) -> list[str]:
    """Проверить имя, документацию, размер и количество аргументов."""
    issues = []
    if not snake_case.fullmatch(node.name):
        issues.append("имя функции не в snake_case: " + node.name)
    if not ast.get_docstring(node):
        issues.append("нет docstring функции " + node.name)
    if node.end_lineno - node.lineno + 1 > function_limit:
        issues.append("функция длиннее 40 строк: " + node.name)
    arguments = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
    if len(arguments) > argument_limit:
        issues.append("больше 7 аргументов: " + node.name)
    return issues


def check_tree(tree: ast.Module) -> list[str]:
    """Проверить функции, классы и числовые литералы в сравнениях."""
    issues = []
    if not ast.get_docstring(tree):
        issues.append("нет docstring модуля")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            issues.extend(check_function(node))
        if isinstance(node, ast.ClassDef):
            valid_name = class_case.fullmatch(node.name)
            if not ast.get_docstring(node) or not valid_name:
                issues.append("неверное имя или нет docstring класса")
        if isinstance(node, ast.Compare):
            for value in [node.left] + node.comparators:
                if isinstance(value, ast.Constant):
                    if type(value.value) in (int, float):
                        issues.append("числовой литерал в сравнении")
    return issues


def check_file(path: Path) -> list[str]:
    """Проверить строки, комментарии и AST одного Python-файла."""
    source = path.read_text(encoding="utf-8")
    issues = check_tree(ast.parse(source))
    lines = source.splitlines()
    if len(lines) > file_limit:
        issues.append("файл длиннее 1000 строк")
    if any(len(line) > line_limit for line in lines):
        issues.append("строка длиннее 80 символов")
    if source and not source.endswith("\n"):
        issues.append("нет завершающего перевода строки")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            issues.append("комментарий вместо docstring")
    return [str(path) + ": " + issue for issue in issues]


def main() -> int:
    """Проверить исходники и тесты, затем запустить flake8."""
    root = Path(__file__).resolve().parent.parent
    problems = []
    for folder in ("src", "tests"):
        for path in (root / folder).rglob("*.py"):
            problems.extend(check_file(path))
    if problems:
        print("\n".join(problems))
        return 1
    result = subprocess.run(
        [sys.executable, "-B", "-m", "flake8", "src", "tests",
         "--max-line-length=80", "--max-complexity=10"], cwd=root,
    )
    if result.returncode:
        return result.returncode
    print("Оформление ЦАП и flake8: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
