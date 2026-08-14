"""ttkbootstrap front-end for the external HDMI monitor.

Sibling of ui/lcd/app.py, not an extension of it: the monitor gets its own
composition (persistent history panel beside the keypad, PRD §8 "maior area,
layout mais rico") instead of the 800x480 panel arrangement.

Responsive by design: unlike the LCD front, this window never pins itself to a
physical size. It opens at whatever resolution the OS reports and every font
and cell is recomputed from the *current* window size, so the same code fits a
1366x768 monitor, a 4K one, or a hand-resized window during local testing.
"""

from __future__ import annotations

import logging

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import BOTH, E, EW, LEFT, NSEW, RIGHT, W, X
except ImportError as exc:  # pragma: no cover - user-facing startup guard
    raise SystemExit(
        "Instale as dependencias com: python -m pip install -r software/requirements.txt"
    ) from exc

from software.accessibility.speech import SpeechService
from software.core import CalculatorState
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
from software.ui.shared.responsive import (
    MIN_USABLE_HEIGHT,
    MIN_USABLE_WIDTH,
    font_sizes,
    responsive_scale,
    visible_chars,
)

logger = logging.getLogger(__name__)

_HISTORY_VISIBLE_ROWS = 10


class CalculatorApp:
    """Visual shell for the external monitor, sized from the active display."""

    def __init__(self) -> None:
        self.state = CalculatorState()
        self.speech = SpeechService()
        self.keyboard = KeyboardAdapter()
        self.ups = UpsMonitor()

        self.root = ttk.Window(themename="darkly")
        self.root.title("Calculadora Cientifica Acessivel - Monitor")

        # Open at the resolution the OS actually reports for this output rather
        # than assuming one (RF-02/RF-03: the monitor is the preferred output,
        # and we do not know its size ahead of time).
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        # A degenerate-window guard only - never a target size. Everything
        # inside adapts continuously via grid weights.
        self.root.minsize(MIN_USABLE_WIDTH, MIN_USABLE_HEIGHT)

        self.style = ttk.Style()
        self._scale = 0.0  # forces the first _apply_scale() to run

        self.ctrl_active = False
        self.shift_active = False
        self.buttons: dict[str, ttk.Button] = {}

        self.expression_var = ttk.StringVar(value="")
        self.result_var = ttk.StringVar(value="Pronto")
        self.status_var = ttk.StringVar(value=self._status_text())

        self.mode_var = ttk.StringVar(value="DEG")
        self.ctrl_var = ttk.StringVar(value="")
        self.shift_var = ttk.StringVar(value="")
        # Teclado na tela começa oculto: a entrada real é o teclado físico
        # (RF-05) e a área livre vai para expressão/resultado/histórico.
        self.controls_visible = False

        self.expression_disp_var = ttk.StringVar(value="")
        self.result_disp_var = ttk.StringVar(value="")

        self._configure_palette()
        self._build_layout()
        self._apply_controls_visibility()
        self._bind_keyboard()
        self._set_initial_focus()

        self.expression_var.trace_add("write", lambda *_: self._update_display())
        self.result_var.trace_add("write", lambda *_: self._update_display())

        # Recompute proportions whenever the window changes size, so a resized
        # window (or a different monitor) re-lays out instead of clipping.
        self.root.bind("<Configure>", self._on_configure)
        self.root.update_idletasks()
        self._apply_scale(force=True)

    # ------------------------------------------------------------------
    # Responsive sizing
    # ------------------------------------------------------------------

    def _current_scale(self) -> float:
        return responsive_scale(self.root.winfo_width(), self.root.winfo_height())

    def _on_configure(self, event: object) -> None:
        # <Configure> fires for child widgets too; only react to the toplevel.
        if getattr(event, "widget", None) is not self.root:
            return
        self._apply_scale()

    def _apply_scale(self, force: bool = False) -> None:
        scale = self._current_scale()
        # Ignore sub-pixel jitter so a drag-resize does not restyle every frame.
        if not force and abs(scale - self._scale) < 0.02:
            return
        self._scale = scale

        sizes = font_sizes(scale)
        expression_size = sizes["expression"]
        result_size = sizes["result"]
        button_size = sizes["button"]
        label_size = sizes["label"]
        history_size = sizes["history"]

        self.style.configure("TLabel", font=("Segoe UI", label_size))
        self.style.configure(
            "Display.TLabel", font=("Segoe UI", expression_size), padding=int(10 * scale),
            foreground=DISPLAY_FOREGROUND, background=DISPLAY_BACKGROUND,
        )
        self.style.configure(
            "Result.TLabel", font=("Segoe UI", result_size, "bold"), padding=int(10 * scale),
            foreground=DISPLAY_FOREGROUND, background=DISPLAY_BACKGROUND,
        )
        self.style.configure("Indicator.TLabel", font=("Segoe UI", label_size, "bold"))
        self.style.configure("History.TLabel", font=("Segoe UI", history_size))
        self.style.configure("HistoryValue.TLabel", font=("Segoe UI", history_size, "bold"))
        self.style.configure("Status.TLabel", font=("Segoe UI", label_size))

        self.style.configure("TButton", font=("Segoe UI", button_size, "bold"))
        for category in BUTTON_PALETTE:
            self.style.configure(f"{category}.TButton", font=("Segoe UI", button_size, "bold"))

        # O botão de mostrar/ocultar teclado acompanha a escala, mas continua
        # no tamanho de rótulo (discreto), não no de tecla.
        if hasattr(self, "_toggle_style"):
            self.style.configure(self._toggle_style, font=("Segoe UI", label_size), padding=(6, 2))

        self._update_display()

    def _configure_palette(self) -> None:
        """Same WCAG-verified palette as the LCD front (ui/shared/palette.py):
        ttkbootstrap's built-in colors are not guaranteed to meet WCAG AA."""
        for category, colors in BUTTON_PALETTE.items():
            self.style.configure(
                f"{category}.TButton",
                background=colors.background,
                foreground=colors.foreground,
            )
            # Pressed/focused states must stay perceivable without relying on
            # color alone: press inverts fg/bg, focus gets a bright border.
            self.style.map(
                f"{category}.TButton",
                background=[("pressed", colors.foreground), ("active", colors.background)],
                foreground=[("pressed", colors.background)],
                bordercolor=[("focus", "#FFFFFF")],
                relief=[("pressed", "sunken")],
            )

    def _update_display(self) -> None:
        """Truncate to what actually fits the current width, not a fixed count."""
        expr = format_expression_for_display(self.expression_var.get())
        res = self.result_var.get()

        # Capacity follows the current width and font size, so a bigger screen
        # shows a longer expression instead of truncating at a fixed count.
        width = self.root.winfo_width()
        sizes = font_sizes(self._scale)
        max_expr = visible_chars(width, sizes["expression"])
        max_res = visible_chars(width, sizes["result"])

        if len(expr) > max_expr:
            self.expression_disp_var.set("..." + expr[-(max_expr - 3):])
        else:
            self.expression_disp_var.set(expr)

        if len(res) > max_res:
            self.result_disp_var.set(".." + res[-(max_res - 2):])
        else:
            self.result_disp_var.set(res)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.speech.say("Calculadora pronta. Saida no monitor.")
        self.root.mainloop()
        self.speech.stop()

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.pack(fill=BOTH, expand=True)
        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(0, weight=0)  # top bar
        root_frame.rowconfigure(1, weight=1)  # main area
        root_frame.rowconfigure(2, weight=0)  # footer

        top_bar = ttk.Frame(root_frame)
        top_bar.grid(row=0, column=0, sticky=EW, pady=(0, 6))
        ttk.Label(top_bar, textvariable=self.mode_var, bootstyle="info", style="Indicator.TLabel").pack(side=LEFT, padx=6)
        ttk.Label(top_bar, textvariable=self.ctrl_var, bootstyle="warning", style="Indicator.TLabel").pack(side=LEFT, padx=6)
        ttk.Label(top_bar, textvariable=self.shift_var, bootstyle="success", style="Indicator.TLabel").pack(side=LEFT, padx=6)

        # Main area: calculator on the left, persistent history on the right.
        # Weights (not pixel widths) are what make this track the window size.
        main = ttk.Frame(root_frame)
        main.grid(row=1, column=0, sticky=NSEW)
        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=3, uniform="main")
        main.columnconfigure(1, weight=1, uniform="main")

        calculator = ttk.Frame(main)
        calculator.grid(row=0, column=0, sticky=NSEW, padx=(0, 10))
        calculator.columnconfigure(0, weight=1)
        calculator.rowconfigure(0, weight=2)  # display
        calculator.rowconfigure(1, weight=5)  # keypad

        display = ttk.Frame(calculator, bootstyle="secondary", padding=12)
        display.grid(row=0, column=0, sticky=NSEW, pady=(0, 10))
        display.columnconfigure(0, weight=1)
        display.rowconfigure(0, weight=1)
        display.rowconfigure(1, weight=2)

        self.expression_label = ttk.Label(
            display, textvariable=self.expression_disp_var, anchor=E,
            style="Display.TLabel", bootstyle="inverse-secondary",
        )
        self.expression_label.grid(row=0, column=0, sticky=NSEW)

        self.result_label = ttk.Label(
            display, textvariable=self.result_disp_var, anchor=E,
            style="Result.TLabel", bootstyle="inverse-secondary",
        )
        self.result_label.grid(row=1, column=0, sticky=NSEW)

        self.keypad_frame = ttk.Frame(calculator)
        self.keypad_frame.grid(row=1, column=0, sticky=NSEW)
        self.keypad_frame.rowconfigure(0, weight=1)
        self.keypad_frame.columnconfigure(0, weight=3, uniform="kp")
        self.keypad_frame.columnconfigure(1, weight=4, uniform="kp")

        left_frame = ttk.Frame(self.keypad_frame)
        left_frame.grid(row=0, column=0, sticky=NSEW, padx=(0, 8))
        for i in range(6):
            left_frame.rowconfigure(i, weight=1, uniform="row")
        for i in range(3):
            left_frame.columnconfigure(i, weight=1, uniform="col_left")

        right_frame = ttk.Frame(self.keypad_frame)
        right_frame.grid(row=0, column=1, sticky=NSEW)
        for i in range(6):
            right_frame.rowconfigure(i, weight=1, uniform="row")
        for i in range(4):
            right_frame.columnconfigure(i, weight=1, uniform="col_right")

        self._build_buttons(left_frame, LEFT_BUTTONS, is_left=True)
        self._build_buttons(right_frame, RIGHT_BUTTONS, is_left=False)

        self._build_history_panel(main)

        footer = ttk.Frame(root_frame, padding=(0, 6))
        footer.grid(row=2, column=0, sticky=EW, pady=(8, 0))
        # Discreto de propósito: estilo "link" (sem moldura) e fonte pequena,
        # para não roubar área do monitor. Continua focável por Tab e anunciado
        # por voz. A fonte acompanha a resolução em _apply_scale().
        self.toggle_btn = ttk.Button(
            footer, text=keypad_toggle_label(self.controls_visible),
            bootstyle="secondary-link", command=self._toggle_controls,
        )
        self._toggle_style = f"Compact.{self.toggle_btn.cget('style')}"
        self.toggle_btn.configure(style=self._toggle_style)
        self.toggle_btn.pack(side=LEFT, padx=(0, 10))
        ttk.Label(footer, textvariable=self.status_var, anchor=W, style="Status.TLabel").pack(
            side=LEFT, fill=X, expand=True, padx=10
        )
        ttk.Label(footer, text="Monitor HDMI", anchor=E, bootstyle="info", style="Status.TLabel").pack(side=RIGHT)

    def _build_buttons(self, container: ttk.Frame, rows: list, is_left: bool) -> None:
        for r, row in enumerate(rows):
            curr_col = 0
            for item in row:
                label, primary, secondary = item[0], item[1], item[2]
                shifted = item[3] if len(item) > 3 else None
                if not label:
                    curr_col += 1
                    continue

                btn_id = f"{primary}_{secondary}"
                button = ttk.Button(
                    container, text=label, bootstyle=button_style(primary),
                    command=lambda p=primary, s=secondary, sh=shifted: self._handle_token(p, s, sh),
                )

                cspan = 1
                if is_left:
                    if (r == 3 and primary == "inv(") or (r == 5 and primary == "Ctrl"):
                        cspan = 2
                elif r == 4 and primary == "0":
                    cspan = 2

                button.grid(row=r, column=curr_col, sticky=NSEW, padx=4, pady=4, columnspan=cspan)
                self.buttons[btn_id] = button
                curr_col += cspan

    def _build_history_panel(self, parent: ttk.Frame) -> None:
        """The extra area the monitor has over the LCD: history always visible
        instead of behind a dialog."""
        panel = ttk.Frame(parent, bootstyle="secondary", padding=10)
        panel.grid(row=0, column=1, sticky=NSEW)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        ttk.Label(
            panel, text="Historico", anchor=W, style="Indicator.TLabel",
            bootstyle="inverse-secondary",
        ).grid(row=0, column=0, sticky=EW, pady=(0, 8))

        self.history_frame = ttk.Frame(panel)
        self.history_frame.grid(row=1, column=0, sticky=NSEW)
        self.history_frame.columnconfigure(0, weight=1)

        self._refresh_history()

    def _refresh_history(self) -> None:
        for child in self.history_frame.winfo_children():
            child.destroy()

        if not self.state.history:
            ttk.Label(
                self.history_frame, text="Nenhuma operacao ainda.",
                anchor=W, style="History.TLabel",
            ).grid(row=0, column=0, sticky=EW)
            return

        recent = list(reversed(self.state.history))[:_HISTORY_VISIBLE_ROWS]
        for index, result in enumerate(recent):
            row = ttk.Frame(self.history_frame)
            row.grid(row=index, column=0, sticky=EW, pady=2)
            row.columnconfigure(0, weight=1)
            ttk.Label(
                row, text=format_expression_for_display(result.expression),
                anchor=W, style="History.TLabel",
            ).grid(row=0, column=0, sticky=EW)
            ttk.Label(
                row, text=f"= {result.display}", anchor=E, style="HistoryValue.TLabel",
            ).grid(row=1, column=0, sticky=EW)

    def _apply_controls_visibility(self) -> None:
        """Sincroniza teclado e rótulo do botão com self.controls_visible."""
        if self.controls_visible:
            self.keypad_frame.grid()
        else:
            self.keypad_frame.grid_remove()
        self.toggle_btn.configure(text=keypad_toggle_label(self.controls_visible))

    def _set_initial_focus(self) -> None:
        """Give Tab traversal a predictable starting point.

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

    # ------------------------------------------------------------------
    # Input handling (mirrors ui/lcd so both fronts behave identically)
    # ------------------------------------------------------------------

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
            main_name = spoken_token(primary)
            ctrl_name = spoken_token(secondary) if secondary else "Nenhuma"
            shift_name = spoken_token(shifted) if shifted else "Nenhuma"

            msg = f"Função {main_name}."
            msg += f" Com Controle ativo, função {ctrl_name}."
            msg += f" Com Shift ativo, função {shift_name}."
            self.speech.say(msg)
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

        # Chaining: after a result, an operator continues from Ans.
        if self.state.last_result and self.state.last_result.ok and token in operators:
            self.state.expression = "Ans"
            self.state.last_result = None

        if token in operators and self.state.expression:
            if self.state.expression[-1] in operators:
                self.speech.say("Substituindo")
                self.state.press("DEL")

        result = self.state.press(token)
        self.expression_var.set(self.state.expression)

        if result is None:
            self.speech.say(spoken_token(token))
            return

        if result.ok:
            self.result_var.set(result.display)
            self.speech.interrupt_and_say(f"Resultado {result.display}")
        else:
            # Same friendly text on screen and in speech, with the PRD §13
            # priority prefix (P1 -> "Erro", P2 -> "Aviso").
            friendly_msg = friendly_message(result.code, result.message)
            prefix = spoken_priority_prefix(result.code)
            self.result_var.set(f"{result.code}: {friendly_msg}")
            self.speech.interrupt_and_say(f"{prefix} {result.code.split('-')[-1]}. {friendly_msg}")

        self._refresh_history()

    def _update_keypad_labels(self) -> None:
        symbol_labels = {token: symbol.rstrip("(") for token, symbol in FUNCTION_DISPLAY_SYMBOLS.items()}
        ctrl_map = {**symbol_labels, "ln(": "ln", "nPr(": "nPr", "e": "e", "RECALL": "Últ. resp."}
        shift_map = {
            "logbase(": symbol_labels["logbase("], ",": ",",
            "RAD/DEG": "Deg/Rad", "RECALL": "Últ. resp.",
        }

        for row in LEFT_BUTTONS + RIGHT_BUTTONS:
            for item in row:
                label, primary, secondary = item[0], item[1], item[2]
                shifted = item[3] if len(item) > 3 else None
                if not label:
                    continue

                button = self.buttons.get(f"{primary}_{secondary}")
                if button is None:
                    continue

                new_text = label
                new_style = button_style(primary)
                if self.shift_active and shifted:
                    new_text = shift_map.get(shifted, shifted.rstrip("("))
                    new_style = "info"
                elif self.ctrl_active and secondary:
                    new_text = ctrl_map.get(secondary, secondary.rstrip("("))
                    new_style = "info"

                button.configure(text=new_text, bootstyle=new_style)

    def _recall_last_answer(self) -> None:
        """Re-announce/redisplay the last full result without recalculating."""
        result = self.state.recall_last_answer()
        if result.ok:
            self.result_var.set(result.display)
            self.speech.interrupt_and_say(f"Última resposta: {result.display}")
        else:
            friendly_msg = friendly_message(result.code, result.message)
            prefix = spoken_priority_prefix(result.code)
            self.speech.interrupt_and_say(f"{prefix} {result.code.split('-')[-1]}. {friendly_msg}")

    def _status_text(self) -> str:
        # This front only ever runs as the monitor output (the entry point
        # picks it precisely when DisplayMode.HDMI won), so report that
        # directly instead of re-querying the selector - re-reading it here
        # reported "LCD" while the monitor UI was on screen.
        ups_status = self.ups.read_status()
        return f"Saida visual: monitor | Energia: {ups_status.label}"


def main() -> None:
    CalculatorApp().run()


if __name__ == "__main__":
    main()
