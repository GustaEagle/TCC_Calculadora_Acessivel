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


BUTTONS: list[list[tuple[str, str, str | None]]] = [
    [("AC", "AC", None), ("DEL", "DEL", None), ("(", "(", None), (")", ")", None), ("Ans", "Ans", None), ("Ctrl", "Ctrl", None)],
    [("sen", "sen(", "asin("), ("cos", "cos(", "acos("), ("tan", "tan(", "atan("), ("log", "log(", "ln("), ("x!", "!", None), ("sqrt", "sqrt(", None)],
    [("nCr", "nCr(", "nPr("), ("Pol", "polar(", "rect("), ("π", "π", "e"), ("7", "7", None), ("8", "8", None), ("9", "9", None)],
    [("÷", "/", None), ("x^y", "^", None), (",", ",", None), ("4", "4", None), ("5", "5", None), ("6", "6", None)],
    [("×", "*", None), ("x⁻¹", "inv(", None), ("1", "1", None), ("2", "2", None), ("3", "3", None), ("-", "-", None)],
    [("0", "0", None), ("00", "00", None), (".", ".", None), ("+", "+", None), ("=", "=", None), ("", "", None)],
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

        # Custom styles for a more premium look
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("Segoe UI", 12))
        self.style.configure("Display.TLabel", font=("Segoe UI", 28), padding=10)
        self.style.configure("Result.TLabel", font=("Segoe UI", 40, "bold"), padding=10)
        
        # Globally configure TButton for the keypad to ensure consistent font and size
        self.style.configure("TButton", font=("Segoe UI", 14, "bold"), width=8)
        
        # Ensure outline versions also have the correct font just in case
        for color in ["primary", "secondary", "success", "info", "warning", "danger"]:
            self.style.configure(f"{color}.Outline.TButton", font=("Segoe UI", 14, "bold"), width=8)

        self.ctrl_active = False
        self.buttons: dict[str, ttk.Button] = {}

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
        root_frame = ttk.Frame(self.root, padding=10)
        root_frame.pack(fill=BOTH, expand=True)
        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(1, weight=1)

        # Glassmorphism effect simulation with contrasting colors and heavy padding
        display = ttk.Frame(root_frame, bootstyle="secondary", padding=15)
        display.grid(row=0, column=0, sticky=EW, pady=(0, 10))
        display.columnconfigure(0, weight=1)

        ttk.Label(
            display,
            textvariable=self.expression_var,
            anchor=E,
            style="Display.TLabel",
            bootstyle="inverse-secondary",
        ).grid(row=0, column=0, sticky=EW)
        ttk.Label(
            display,
            textvariable=self.result_var,
            anchor=E,
            style="Result.TLabel",
            bootstyle="inverse-secondary",
        ).grid(row=1, column=0, sticky=EW)

        keypad = ttk.Frame(root_frame)
        keypad.grid(row=1, column=0, sticky="nsew")
        for row_index in range(len(BUTTONS)):
            keypad.rowconfigure(row_index, weight=1)
        for column_index in range(6):
            keypad.columnconfigure(column_index, weight=1)

        for row_index, row in enumerate(BUTTONS):
            for column_index, (label, primary, secondary) in enumerate(row):
                if not label:
                    continue
                
                # Combine primary and secondary to create a unique ID for the button widget
                btn_id = f"{primary}_{secondary}"
                style = self._button_style(primary)
                
                button = ttk.Button(
                    keypad,
                    text=label,
                    bootstyle=style,
                    command=lambda p=primary, s=secondary: self._handle_token(p, s),
                )
                button.grid(
                    row=row_index,
                    column=column_index,
                    sticky="nsew",
                    padx=3,
                    pady=3,
                )
                self.buttons[btn_id] = button

        footer = ttk.Frame(root_frame, padding=(0, 5))
        footer.grid(row=2, column=0, sticky=EW)
        ttk.Label(footer, textvariable=self.status_var, anchor=W, font=("Segoe UI", 11)).pack(side=LEFT, fill=X, expand=True)
        ttk.Label(footer, text="Modo local", anchor=E, bootstyle="info", font=("Segoe UI", 11, "italic")).pack(side=RIGHT)

    def _button_style(self, token: str) -> str:
        if token == "AC":
            return "danger"
        if token == "DEL":
            return "warning"
        if token == "=":
            return "success"
        if token == "Ctrl":
            return "warning"
        
        # Operators and other symbols
        if token in {"+", "-", "*", "/", "^", "nCr(", "polar(", "π", ",", "."}:
            return "warning"
            
        # Scientific functions (green per request)
        if any(f in token for f in ["sin", "cos", "tan", "log", "sqrt", "!", "asin", "acos", "atan", "inv", "ln", "nPr", "rect"]):
            return "success"
            
        # Numeric keys (light blue per request)
        if token.isdigit() or token == "Ans":
            return "info"
            
        return "primary"

    def _bind_keyboard(self) -> None:
        self.root.bind("<Key>", self._on_key)
        self.root.bind("<Return>", lambda _event: self._handle_token("=", None))
        self.root.bind("<BackSpace>", lambda _event: self._handle_token("DEL", None))
        self.root.bind("<Escape>", lambda _event: self._handle_token("AC", None))
        self.root.bind("<Control_L>", lambda _event: self._handle_token("Ctrl", None))
        self.root.bind("<Control_R>", lambda _event: self._handle_token("Ctrl", None))

    def _on_key(self, event: object) -> None:
        char = getattr(event, "char", "")
        token = self.keyboard.map_key(char)
        if token:
            self._handle_token(token, None)

    def _handle_token(self, primary: str, secondary: str | None) -> None:
        # Toggle Ctrl state
        if primary == "Ctrl":
            self.ctrl_active = not self.ctrl_active
            self._update_ui_for_ctrl()
            self.speech.say("Controle ativo" if self.ctrl_active else "Controle desativado")
            return

        # Select token based on Ctrl state
        token = secondary if (self.ctrl_active and secondary) else primary
        
        with open("C:/Users/Administrator/TCC_Calculadora_Acessivel/speech_debug.log", "a", encoding="utf-8") as logs:
            logs.write(f"UI: Pressionado botão '{token}' (Ctrl={self.ctrl_active})\n")
        
        result = self.state.press(token)
        
        # Reset Ctrl after use if it was a scientific function
        if self.ctrl_active and secondary:
            self.ctrl_active = False
            self._update_ui_for_ctrl()

        self.expression_var.set(self.state.expression)

        if result is None:
            if token in {"AC", "DEL"}:
                self.result_var.set("Pronto" if token == "AC" else self.result_var.get())
            
            spoken = self._spoken_token(token)
            with open("C:/Users/Administrator/TCC_Calculadora_Acessivel/speech_debug.log", "a", encoding="utf-8") as logs:
                logs.write(f"UI: Falando token '{spoken}'\n")
            self.speech.say(spoken)
            return

        self.result_var.set(result.display)
        if result.ok:
            self.speech.interrupt_and_say(f"Resultado {result.display}")
        else:
            self.speech.interrupt_and_say(f"{result.code}. {result.message}")

    def _update_ui_for_ctrl(self) -> None:
        """Refresh all button labels based on current Ctrl state."""
        for row in BUTTONS:
            for label, primary, secondary in row:
                if not label or not secondary:
                    continue
                
                btn_id = f"{primary}_{secondary}"
                if btn_id in self.buttons:
                    # Update label to show primary or secondary
                    new_text = secondary.rstrip("(") if self.ctrl_active else label
                    # Mapping secondary names to readable short labels
                    display_map = {
                        "asin(": "sen⁻¹",
                        "acos(": "cos⁻¹",
                        "atan(": "tan⁻¹",
                        "ln(": "ln",
                        "nPr(": "nPr",
                        "rect(": "Rec",
                        "e": "e"
                    }
                    if self.ctrl_active:
                        new_text = display_map.get(secondary, secondary.rstrip("("))
                    else:
                        new_text = label
                        
                    self.buttons[btn_id].configure(text=new_text)
                    # Change style to highlight active secondary function
                    new_style = "info" if self.ctrl_active else self._button_style(primary)
                    self.buttons[btn_id].configure(bootstyle=new_style)

    def _spoken_token(self, token: str) -> str:
        names = {
            "AC": "limpar tudo",
            "DEL": "apagar",
            "/": "dividido por",
            "*": "vezes",
            "-": "menos",
            "+": "mais",
            "^": "elevado a",
            "π": "pi",
            "e": "é",
            "(": "abre parênteses",
            ")": "fecha parênteses",
            "Ans": "resposta anterior",
            "sen(": "seno",
            "cos(": "cosseno",
            "tan(": "tangente",
            "log(": "logaritmo decimal",
            "ln(": "logaritmo natural",
            "sqrt(": "raiz quadrada",
            "asin(": "arco seno",
            "acos(": "arco cosseno",
            "atan(": "arco tangente",
            "!": "fatorial",
            "nCr(": "combinação",
            "nPr(": "permutação",
            "polar(": "polar para retangular",
            "rect(": "retangular para polar",
            "x^-1": "inverso",
            "Ctrl": "controle",
            ",": "vírgula",
            ".": "ponto",
        }
        return names.get(token, token)

    def _status_text(self) -> str:
        display_mode = self.display_selector.current_mode()
        ups_status = self.ups.read_status()
        visual = "LCD" if display_mode == DisplayMode.LCD else "monitor"
        return f"Saida visual: {visual} | Energia: {ups_status.label}"


def main() -> None:
    CalculatorApp().run()
