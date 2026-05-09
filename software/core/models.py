"""Shared models for calculator operations and feedback."""

from __future__ import annotations

from dataclasses import dataclass


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

    @classmethod
    def success(
        cls,
        expression: str,
        value: float | tuple[float, float],
        display: str,
    ) -> "CalculationResult":
        return cls(ok=True, expression=expression, value=value, display=display)

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
