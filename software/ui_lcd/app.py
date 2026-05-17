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
from software.hw_platform.display import DisplayMode, DisplaySelector
from software.hw_platform.keyboard import KeyboardAdapter
from software.hw_platform.ups import UpsMonitor


LEFT_BUTTONS: list[list[tuple[str, str, str | None, str | None]]] = [
    [("Pol", "polar(", "rect(", None), ("x!", "!", None, None), ("Pi", "π", "e", None)],
    [("sen", "sen(", "asin(", None), ("cos", "cos(", "acos(", None), ("", "", None, None)],
    [("tan", "tan(", "atan(", None), ("log", "log(", "ln(", "logbase("), ("", "", None, None)],
    [("x⁻¹", "inv(", None, None), ("^", "^", None, None)], # R3: x^-1 will span 2
    [("?", "", None, None), ("nCr", "nCr(", "nPr(", None), ("√", "sqrt(", None, None)],
    [("Ctrl", "Ctrl", None, None), ("exp", "exp(", None, None), ("Shift", "Shift", None, None)], # R5: Ctrl will span 2
]

RIGHT_BUTTONS: list[list[tuple[str, str, str | None, str | None]]] = [
    [("(", "(", None, None), (")", ")", None, None), ("%", "%", None, None), ("e", "e", None, None)],
    [("7", "7", None, None), ("8", "8", None, None), ("9", "9", None, None), ("/", "/", None, None)],
    [("4", "4", None, None), ("5", "5", None, None), ("6", "6", None, None), ("*", "*", None, None)],
    [("1", "1", None, None), ("2", "2", None, None), ("3", "3", None, None), ("-", "-", None, None)],
    [("0", "0", None, None), (".", ".", None, ","), ("+", "+", None, None)], # R4: 0 will span 2
    [("Ans", "Ans", None, None), ("=", "=", None, None), ("AC", "AC", None, None), ("DEL", "DEL", None, None)],
]


