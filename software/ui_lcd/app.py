"""ttkbootstrap LCD prototype for local testing and Raspberry Pi use."""

from __future__ import annotations

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import BOTH, CENTER, E, EW, LEFT, RIGHT, W, X
except ImportError as exc:  # pragma: no cover - user-facing startup guard
    raise SystemExit(
        "Instale as dependencias com: python -m pip install -r software/requirements.txt"
    ) from exc

from software.accessibility.speech import SpeechService
from software.core import CalculatorState
from software.platform.display import DisplayMode, DisplaySelector
from software.platform.keyboard import KeyboardAdapter
from software.platform.ups import UpsMonitor


BUTTONS: list[list[tuple[str, str]]] = [
    [("AC", "AC"), ("DEL", "DEL"), ("(", "("), (")", ")"), ("Ans", "Ans"), ("x^-1", "x^-1")],
    [("sen", "sen("), ("cos", "cos("), ("tan", "tan("), ("log", "log("), ("ln", "ln("), ("sqrt", "sqrt(")],
    [("sen-1", "asin("), ("cos-1", "acos("), ("tan-1", "atan("), ("x!", "!"), ("nCr", "nCr("), ("nPr", "nPr(")],
    [("7", "7"), ("8", "8"), ("9", "9"), ("÷", "/"), ("x^y", "^"), (",", ",")],
    [("4", "4"), ("5", "5"), ("6", "6"), ("×", "*"), ("π", "π"), ("e", "e")],
    [("1", "1"), ("2", "2"), ("3", "3"), ("-", "-"), (".", "."), ("=", "=")],
    [("0", "0"), ("00", "00"), ("+", "+"), ("", ""), ("", ""), ("", "")],
]


class CalculatorApp:
    """Main visual shell sized for the 4.3 inch 800x480 LCD."""

    def __init__(self) -> None:
        self.state = CalculatorState()
        self.speech = SpeechService()
        self.keyboard = KeyboardAdapter()
        self.display_selector = DisplaySelector()
        self.ups = UpsMonitor()

        self.root = ttk.Window(themename="darkly")
        self.root.title("Calculadora Cientifica Acessivel")
        self.root.geometry("800x480")
        self.root.minsize(800, 480)

        self.expression_var = ttk.StringVar(value="")
        self.result_var = ttk.StringVar(value="Pronto")
        self.status_var = ttk.StringVar(value=self._status_text())

        self._build_layout()
        self._bind_keyboard()

    def run(self) -> None:
        self.speech.say("Calculadora pronta")
        self.root.mainloop()
        self.speech.stop()

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self.root, padding=8)
        root_frame.pack(fill=BOTH, expand=True)
        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(1, weight=1)

        display = ttk.Frame(root_frame, bootstyle="secondary", padding=8)
        display.grid(row=0, column=0, sticky=EW, pady=(0, 6))
        display.columnconfigure(0, weight=1)

        ttk.Label(
            display,
            textvariable=self.expression_var,
            anchor=E,
            font=("Arial", 20),
            bootstyle="inverse-secondary",
        ).grid(row=0, column=0, sticky=EW)
        ttk.Label(
            display,
            textvariable=self.result_var,
            anchor=E,
            font=("Arial", 28, "bold"),
            bootstyle="inverse-secondary",
        ).grid(row=1, column=0, sticky=EW)

        keypad = ttk.Frame(root_frame)
        keypad.grid(row=1, column=0, sticky="nsew")
        for row_index in range(len(BUTTONS)):
            keypad.rowconfigure(row_index, weight=1)
        for column_index in range(6):
            keypad.columnconfigure(column_index, weight=1)

        for row_index, row in enumerate(BUTTONS):
            for column_index, (label, token) in enumerate(row):
                if not label:
                    continue
                style = self._button_style(token)
                button = ttk.Button(
                    keypad,
                    text=label,
                    bootstyle=style,
                    command=lambda value=token: self._handle_token(value),
                )
                button.grid(
                    row=row_index,
                    column=column_index,
                    sticky="nsew",
                    padx=2,
                    pady=2,
                )

        footer = ttk.Frame(root_frame)
        footer.grid(row=2, column=0, sticky=EW, pady=(6, 0))
        ttk.Label(footer, textvariable=self.status_var, anchor=W).pack(side=LEFT, fill=X, expand=True)
        ttk.Label(footer, text="Modo local", anchor=E, bootstyle="info").pack(side=RIGHT)

    def _button_style(self, token: str) -> str:
        if token in {"AC", "DEL"}:
            return "danger"
        if token == "=":
            return "success"
        if token in {"+", "-", "*", "/", "^", "nCr(", "nPr("}:
            return "warning"
        return "primary"

    def _bind_keyboard(self) -> None:
        self.root.bind("<Key>", self._on_key)
        self.root.bind("<Return>", lambda _event: self._handle_token("="))
        self.root.bind("<BackSpace>", lambda _event: self._handle_token("DEL"))
        self.root.bind("<Escape>", lambda _event: self._handle_token("AC"))

    def _on_key(self, event: object) -> None:
        char = getattr(event, "char", "")
        token = self.keyboard.map_key(char)
        if token:
            self._handle_token(token)

    def _handle_token(self, token: str) -> None:
        result = self.state.press(token)
        self.expression_var.set(self.state.expression)

        if result is None:
            if token in {"AC", "DEL"}:
                self.result_var.set("Pronto" if token == "AC" else self.result_var.get())
            self.speech.say(self._spoken_token(token))
            return

        self.result_var.set(result.display)
        if result.ok:
            self.speech.interrupt_and_say(f"Resultado {result.display}")
        else:
            self.speech.interrupt_and_say(f"{result.code}. {result.message}")

    def _spoken_token(self, token: str) -> str:
        names = {
            "AC": "limpar",
            "DEL": "apagar",
            "/": "dividir",
            "*": "multiplicar",
            "-": "menos",
            "+": "mais",
            "^": "elevado a",
            "π": "pi",
        }
        return names.get(token, token.replace("(", ""))

    def _status_text(self) -> str:
        display_mode = self.display_selector.current_mode()
        ups_status = self.ups.read_status()
        visual = "LCD" if display_mode == DisplayMode.LCD else "monitor"
        return f"Saida visual: {visual} | Energia: {ups_status.label}"


def main() -> None:
    CalculatorApp().run()
