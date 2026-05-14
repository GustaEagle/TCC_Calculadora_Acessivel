"""State machine shared by visual, keyboard, and audio interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field

from software.core.engine import CalculationEngine
from software.core.models import CalculationResult


@dataclass
class CalculatorState:
    """Current expression, last answer, and button handling rules."""

    engine: CalculationEngine = field(default_factory=CalculationEngine)
    expression: str = ""
    ans: float | None = None
    last_result: CalculationResult | None = None
    history: list[CalculationResult] = field(default_factory=list)
    angle_mode: str = "deg" # 'deg' or 'rad'

    def press(self, token: str) -> CalculationResult | None:
        if token == "AC":
            self.expression = ""
            self.last_result = None
            return None
        if token == "DEL":
            self.expression = self.expression[:-1]
            return None
        if token == "=":
            return self.evaluate()
        if token == "x^-1":
            self.expression = f"inv({self.expression})" if self.expression else "inv("
            return None
        if token == "RAD/DEG":
            self.angle_mode = "rad" if self.angle_mode == "deg" else "deg"
            self.engine.angle_mode = self.angle_mode
            return None

        self.expression += token
        return None

    def evaluate(self) -> CalculationResult:
        result = self.engine.evaluate(self.expression, self.ans)
        self.last_result = result
        self.history.append(result)
        if len(self.history) > 10: # Keep last 10
            self.history.pop(0)
            
        if result.ok and isinstance(result.value, float):
            self.ans = result.value
            self.expression = result.display
        return result
