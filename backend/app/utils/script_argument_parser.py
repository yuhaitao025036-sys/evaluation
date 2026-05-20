"""Static argparse argument extraction for evaluation scripts."""
import ast
from pathlib import Path
from typing import Any, Dict, List, Optional

SYSTEM_ARGUMENTS = {
    "--instance-id",
    "--instance-data-path",
    "--dataset-id",
    "--dataset-name",
    "--dataset-path",
    "--output-dir",
    "--model",
    "--tag",
}

HIDDEN_ARGUMENTS = {
    "--external-root",
    "--scripts-dir",
    "--in-container",
    "--no-in-container",
    "--use-local-docker",
    "--no-use-local-docker",
    "--keep-external-output",
    "--enable-eval",
    "--no-enable-eval",
    "--dockerhub-username",
    "--docker-platform",
    "--use-tmux",
    "--conda-env",
    "--anthropic-model",
    "--anthropic-base-url",
    "--anthropic-auth-token",
}


def parse_script_arguments(script_path: Path) -> List[Dict[str, Any]]:
    try:
        tree = ast.parse(script_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    arguments = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_add_argument_call(node):
            continue

        argument = _parse_add_argument(node)
        if argument and argument["cli_name"] not in SYSTEM_ARGUMENTS and argument["cli_name"] not in HIDDEN_ARGUMENTS:
            arguments.append(argument)

    return arguments


def _is_add_argument_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"


def _parse_add_argument(node: ast.Call) -> Optional[Dict[str, Any]]:
    option_names = [_literal(arg) for arg in node.args]
    option_names = [name for name in option_names if isinstance(name, str)]
    cli_name = next((name for name in option_names if name.startswith("--")), None)
    if not cli_name:
        return None

    kwargs = {
        kw.arg: _literal(kw.value)
        for kw in node.keywords
        if kw.arg is not None
    }
    action = kwargs.get("action")
    arg_type = _argument_type(kwargs.get("type"), action, kwargs.get("choices"))
    default = kwargs.get("default")
    if action == "store_true" and default is None:
        default = False
    elif action == "store_false" and default is None:
        default = True

    return {
        "name": cli_name[2:],
        "cli_name": cli_name,
        "type": arg_type,
        "required": bool(kwargs.get("required", False)),
        "default": default,
        "help": kwargs.get("help"),
        "choices": kwargs.get("choices"),
        "action": action,
    }


def _argument_type(type_value: Any, action: Any, choices: Any) -> str:
    if action in {"store_true", "store_false"}:
        return "boolean"
    if choices:
        return "choice"
    if type_value in {"int", int}:
        return "int"
    if type_value in {"float", float}:
        return "float"
    return "string"


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [_literal(item) for item in node.elts]
        return values if isinstance(node, ast.List) else tuple(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _literal(node.operand)
        if isinstance(value, (int, float)):
            return -value
    return None
