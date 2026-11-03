"""Shared models for calculator operations and feedback."""

from __future__ import annotations

from dataclasses import dataclass

# Sentido de uma conversão de coordenadas que produziu um PAR de valores. A
# camada de voz escolhe por aqui a frase padronizada de cada sentido (PRD §5,
# "conversões de coordenadas") sem reinterpretar a expressão - o motor é que
# sabe qual conversão correu, e o front não deve adivinhar pela string (§8).
VALUE_KIND_RECTANGULAR = "rectangular"
VALUE_KIND_POLAR = "polar"


@dataclass(frozen=True)
class CalculationResult:
    """Result returned by the calculation engine."""

    ok: bool
    expression: str
    value: float | tuple[float, float] | None = None
    display: str = ""
    code: str | None = None
    message: str = ""
    priority: str = "P2"
    # None para resultados escalares; um dos VALUE_KIND_* quando `value` é par.
    value_kind: str | None = None

    @classmethod
    def success(
        cls,
        expression: str,
        value: float | tuple[float, float],
        display: str,
        value_kind: str | None = None,
    ) -> "CalculationResult":
        return cls(
            ok=True,
            expression=expression,
            value=value,
            display=display,
            value_kind=value_kind,
        )

    @classmethod
    def error(
        cls,
        expression: str,
        code: str,
        message: str,
        priority: str = "P1",
    ) -> "CalculationResult":
        return cls(
            ok=False,
            expression=expression,
            display=f"{code}: {message}",
            code=code,
            message=message,
            priority=priority,
        )