ERROR_MESSAGES = {
    "ERR-001": "Divisão por zero. Limpe ou altere a expressão.",
    "ERR-002": "Argumento inválido para esta função. Verifique o sinal e o domínio.",
    "ERR-003": "Valor fora do domínio da função.",
    "ERR-004": "Parâmetros inválidos para combinação ou permutação.",
    "ERR-005": "Fatorial não definido para este valor.",
    "ERR-006": "Resultado muito grande ou não representável.",
    "ERR-007": "Expressão inválida. Verifique parênteses e operadores.",
    "ERR-008": "Expressão incompleta.",
    "ERR-009": "Dados insuficientes ou inválidos para a conversão.",
    "WRN-010": "Não há resposta anterior.",
}


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
        
        # Globally configure TButton for the keypad to ensure consistent font
        self.style.configure("TButton", font=("Segoe UI", 14, "bold"))
        
        # Ensure outline versions also have the correct font just in case
        for color in ["primary", "secondary", "success", "info", "warning", "danger"]:
            self.style.configure(f"{color}.Outline.TButton", font=("Segoe UI", 14, "bold"))

        self.ctrl_active = False
        self.shift_active = False # Added shift tracking
        self.buttons: dict[str, ttk.Button] = {}

        self.expression_var = ttk.StringVar(value="")
        self.result_var = ttk.StringVar(value="Pronto")
        self.status_var = ttk.StringVar(value=self._status_text())
        
        # Indicators for special states
        self.mode_var = ttk.StringVar(value="DEG")
        self.ctrl_var = ttk.StringVar(value="")
        self.shift_var = ttk.StringVar(value="")

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

        # Top bar with indicators
        top_bar = ttk.Frame(root_frame)
        top_bar.grid(row=0, column=0, sticky=EW, pady=(0, 5))
        
        ttk.Label(top_bar, textvariable=self.mode_var, bootstyle="info", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)
        ttk.Label(top_bar, textvariable=self.ctrl_var, bootstyle="warning", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)
        ttk.Label(top_bar, textvariable=self.shift_var, bootstyle="success", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)

        # Glassmorphism effect simulation
        display = ttk.Frame(root_frame, bootstyle="secondary", padding=15)
        display.grid(row=1, column=0, sticky=EW, pady=(0, 10))
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
        keypad.grid(row=2, column=0, sticky="nsew")
        keypad.columnconfigure(0, weight=3, uniform="kp") # Left section
        keypad.columnconfigure(1, weight=1, uniform="kp") # Spacer
        keypad.columnconfigure(2, weight=4, uniform="kp") # Right section
        keypad.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(keypad)
        left_frame.grid(row=0, column=0, sticky="nsew")
        for i in range(6): left_frame.rowconfigure(i, weight=1, uniform="row")
        for i in range(3): left_frame.columnconfigure(i, weight=1, uniform="col_left")

        right_frame = ttk.Frame(keypad)
        right_frame.grid(row=0, column=2, sticky="nsew")
        for i in range(6): right_frame.rowconfigure(i, weight=1, uniform="row")
        for i in range(4): right_frame.columnconfigure(i, weight=1, uniform="col_right")

        # Update LEFT_BUTTONS to include RAD/DEG
        updated_left = [row[:] for row in LEFT_BUTTONS]
        # Replace the empty button in row 1, col 2 with RAD/DEG
        updated_left[1][2] = ("R/D", "RAD/DEG", None, None)

        # Helper to build buttons
        def build_buttons(container, buttons_list, is_left):
            for r, row in enumerate(buttons_list):
                curr_col = 0
                for item in row:
                    label, primary, secondary = item[0], item[1], item[2]
                    shifted = item[3] if len(item) > 3 else None
                    if not label: 
                        curr_col += 1
                        continue
                    btn_id = f"{primary}_{secondary}"
                    style = self._button_style(primary)
                    
                    button = ttk.Button(
                        container, text=label, bootstyle=style,
                        command=lambda p=primary, s=secondary, sh=shifted: self._handle_token(p, s, sh)
                    )
                    
                    # Special spans
                    cspan = 1
                    if is_left:
                        if (r == 3 and primary == "inv(") or (r == 5 and primary == "Ctrl"): cspan = 2
                    else:
                        if (r == 4 and primary == "0"): cspan = 2
                        
                    button.grid(row=r, column=curr_col, sticky="nsew", padx=3, pady=3, columnspan=cspan)
                    self.buttons[btn_id] = button
                    curr_col += cspan

        build_buttons(left_frame, updated_left, True)
        build_buttons(right_frame, RIGHT_BUTTONS, False)

        footer = ttk.Frame(root_frame, padding=(0, 5))
        footer.grid(row=3, column=0, sticky=EW)
        
        ttk.Button(footer, text="Histórico", bootstyle="link", command=self._show_history).pack(side=LEFT)
        ttk.Label(footer, textvariable=self.status_var, anchor=W, font=("Segoe UI", 11)).pack(side=LEFT, fill=X, expand=True, padx=10)
        ttk.Label(footer, text="Modo local", anchor=E, bootstyle="info", font=("Segoe UI", 11, "italic")).pack(side=RIGHT)

    def _button_style(self, token: str) -> str:
        if token == "AC":
            return "danger"
        if token == "DEL":
            return "warning"
        if token in {"=", "RAD/DEG"}:
            return "success"
        if token in {"Ctrl", "Shift"}:
            return "warning"
        
        # Operators and other symbols
        if token in {"+", "-", "*", "/", "^", "nCr(", "polar(", "π", ",", "."}:
            return "warning"
            
        # Scientific functions
        if any(f in token for f in ["sin", "cos", "tan", "log", "sqrt", "!", "asin", "acos", "atan", "inv", "ln", "nPr", "rect"]):
            return "success"
            
        # Numeric keys
        if token.isdigit() or token == "Ans":
            return "info"
            
        return "primary"

    def _bind_keyboard(self) -> None:
        self.root.bind("<Key>", self._on_key)
        self.root.bind("<Return>", lambda _event: self._handle_token("=", None, None))
        self.root.bind("<BackSpace>", lambda _event: self._handle_token("DEL", None, None))
        self.root.bind("<Escape>", lambda _event: self._handle_token("AC", None, None))
        self.root.bind("<Control_L>", lambda _event: self._handle_token("Ctrl", None, None))
        self.root.bind("<Control_R>", lambda _event: self._handle_token("Ctrl", None, None))
        self.root.bind("<Shift_L>", lambda _event: self._handle_token("Shift", None, None))
        self.root.bind("<Shift_R>", lambda _event: self._handle_token("Shift", None, None))

    def _on_key(self, event: object) -> None:
        char = getattr(event, "char", "")
        token = self.keyboard.map_key(char)
        if token:
            with open("speech_debug.log", "a", encoding="utf-8") as logs:
                logs.write(f"EVENTO TECLADO: char='{char}' -> token='{token}'\n")
            self._handle_token(token, None, None)

    def _handle_token(self, primary: str, secondary: str | None, shifted: str | None = None) -> None:
        if primary == "Ctrl":
            self.ctrl_active = not self.ctrl_active
            self.ctrl_var.set("CTRL" if self.ctrl_active else "")
            self._update_keypad_labels()
            self.speech.say("Controle ativo" if self.ctrl_active else "Controle desativado")
            return

        if primary == "Shift":
            self.shift_active = not self.shift_active
            self.shift_var.set("SHIFT" if self.shift_active else "")
            self._update_keypad_labels()
            self.speech.say("Shift ativo" if self.shift_active else "Shift desativado")
            return

        if primary == "RAD/DEG":
            self.state.press("RAD/DEG")
            self.mode_var.set(self.state.angle_mode.upper())
            self.speech.say(f"Modo {self.state.angle_mode}")
            return

        token = primary
        if self.shift_active and shifted:
            token = shifted
            self.shift_active = False
            self.shift_var.set("")
            self._update_keypad_labels()
        elif self.ctrl_active and secondary:
            token = secondary
            self.ctrl_active = False
            self.ctrl_var.set("")
            self._update_keypad_labels()
        
        if token == "=" and not self.state.expression:
            return

        is_digit_or_func = token.isdigit() or token == "Ans" or "(" in token or token in {"π", "e"}
        if self.state.last_result and self.state.last_result.ok and is_digit_or_func:
            self.state.press("AC")

        operators = {"+", "-", "*", "/", "^"}
        
        # CHAINING LOGIC: If a result was just shown and user presses an operator, 
        # auto-insert 'Ans' to chain the calculation.
        if self.state.last_result and self.state.last_result.ok and token in operators:
             self.state.expression = "Ans"
             self.state.last_result = None
             
        if token in operators and self.state.expression:
            last_char = self.state.expression[-1]
            if last_char in operators:
                self.speech.say("Substituindo")
                self.state.press("DEL")

        result = self.state.press(token)
        
        self.expression_var.set(self.state.expression)

        if result is None:
            spoken = self._spoken_token(token)
            self.speech.say(spoken)
            return

        self.result_var.set(result.display)
        if result.ok:
            self.speech.interrupt_and_say(f"Resultado {result.display}")
        else:
            friendly_msg = ERROR_MESSAGES.get(result.code, result.message)
            self.speech.interrupt_and_say(f"Erro {result.code.split('-')[-1]}. {friendly_msg}")

    def _update_keypad_labels(self) -> None:
        ctrl_map = {"asin(": "sen⁻¹", "acos(": "cos⁻¹", "atan(": "tan⁻¹", "ln(": "ln", "nPr(": "nPr", "rect(": "Rec", "e": "e"}
        shift_map = {"logbase(": "log_b", ",": ","}
        
        # Combine lists for iteration
        all_rows = LEFT_BUTTONS + RIGHT_BUTTONS
        
        for row in all_rows:
            for item in row:
                label, primary, secondary = item[0], item[1], item[2]
                shifted = item[3] if len(item) > 3 else None
                if not label: continue
                
                btn_id = f"{primary}_{secondary}"
                if btn_id in self.buttons:
                    button = self.buttons[btn_id]
                    new_text = label
                    new_style = self._button_style(primary)
                    
                    if self.shift_active and shifted:
                        new_text = shift_map.get(shifted, shifted.rstrip("("))
                        new_style = "info"
                    elif self.ctrl_active and secondary:
                        new_text = ctrl_map.get(secondary, secondary.rstrip("("))
                        new_style = "info"
                    
                    button.configure(text=new_text, bootstyle=new_style)

    def _show_history(self) -> None:
        top = ttk.Toplevel(title="Histórico de Operações")
        top.geometry("400x500")
        
        frame = ttk.Frame(top, padding=10)
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(frame, text="Últimas 10 operações", font=("Segoe UI", 12, "bold")).pack(pady=(0, 10))
        
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=BOTH, expand=True)
        
        if not self.state.history:
            ttk.Label(list_frame, text="Nenhuma operação realizada.", font=("Segoe UI", 10, "italic")).pack()
        else:
            for res in reversed(self.state.history):
                item = ttk.Frame(list_frame, padding=5, bootstyle="secondary")
                item.pack(fill=X, pady=2)
                ttk.Label(item, text=res.expression, font=("Segoe UI", 10)).pack(side=LEFT)
                ttk.Label(item, text=f"= {res.display}", font=("Segoe UI", 10, "bold")).pack(side=RIGHT)

    def _spoken_token(self, token: str) -> str:
        names = {
            "AC": "limpar tudo", "DEL": "apagar", "/": "dividido por", "*": "vezes", "-": "menos", "+": "mais", "^": "elevado a",
            "π": "pi", "e": "é", "(": "abre parênteses", ")": "fecha parênteses", "Ans": "resposta anterior",
            "sen(": "seno", "cos(": "cosseno", "tan(": "tangente", "log(": "logaritmo decimal", "ln(": "logaritmo natural",
            "sqrt(": "raiz quadrada", "asin(": "arco seno", "acos(": "arco cosseno", "atan(": "arco tangente", "!": "fatorial",
            "nCr(": "combinação", "nPr(": "permutação", "polar(": "polar para retangular", "rect(": "retangular para polar",
            "logbase(": "logaritmo na base x",
            "x^-1": "inverso", "Ctrl": "controle", "Shift": "shift", ",": "vírgula", ".": "ponto", "RAD/DEG": "alternar radianos e graus"
        }
        return names.get(token, token)

    def _status_text(self) -> str:
        display_mode = self.display_selector.current_mode()
        ups_status = self.ups.read_status()
        visual = "LCD" if display_mode == DisplayMode.LCD else "monitor"
        return f"Saida visual: {visual} | Energia: {ups_status.label}"


def main() -> None:
    CalculatorApp().run()


def main() -> None:
    CalculatorApp().run()
