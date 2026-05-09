"""Scientific calculation engine for the accessible calculator."""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Callable

from software.core.models import CalculationResult


class CalculationDomainError(ValueError):
    """Domain error tagged with the PRD error code."""

    def __init__(self, code: str, message: str, priority: str = "P1") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.priority = priority


class CalculationEngine:
    """Evaluate calculator expressions without depending on any UI toolkit."""

    def __init__(self, angle_mode: str = "deg") -> None:
        self.angle_mode = angle_mode

    def evaluate(self, expression: str, ans: float | None = None) -> CalculationResult:
        original = expression.strip()
        if not original:
            return CalculationResult.error(original, "ERR-008", "Expressao incompleta", "P2")

        try:
            normalized = self._normalize(original, ans)
            tree = ast.parse(normalized, mode="eval")
            value = self._eval_node(tree.body)
            display = self._format_value(value)
            return CalculationResult.success(original, value, display)
        except ZeroDivisionError:
            return CalculationResult.error(original, "ERR-001", "Divisao por zero")
        except CalculationDomainError as exc:
            return CalculationResult.error(original, exc.code, exc.message, exc.priority)
        except (SyntaxError, ValueError, TypeError, KeyError):
            return CalculationResult.error(original, "ERR-007", "Expressao invalida")
        except OverflowError:
            return CalculationResult.error(original, "ERR-006", "Resultado muito grande")

    def _normalize(self, expression: str, ans: float | None) -> str:
        text = expression
        text = text.replace("×", "*").replace("x", "*").replace("÷", "/")
        text = text.replace("^", "**").replace("√", "sqrt")
        text = text.replace("π", "pi")
        text = re.sub(r"\bsen\s*\(", "sin(", text, flags=re.IGNORECASE)
        text = re.sub(r"\bsen-1\s*\(", "asin(", text, flags=re.IGNORECASE)
        text = re.sub(r"\bcos-1\s*\(", "acos(", text, flags=re.IGNORECASE)
        text = re.sub(r"\btan-1\s*\(", "atan(", text, flags=re.IGNORECASE)
        text = re.sub(r"\bln\s*\(", "ln(", text, flags=re.IGNORECASE)
        text = re.sub(r"\bnCr\s*\(", "ncr(", text, flags=re.IGNORECASE)
        text = re.sub(r"\bnPr\s*\(", "npr(", text, flags=re.IGNORECASE)

        if re.search(r"\bAns\b", text, flags=re.IGNORECASE):
            if ans is None:
                raise CalculationDomainError("WRN-010", "Sem resposta anterior", "P2")
            text = re.sub(r"\bAns\b", str(ans), text, flags=re.IGNORECASE)

        text = self._replace_factorials(text)
        return text

    def _replace_factorials(self, text: str) -> str:
        # Handles common postfix factorial cases used by the on-screen keyboard.
        pattern = re.compile(r"(\b\d+(?:\.\d+)?\b|\bpi\b|\be\b|\([^()]*\))!", re.IGNORECASE)
        previous = None
        while previous != text:
            previous = text
            text = pattern.sub(r"fact(\1)", text)
        return text

    def _eval_node(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            return self._constants()[node.id]
        if isinstance(node, ast.UnaryOp):
            return self._eval_unary(node)
        if isinstance(node, ast.BinOp):
            return self._eval_binary(node)
        if isinstance(node, ast.Call):
            return self._eval_call(node)
        raise ValueError("Unsupported expression")

    def _eval_unary(self, node: ast.UnaryOp) -> float:
        operand = self._eval_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError("Unsupported unary operator")

    def _eval_binary(self, node: ast.BinOp) -> float:
        left = self._eval_node(node.left)
        right = self._eval_node(node.right)
        operators: dict[type[ast.operator], Callable[[float, float], float]] = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
        }
        operation = operators.get(type(node.op))
        if operation is None:
            raise ValueError("Unsupported binary operator")
        return operation(left, right)

    def _eval_call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Unsupported function")
        functions = self._functions()
        function = functions[node.func.id]
        args = [self._eval_node(arg) for arg in node.args]
        return function(*args)

    def _constants(self) -> dict[str, float]:
        return {"pi": math.pi, "e": math.e}

    def _functions(self) -> dict[str, Callable[..., float]]:
        return {
            "sin": lambda value: math.sin(self._angle_to_radians(value)),
            "cos": lambda value: math.cos(self._angle_to_radians(value)),
            "tan": self._tan,
            "asin": self._asin,
            "acos": self._acos,
            "atan": lambda value: self._angle_from_radians(math.atan(value)),
            "log": self._log10,
            "ln": self._ln,
            "sqrt": self._sqrt,
            "fact": self._factorial,
            "inv": self._inverse,
            "ncr": self._ncr,
            "npr": self._npr,
            "polar": self._polar_to_rect_x,
            "rect": self._rect_to_polar_radius,
        }

    def _angle_to_radians(self, value: float) -> float:
        if self.angle_mode == "deg":
            return math.radians(value)
        return value

    def _angle_from_radians(self, value: float) -> float:
        if self.angle_mode == "deg":
            return math.degrees(value)
        return value

    def _tan(self, value: float) -> float:
        radians = self._angle_to_radians(value)
        if math.isclose(math.cos(radians), 0.0, abs_tol=1e-12):
            raise CalculationDomainError("ERR-002", "Argumento invalido para a funcao")
        return math.tan(radians)

    def _asin(self, value: float) -> float:
        if value < -1 or value > 1:
            raise CalculationDomainError("ERR-003", "Valor fora do dominio")
        return self._angle_from_radians(math.asin(value))

    def _acos(self, value: float) -> float:
        if value < -1 or value > 1:
            raise CalculationDomainError("ERR-003", "Valor fora do dominio")
        return self._angle_from_radians(math.acos(value))

    def _log10(self, value: float) -> float:
        if value <= 0:
            raise CalculationDomainError("ERR-002", "Argumento invalido para a funcao")
        return math.log10(value)

    def _ln(self, value: float) -> float:
        if value <= 0:
            raise CalculationDomainError("ERR-002", "Argumento invalido para a funcao")
        return math.log(value)

    def _sqrt(self, value: float) -> float:
        if value < 0:
            raise CalculationDomainError("ERR-002", "Argumento invalido para a funcao")
        return math.sqrt(value)

    def _factorial(self, value: float) -> float:
        if value < 0 or not float(value).is_integer():
            raise CalculationDomainError("ERR-005", "Fatorial invalido")
        return float(math.factorial(int(value)))

    def _inverse(self, value: float) -> float:
        if value == 0:
            raise ZeroDivisionError
        return 1 / value

    def _ncr(self, n: float, r: float) -> float:
        n_int, r_int = self._validate_combinatorics(n, r)
        return float(math.comb(n_int, r_int))

    def _npr(self, n: float, r: float) -> float:
        n_int, r_int = self._validate_combinatorics(n, r)
        return float(math.perm(n_int, r_int))

    def _validate_combinatorics(self, n: float, r: float) -> tuple[int, int]:
        if n < 0 or r < 0 or n < r or not float(n).is_integer() or not float(r).is_integer():
            raise CalculationDomainError("ERR-004", "Combinacao ou permutacao invalida")
        return int(n), int(r)

    def _polar_to_rect_x(self, radius: float, angle: float) -> float:
        return radius * math.cos(self._angle_to_radians(angle))

    def _rect_to_polar_radius(self, x_value: float, y_value: float) -> float:
        return math.hypot(x_value, y_value)

    def _format_value(self, value: float | tuple[float, float]) -> str:
        if isinstance(value, tuple):
            return f"({value[0]:.10g}, {value[1]:.10g})"
        if math.isfinite(value) and float(value).is_integer():
            return str(int(value))
        return f"{value:.10g}"
