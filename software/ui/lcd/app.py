"""ttkbootstrap LCD prototype for local testing and Raspberry Pi use."""

from __future__ import annotations

import logging

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import BOTH, CENTER, E, EW, LEFT, NSEW, RIGHT, W, X
except ImportError as exc:  # pragma: no cover - user-facing startup guard
    raise SystemExit(
        "Instale as dependencias com: python -m pip install -r software/requirements.txt"
    ) from exc

from software.accessibility.speech import SpeechService
from software.core import CalculatorState
from software.hw_platform.display import DisplayMode, DisplaySelector
from software.hw_platform.keyboard import KeyboardAdapter
from software.hw_platform.ups import UpsMonitor
from software.ui.shared.error_messages import friendly_message, spoken_priority_prefix
from software.ui.shared.formatting import FUNCTION_DISPLAY_SYMBOLS, format_expression_for_display
from software.ui.shared.keypad import (
    LEFT_BUTTONS,
    RIGHT_BUTTONS,
    button_style,
    keypad_toggle_label,
    keypad_toggle_speech,
    spoken_token,
)
from software.ui.shared.palette import BUTTON_PALETTE, DISPLAY_BACKGROUND, DISPLAY_FOREGROUND

logger = logging.getLogger(__name__)


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
        self.style.configure(
            "Display.TLabel", font=("Segoe UI", 80), padding=15,
            foreground=DISPLAY_FOREGROUND, background=DISPLAY_BACKGROUND,
        )
        self.style.configure(
            "Result.TLabel", font=("Segoe UI", 120, "bold"), padding=15,
            foreground=DISPLAY_FOREGROUND, background=DISPLAY_BACKGROUND,
        )

        # Globally configure TButton for the keypad to ensure consistent font
        self.style.configure("TButton", font=("Segoe UI", 28, "bold"))

        # Ensure outline versions also have the correct font just in case
        for color in ["primary", "secondary", "success", "info", "warning", "danger"]:
            self.style.configure(f"{color}.Outline.TButton", font=("Segoe UI", 28, "bold"))

        # Accessibility: override the theme's built-in bootstyle colors with a
        # WCAG-verified palette (see ui/shared/palette.py + ui/shared/contrast.py).
        # ttkbootstrap's default theme colors aren't guaranteed to meet WCAG AA
        # and can't be introspected without a running Tk instance, so this app
        # owns and verifies its own category colors instead of trusting them.
        for category, colors in BUTTON_PALETTE.items():
            self.style.configure(
                f"{category}.TButton",
                background=colors.background,
                foreground=colors.foreground,
            )
            # Pressed/focused states must stay perceivable without relying on
            # color alone: press inverts fg/bg (high-contrast tactile cue),
            # focus gets a bright border (interaction-feedback spec).
            self.style.map(
                f"{category}.TButton",
                background=[("pressed", colors.foreground), ("active", colors.background)],
                foreground=[("pressed", colors.background)],
                bordercolor=[("focus", "#FFFFFF")],
                relief=[("pressed", "sunken")],
            )

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
        # Teclado na tela começa oculto: a entrada real é o teclado físico
        # (RF-05) e a área livre vai para expressão/resultado.
        self.controls_visible = False

        # Truncated display variables
        self.expression_disp_var = ttk.StringVar(value="")
        self.result_disp_var = ttk.StringVar(value="")

        self._build_layout()
        self._apply_controls_visibility()
        self._bind_keyboard()
        self._set_initial_focus()

        # Add tracers for truncation logic
        self.expression_var.trace_add("write", lambda *_: self._update_display())
        self.result_var.trace_add("write", lambda *_: self._update_display())

    def _update_display(self) -> None:
        """Update truncated display variables based on raw variables."""
        expr = format_expression_for_display(self.expression_var.get())
        res = self.result_var.get()
        
        # Max chars that reasonably fit with current font sizes (80/120)
        # Increased to utilize more screen width as requested
        max_expr = 30
        max_res = 20
        
        if len(expr) > max_expr:
            self.expression_disp_var.set("..." + expr[-(max_expr-3):])
        else:
            self.expression_disp_var.set(expr)
            
        if len(res) > max_res:
            self.result_disp_var.set(".." + res[-(max_res-2):])
        else:
            self.result_disp_var.set(res)

    def run(self) -> None:
        self.speech.say("Calculadora pronta")
        self.root.mainloop()
        self.speech.stop()

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self.root, padding=10)
        root_frame.pack(fill=BOTH, expand=True)
        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(0, weight=0) # Top bar
        root_frame.rowconfigure(1, weight=1) # Display area
        root_frame.rowconfigure(2, weight=2) # Keypad area
        root_frame.rowconfigure(3, weight=0) # Footer

        row_idx = 0

        # Top bar with indicators
        top_bar = ttk.Frame(root_frame)
        top_bar.grid(row=row_idx, column=0, sticky=EW, pady=(0, 5))
        row_idx += 1
        
        ttk.Label(top_bar, textvariable=self.mode_var, bootstyle="info", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)
        ttk.Label(top_bar, textvariable=self.ctrl_var, bootstyle="warning", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)
        ttk.Label(top_bar, textvariable=self.shift_var, bootstyle="success", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)

        # Glassmorphism effect simulation
        display = ttk.Frame(root_frame, bootstyle="secondary", padding=15)
        display.grid(row=row_idx, column=0, sticky=NSEW, pady=(0, 10))
        display.columnconfigure(0, weight=1)
        display.rowconfigure(0, weight=1) # Expression
        display.rowconfigure(1, weight=2) # Result (more dominant)
        row_idx += 1

        self.expression_label = ttk.Label(
            display,
            textvariable=self.expression_disp_var,
            anchor=E,
            style="Display.TLabel",
            bootstyle="inverse-secondary"
        )
        self.expression_label.grid(row=0, column=0, sticky=NSEW)

        self.result_label = ttk.Label(
            display,
            textvariable=self.result_disp_var,
            anchor=E,
            style="Result.TLabel",
            bootstyle="inverse-secondary"
        )
        self.result_label.grid(row=1, column=0, sticky=NSEW)

        self.keypad_frame = ttk.Frame(root_frame)
        self.keypad_frame.grid(row=row_idx, column=0, sticky=NSEW)
        row_idx += 1
        self.keypad_frame.columnconfigure(0, weight=3, uniform="kp") # Left section
        self.keypad_frame.columnconfigure(1, weight=1, uniform="kp") # Spacer
        self.keypad_frame.columnconfigure(2, weight=4, uniform="kp") # Right section
        self.keypad_frame.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(self.keypad_frame)
        left_frame.grid(row=0, column=0, sticky="nsew")
        for i in range(6): left_frame.rowconfigure(i, weight=1, uniform="row")
        for i in range(3): left_frame.columnconfigure(i, weight=1, uniform="col_left")

        right_frame = ttk.Frame(self.keypad_frame)
        right_frame.grid(row=0, column=2, sticky="nsew")
        for i in range(6): right_frame.rowconfigure(i, weight=1, uniform="row")
        for i in range(4): right_frame.columnconfigure(i, weight=1, uniform="col_right")

        # No longer injecting R/D here
        updated_left = [row[:] for row in LEFT_BUTTONS]

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
        footer.grid(row=row_idx, column=0, sticky=EW, pady=(5, 0))
        
        ttk.Button(footer, text="Histórico", bootstyle="link", command=self._show_history).pack(side=LEFT)
        # Discreto de propósito: estilo "link" (sem moldura) e fonte pequena,
        # para não roubar espaço dos 800x480. Continua focável por Tab e
        # anunciado por voz.
        self.toggle_btn = ttk.Button(
            footer, text=keypad_toggle_label(self.controls_visible),
            bootstyle="secondary-link", command=self._toggle_controls,
        )
        self._style_discreet(self.toggle_btn, size=11)
        self.toggle_btn.pack(side=LEFT, padx=10)
        
        ttk.Label(footer, textvariable=self.status_var, anchor=W, font=("Segoe UI", 20)).pack(side=LEFT, fill=X, expand=True, padx=10)
        ttk.Label(footer, text="Modo local", anchor=E, bootstyle="info", font=("Segoe UI", 20, "italic")).pack(side=RIGHT)

    def _style_discreet(self, button: ttk.Button, size: int) -> None:
        """Encolhe só este botão.

        A app configura "TButton" globalmente com 28pt bold (tamanho de tecla),
        o que deixaria o botão do rodapé enorme. Deriva um estilo do que o
        ttkbootstrap gerou, herdando as cores e trocando apenas a fonte.
        """
        compact = f"Compact.{button.cget('style')}"
        self.style.configure(compact, font=("Segoe UI", size), padding=(6, 2))
        button.configure(style=compact)

    def _apply_controls_visibility(self) -> None:
        """Sincroniza teclado e rótulo do botão com self.controls_visible."""
        if self.controls_visible:
            self.keypad_frame.grid()
        else:
            self.keypad_frame.grid_remove()
        self.toggle_btn.configure(text=keypad_toggle_label(self.controls_visible))

    def _set_initial_focus(self) -> None:
        """Give Tab traversal a predictable starting point (keyboard-navigation).

        Com o teclado oculto por padrão, o ponto de partida passa a ser o
        próprio botão que o revela - senão o Tab começaria em algo invisível.
        """
        if self.controls_visible:
            first_digit = self.buttons.get("7_None")
            if first_digit is not None:
                first_digit.focus_set()
                return
        self.toggle_btn.focus_set()

    def _toggle_controls(self) -> None:
        self.controls_visible = not self.controls_visible
        self._apply_controls_visibility()
        self.speech.say(keypad_toggle_speech(self.controls_visible))

    def _button_style(self, token: str) -> str:
        return button_style(token)

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
            logger.debug("key event: char=%r -> token=%r", char, token)
            self._handle_token(token, None, None)

    def _handle_token(self, primary: str, secondary: str | None, shifted: str | None = None) -> None:
        if self.ctrl_active and self.shift_active and primary not in {"Ctrl", "Shift"}:
            # Consolidated announcement for Task 3
            main_name = self._spoken_token(primary)
            ctrl_name = self._spoken_token(secondary) if secondary else "Nenhuma"
            shift_name = self._spoken_token(shifted) if shifted else "Nenhuma"
            
            msg = f"Função {main_name}."
            msg += f" Com Controle ativo, função {ctrl_name}."
            msg += f" Com Shift ativo, função {shift_name}."
            
            self.speech.say(msg)
            # Modifiers remain active for further exploration or can be reset. 
            # Following usual help patterns, we keep them.
            return

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

        if token == "RECALL":
            self._recall_last_answer()
            return

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

        if result.ok:
            self.result_var.set(result.display)
            self.speech.interrupt_and_say(f"Resultado {result.display}")
        else:
            # Same friendly text on screen and in speech (error-messaging spec:
            # UI and TTS must agree, not just share a code) and the PRD §13
            # prefix by priority: P1 codes are "Erro", P2 codes are "Aviso"
            # (WRN-010 previously always announced as "Erro", which was wrong).
            friendly_msg = friendly_message(result.code, result.message)
            prefix = spoken_priority_prefix(result.code)
            self.result_var.set(f"{result.code}: {friendly_msg}")
            self.speech.interrupt_and_say(f"{prefix} {result.code.split('-')[-1]}. {friendly_msg}")

    def _update_keypad_labels(self) -> None:
        # Reuse FUNCTION_DISPLAY_SYMBOLS so the button label always matches the
        # symbol shown in the expression and spoken by the TTS (task 1.3).
        symbol_labels = {token: symbol.rstrip("(") for token, symbol in FUNCTION_DISPLAY_SYMBOLS.items()}
        ctrl_map = {**symbol_labels, "ln(": "ln", "nPr(": "nPr", "e": "e", "RECALL": "Últ. resp."}
        shift_map = {"logbase(": symbol_labels["logbase("], ",": ",", "RAD/DEG": "Deg/Rad", "RECALL": "Últ. resp."}
        
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
            self.speech.say("Histórico vazio. Nenhuma operação realizada.")
        else:
            for res in reversed(self.state.history):
                item = ttk.Frame(list_frame, padding=5, bootstyle="secondary")
                item.pack(fill=X, pady=2)
                ttk.Label(item, text=res.expression, font=("Segoe UI", 20)).pack(side=LEFT)
                ttk.Label(item, text=f"= {res.display}", font=("Segoe UI", 20, "bold")).pack(side=RIGHT)
            self.speech.say(f"Histórico aberto. {len(self.state.history)} operações.")

    def _recall_last_answer(self) -> None:
        """Shift/Ctrl + '=' : re-announce/redisplay the last full result
        without recalculating or touching the in-progress expression."""
        result = self.state.recall_last_answer()
        if result.ok:
            self.result_var.set(result.display)
            self.speech.interrupt_and_say(f"Última resposta: {result.display}")
        else:
            friendly_msg = friendly_message(result.code, result.message)
            prefix = spoken_priority_prefix(result.code)
            self.speech.interrupt_and_say(f"{prefix} {result.code.split('-')[-1]}. {friendly_msg}")

    def _spoken_token(self, token: str) -> str:
        return spoken_token(token)

    def _status_text(self) -> str:
        display_mode = self.display_selector.current_mode()
        ups_status = self.ups.read_status()
        visual = "LCD" if display_mode == DisplayMode.LCD else "monitor"
        return f"Saida visual: {visual} | Energia: {ups_status.label}"


def main() -> None:
    CalculatorApp().run()


if __name__ == "__main__":
    main()
