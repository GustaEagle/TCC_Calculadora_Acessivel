"""Scientific calculation engine for the accessible calculator."""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Callable

from software.core.models import (
    VALUE_KIND_POLAR,
    VALUE_KIND_RECTANGULAR,
    CalculationResult,
)


class CalculationDomainError(ValueError):
    """Domain error tagged with the PRD error code."""

    def __init__(self, code: str, message: str, priority: str = "P1") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.priority = priority


class CalculationEngine:
    """Evaluate calculator expressions without depending on any UI toolkit."""

    # Aridade de cada função chamável. Validada ANTES da invocação para que um
    # TypeError do Python ("takes 2 positional arguments but 1 was given") não
    # chegue ao TTS em inglês, e para distinguir entrada incompleta (ERR-008,
    # P2) de dados inválidos de conversão (ERR-009) e de sintaxe (ERR-007) -
    # ver PRD §13 e design.md §4.
    ARITY: dict[str, int] = {
        "sin": 1, "cos": 1, "tan": 1,
        "asin": 1, "acos": 1, "atan": 1,
        "log": 1, "ln": 1, "logbase": 2,
        "sqrt": 1, "fact": 1, "inv": 1, "exp": 1,
        "__ncr": 2, "__npr": 2,
        "polar": 2, "rect": 2,
    }

    # As conversões de coordenadas têm código de erro próprio no §13 (ERR-009)
    # quando recebem dados a mais; as outras funções caem no ERR-007.
    CONVERSIONS = frozenset({"polar", "rect"})

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
            # `original` (e não `normalized`): o fecho automático de parênteses
            # e a reescrita infixa são detalhes da avaliação e não devem
            # reescrever o que o utilizador vê na linha de cálculo.
            return CalculationResult.success(
                original, value, display, self._value_kind(tree.body)
            )
        except ZeroDivisionError:
            return CalculationResult.error(original, "ERR-001", "Divisao por zero")
        except CalculationDomainError as exc:
            return CalculationResult.error(original, exc.code, exc.message, exc.priority)
        except OverflowError:
            return CalculationResult.error(original, "ERR-006", "Resultado muito grande")
        except (SyntaxError, ValueError, TypeError, KeyError) as exc:
            # Distinguish between system/logic errors and true syntax/input errors
            msg = str(exc) if str(exc) else "Expressao invalida"
            return CalculationResult.error(original, "ERR-007", msg)

    def _normalize(self, expression: str, ans: float | None) -> str:
        text = expression.strip()
        
        # 0. Handle Ans (case insensitive)
        if ans is not None:
            text = re.sub(r"\bAns\b", str(ans), text, flags=re.IGNORECASE)

        # 0.1 Handle scientific tokens that contain characters used in basic arithmetic
        text = text.replace("x^-1", "inv").replace("X^-1", "inv")
        
        # 0.2 Replace math symbols (case insensitive)
        text = text.replace("×", "*").replace("÷", "/")
        text = re.sub(r"\bx\b", "*", text, flags=re.IGNORECASE)
        
        # 0.3 Replace trig and log functions (case insensitive)
        # Use regex to replace common function aliases to their canonical internal names
        replacements = {
            r"\bsen-1": "asin",
            r"\bsin-1": "asin",
            r"\bcos-1": "acos",
            r"\btan-1": "atan",
            r"\bsen\b": "sin",
            r"\blogbase\b": "logbase",
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            
        # Lowercase all remaining text to handle SIN/COS/LOG/PI/E
        text = text.lower()
        
        text = text.replace("^", "**")
        # 1. Handle √ followed by parentheses: √(64) -> sqrt(64)
        text = text.replace("√(", "sqrt(")
        # 2. Handle √ followed by number or constant: √64 -> sqrt(64)
        text = re.sub(r"√(\d+(?:\.\d+)?|pi|e)", r"sqrt(\1)", text)
        # 3. Fallback for any remaining √
        text = text.replace("√", "sqrt")
        
        text = text.replace("π", "pi")
        # Ensure 'inv' is a function call
        text = re.sub(r"\binv\s*\(", "inv(", text, flags=re.IGNORECASE)
        # Handle 'inv' as a property or trailing token: '2inv' -> 'inv(2)'
        text = re.sub(r"(\d+(?:\.\d+)?|pi|e|\))\s*inv\b", r"inv(\1)", text, flags=re.IGNORECASE)
        # Handle 'inv' followed by a number: 'inv2' -> 'inv(2)'
        text = re.sub(r"\binv(\d+(?:\.\d+)?|pi|e)", r"inv(\1)", text, flags=re.IGNORECASE)
        # If 'inv' stands alone, treat as 'inv(Ans)'
        if text.strip().lower() == "inv":
            if ans is None:
                raise CalculationDomainError("WRN-010", "Sem resposta anterior", "P2")
            text = f"inv({ans})"

        text = re.sub(r"\bsen\s*\(", "sin(", text, flags=re.IGNORECASE)
        text = re.sub(r"\bsen-1\s*\(", "asin(", text, flags=re.IGNORECASE)
        text = re.sub(r"\bcos-1\s*\(", "acos(", text, flags=re.IGNORECASE)
        text = re.sub(r"\btan-1\s*\(", "atan(", text, flags=re.IGNORECASE)
        text = re.sub(r"\bln\s*\(", "ln(", text, flags=re.IGNORECASE)
        text = re.sub(r"\blog(\d+)\s*\(", r"logbase(\1, ", text, flags=re.IGNORECASE)

        if re.search(r"\bAns\b", text, flags=re.IGNORECASE):
            if ans is None:
                raise CalculationDomainError("WRN-010", "Sem resposta anterior", "P2")
            text = re.sub(r"\bAns\b", str(ans), text, flags=re.IGNORECASE)

        text = self._replace_factorials(text)
        text = self._replace_percentages(text)
        
        # 4. Remove leading zeros from integers to prevent SyntaxError
        # e.g. '09' -> '9', but '0.9' remains '0.9'
        text = re.sub(r"(?<!\.)\b0+(\d+)", r"\1", text)

        # 4.1 Mantissa seguida da tecla EXP: "3 EXP 8" é 3x10^8, e no teclado a
        # tecla insere "exp(" logo após a mantissa, produzindo "3exp(8". Sem
        # esta multiplicação implícita o ast.parse recusaria "3exp(8)". Um
        # "exp(" que não venha depois de um número/grupo fica intacto e vale
        # 10^x sozinho.
        text = re.sub(r"(\d+(?:\.\d+)?|\)|\bpi\b|\be\b)\s*exp\(", r"\1*exp(", text)

        # 5. Fecho automático dos parênteses em falta. Corre AQUI, no fim,
        # porque _replace_factorials, _replace_percentages e a reescrita de
        # log2( -> logbase(2, injetam parênteses equilibrados: contá-los antes
        # daria um défice errado (design.md §1).
        text = self._close_parentheses(text)

        # 6. nCr/nPr infixos. Depende do passo 5: com os parênteses já
        # equilibrados, a procura dos operandos é um varrimento bem definido e
        # nunca encontra um grupo sem fecho (design.md §2).
        text = self._rewrite_infix_combinatorics(text)

        return text

    def _close_parentheses(self, text: str) -> str:
        """Fecha os parênteses em falta quando o défice é inequívoco.

        Numa calculadora física o utilizador pressiona "√", "1", "4", "4", "="
        e nunca pressiona o fecho: o fecho implícito é o caso NORMAL, não a
        exceção. Só é aplicado quando não existe fecho órfão - um ")" sem
        abertura não tem leitura única, e adivinhar seria pior que recusar, por
        isso o texto segue inalterado e o ast.parse produz o ERR-007 de sempre.

        Expressões de calculadora não têm literais de texto nem comentários,
        logo o varrimento de caracteres é exato: nenhum "(" é falso.
        """
        depth = 0
        for char in text:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    return text
        return text + ")" * depth

    def _rewrite_infix_combinatorics(self, text: str) -> str:
        """Reescreve "5 ncr 2" para a chamada interna "__ncr(5,2)".

        A notação é INFIXA (a tecla dá "nCr" entre os operandos, como numa
        calculadora científica); a forma funcional nCr(5,2) não é aceita. O
        alvo interno leva "__" porque o teclado não tem "_": assim o utilizador
        não consegue escrever a chamada diretamente, e qualquer "ncr"/"npr"
        que sobreviva a esta reescrita é entrada inválida.

        A guarda é "(?<![_a-z])...(?![_a-z])" e não "\\b": o utilizador pode
        escrever sem espaços ("5nCr2"), onde não há fronteira de palavra entre
        o dígito e o "n", mas a guarda tem de continuar a NÃO casar dentro de
        "__ncr" - senão o laço reescrevia o que já reescreveu.
        """
        for name, internal in (("ncr", "__ncr"), ("npr", "__npr")):
            while True:
                match = re.search(rf"(?<![_a-z]){name}(?![_a-z])", text)
                if match is None:
                    break
                left = self._atom_before(text, match.start())
                right = self._atom_after(text, match.end())
                if left is None or right is None:
                    # Sem operando à esquerda e seguido de "(": é a forma
                    # funcional nCr(5,2), que deixou de ser válida -> ERR-007.
                    if left is None and text[match.end():].lstrip().startswith("("):
                        raise CalculationDomainError("ERR-007", "Expressao invalida")
                    # Caso contrário é entrada truncada ("5 nCr") -> ERR-008.
                    raise CalculationDomainError("ERR-008", "Expressao incompleta", "P2")
                operand_left = text[left[0]:left[1]]
                operand_right = text[right[0]:right[1]]
                text = (
                    f"{text[:left[0]]}{internal}({operand_left},{operand_right})"
                    f"{text[right[1]:]}"
                )
        return text

    def _atom_before(self, text: str, end: int) -> tuple[int, int] | None:
        """Limites do átomo que termina antes de `end`, ou None se não houver.

        Um átomo é um número, uma constante, um grupo "(...)" equilibrado ou
        uma chamada de função - "sqrt(25)" é UM átomo, não "sqrt" e "(25)".
        O sinal fica de FORA: em "-5 ncr 2" o menos é o unário do resto do
        motor, logo o resultado é "-__ncr(5,2)" (design.md, questões abertas).
        """
        stop = end
        while stop > 0 and text[stop - 1].isspace():
            stop -= 1
        if stop == 0:
            return None

        if text[stop - 1] == ")":
            depth = 0
            index = stop
            while index > 0:
                index -= 1
                if text[index] == ")":
                    depth += 1
                elif text[index] == "(":
                    depth -= 1
                    if depth == 0:
                        break
            if depth != 0:
                return None
            # Identificador imediatamente antes do "(": é uma chamada.
            while index > 0 and (text[index - 1].isalnum() or text[index - 1] == "_"):
                index -= 1
            return index, stop

        index = stop
        while index > 0 and (text[index - 1].isalnum() or text[index - 1] in "._"):
            index -= 1
        if index == stop:
            return None
        return index, stop

    def _atom_after(self, text: str, start: int) -> tuple[int, int] | None:
        """Limites do átomo que começa em `start`, ou None se não houver.

        Aqui o sinal ENTRA no átomo: à direita de um operador infixo o "-" só
        pode ser unário, então "5 nCr -2" chega a __ncr(5,-2) e devolve o
        ERR-004 do domínio, em vez de parecer entrada truncada.
        """
        begin = start
        while begin < len(text) and text[begin].isspace():
            begin += 1
        if begin >= len(text):
            return None

        index = begin
        if text[index] in "+-":
            index += 1
            while index < len(text) and text[index].isspace():
                index += 1
            if index >= len(text):
                return None
        after_sign = index

        if text[index] != "(":
            while index < len(text) and (text[index].isalnum() or text[index] in "._"):
                index += 1
            if index == after_sign:
                return None
            if index >= len(text) or text[index] != "(":
                return begin, index

        depth = 0
        while index < len(text):
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
                if depth == 0:
                    return begin, index + 1
            index += 1
        return None

    def _replace_percentages(self, text: str) -> str:
        # Handles postfix percentage cases: 50% -> (50/100)
        pattern = re.compile(r"(\b\d+(?:\.\d+)?\b|\bpi\b|\be\b|\([^()]*\))%", re.IGNORECASE)
        previous = None
        while previous != text:
            previous = text
            text = pattern.sub(r"(\1/100)", text)
        return text

    def _replace_factorials(self, text: str) -> str:
        # Handles common postfix factorial cases used by the on-screen keyboard.
        pattern = re.compile(r"(\b\d+(?:\.\d+)?\b|\bpi\b|\be\b|\([^()]*\))!", re.IGNORECASE)
        previous = None
        while previous != text:
            previous = text
            text = pattern.sub(r"fact(\1)", text)
        return text

    def _value_kind(self, node: ast.AST) -> str | None:
        """Sentido da conversão de coordenadas, lido do nó de TOPO.

        É bem definido porque um par só é válido como expressão completa (ver
        _scalar): se existe par, a conversão é a raiz da árvore. Ler aqui, uma
        vez, evita que o front reinterprete a string da expressão (§8).
        """
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            # O sentido é o DESTINO da conversão (convenção Casio): polar()
            # produz um par polar, rect() produz um par retangular.
            if node.func.id == "polar":
                return VALUE_KIND_POLAR
            if node.func.id == "rect":
                return VALUE_KIND_RECTANGULAR
        return None

    def _scalar(self, value: float | tuple[float, float]) -> float:
        """Exige um escalar: um par só é válido como expressão COMPLETA.

        O catálogo do PRD §5 não define aritmética de pares, então usar uma
        conversão como operando é expressão inválida. Tem de ser recusado aqui
        explicitamente - sem isto, "polar(2,60)+1" sairia como um TypeError
        cru do Python em vez de um código do §13.
        """
        if isinstance(value, tuple):
            raise CalculationDomainError("ERR-007", "Expressao invalida")
        return value

    def _eval_node(self, node: ast.AST) -> float | tuple[float, float]:
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
        operand = self._scalar(self._eval_node(node.operand))
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError("Unsupported unary operator")

    def _eval_binary(self, node: ast.BinOp) -> float:
        left = self._scalar(self._eval_node(node.left))
        right = self._scalar(self._eval_node(node.right))
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

    def _eval_call(self, node: ast.Call) -> float | tuple[float, float]:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Unsupported function")
        functions = self._functions()
        name = node.func.id
        function = functions[name]
        self._validate_arity(name, len(node.args))
        args = [self._scalar(self._eval_node(arg)) for arg in node.args]
        return function(*args)

    def _validate_arity(self, name: str, given: int) -> None:
        """PRD §13: argumentos a menos é entrada INCOMPLETA, não inválida."""
        expected = self.ARITY[name]
        if given == expected:
            return
        if given < expected:
            # É o que acontece quando o fecho automático fecha uma chamada mais
            # cedo do que o utilizador pretendia: "polar(5" -> "polar(5)".
            raise CalculationDomainError("ERR-008", "Expressao incompleta", "P2")
        if name in self.CONVERSIONS:
            raise CalculationDomainError("ERR-009", "Dados invalidos para a conversao")
        raise CalculationDomainError("ERR-007", "Expressao invalida")

    def _constants(self) -> dict[str, float]:
        return {"pi": math.pi, "e": math.e}

    def _functions(self) -> dict[str, Callable[..., float | tuple[float, float]]]:
        return {
            "sin": lambda value: math.sin(self._angle_to_radians(value)),
            "cos": lambda value: math.cos(self._angle_to_radians(value)),
            "tan": self._tan,
            "asin": self._asin,
            "acos": self._acos,
            "atan": lambda value: self._angle_from_radians(math.atan(value)),
            "log": self._log10,
            "logbase": self._log_base,
            "ln": self._ln,
            "sqrt": self._sqrt,
            "fact": self._factorial,
            "inv": self._inverse,
            "exp": self._power_of_ten,
            # Alvos da reescrita infixa (_rewrite_infix_combinatorics): o "__"
            # é intencional, para o utilizador não poder chamá-los diretamente.
            "__ncr": self._ncr,
            "__npr": self._npr,
            # Convenção Casio: o token diz o DESTINO. polar( recebe (x,y) e
            # devolve (r,ângulo); rect( recebe (r,ângulo) e devolve (x,y).
            "polar": self._to_polar,
            "rect": self._to_rect,
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

    def _log_base(self, base: float, value: float) -> float:
        if value <= 0 or base <= 0 or base == 1:
            raise CalculationDomainError("ERR-002", "Argumento invalido para a funcao")
        return math.log(value, base)

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

    def _power_of_ten(self, value: float) -> float:
        """10 elevado a `value`: a tecla EXP de entrada em notação científica.

        No teclado de uma calculadora, "EXP" (ou "EE") NÃO é a exponencial de
        base e - é a entrada do expoente de base dez: "3 EXP 8" é 3x10^8. Por
        isso não acrescenta função ao catálogo do PRD §5: é notação de ENTRADA
        de número, e o e^x continua acessível por "e ^ x".

        Um expoente grande estoura em OverflowError, que o evaluate() já
        traduz para ERR-006 ("resultado muito grande").
        """
        return 10.0**value

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

    def _snap_to_zero(self, value: float) -> float:
        """Elimina o ruído de vírgula flutuante em torno do zero.

        sin(180°) dá 1.2246e-16, não 0, por causa da conversão graus ->
        radianos. Num escalar o _format_value já limpa isso; num PAR a limpeza
        tem de acontecer na ORIGEM, para que o valor, o texto da tela e a fala
        digam todos "0" - senão a voz leria "1 ponto 2 2 4 ... e menos 16".
        """
        return 0.0 if abs(value) < 1e-12 else value

    def _to_polar(self, x_value: float, y_value: float) -> tuple[float, float]:
        """Pol(x, y) -> (r, ângulo): converte PARA polar.

        Segue a convenção das calculadoras científicas (Casio e afins): o "Pol"
        recebe coordenadas retangulares e devolve as polares. O nome do token
        diz o DESTINO da conversão, não a entrada.

        O ângulo sai por atan2 (e não atan(y/x)) pelo quadrante correto e por
        não dividir por zero quando x = 0, e é convertido para a unidade do
        modo angular ativo como o resto da trigonometria do motor.
        """
        radius = math.hypot(x_value, y_value)
        angle = self._angle_from_radians(math.atan2(y_value, x_value))
        return self._snap_to_zero(radius), self._snap_to_zero(angle)

    def _to_rect(self, radius: float, angle: float) -> tuple[float, float]:
        """Rec(r, ângulo) -> (x, y): converte PARA retangular."""
        radians = self._angle_to_radians(angle)
        return (
            self._snap_to_zero(radius * math.cos(radians)),
            self._snap_to_zero(radius * math.sin(radians)),
        )

    def _format_value(self, value: float | tuple[float, float]) -> str:
        if isinstance(value, tuple):
            return f"({value[0]:.10g}, {value[1]:.10g})"
        
        # Clean up floating point noise for zero
        if abs(value) < 1e-12:
            value = 0.0
            
        if math.isfinite(value) and float(value).is_integer():
            return str(int(value))
        return f"{value:.10g}"
