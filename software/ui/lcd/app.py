"""ttkbootstrap front-end for the 4.3 inch Waveshare LCD.

The LCD is *only a screen*: there is no on-screen keypad and no buttons at all.
Every input arrives from the physical 6x7 keyboard (RF-05), so the whole 800x480
panel is spent on what the user needs to read - the expression, the result, and
the active modifiers.

History is reached by keyboard (Ctrl + Ans), never by a button; it takes over
the display area while open and is also announced by voice.
"""

from __future__ import annotations

import logging

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import BOTH, E, EW, LEFT, NSEW, W
except ImportError as exc:  # pragma: no cover - user-facing startup guard
    raise SystemExit(
        "Instale as dependencias com: python -m pip install -r software/requirements.txt"
    ) from exc

from software.accessibility.speech import SpeechService
from software.core import CalculatorState
from software.hw_platform.display import DisplayMode
from software.hw_platform.keyboard import KeyboardAdapter
from software.ui.shared.error_messages import friendly_message, spoken_priority_prefix
from software.ui.shared.formatting import format_expression_for_display
from software.ui.shared.history import recent_entries, spoken_history
from software.ui.shared.keypad import HISTORY_TOKEN, spoken_token
from software.ui.shared.palette import DISPLAY_BACKGROUND, DISPLAY_FOREGROUND
from software.ui.shared.video_watch import VideoOutputWatch

logger = logging.getLogger(__name__)

# Painel Waveshare 4,3": tamanho fixo, não redimensionável.
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 480

FONT_SIZES = {
    "expression": 44,
    "result": 96,
    "indicator": 14,
    "history": 22,
}

# Truncamento do display para as fontes acima nos 800x480.
MAX_EXPRESSION_CHARS = 26
MAX_RESULT_CHARS = 14

_HISTORY_VISIBLE_ROWS = 6


class CalculatorApp:
    """Display-only shell for the 4.3 inch 800x480 LCD."""

    def __init__(
        self,
        state: CalculatorState | None = None,
        speech: SpeechService | None = None,
    ) -> None:
        # Injected when the other front hands over (RF-09): reusing the same
        # state keeps the expression, history and angle mode across the swap,
        # and reusing the SpeechService avoids restarting the TTS worker.
        self.state = state or CalculatorState()
        self.speech = speech or SpeechService()
        self.keyboard = KeyboardAdapter()

        self.root = ttk.Window(themename="darkly")
        self.root.title("Calculadora Cientifica Acessivel")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)

        self.style = ttk.Style()

        self.ctrl_active = False
        self.shift_active = False
        self.history_open = False

        self.expression_var = ttk.StringVar(value="")
        self.result_var = ttk.StringVar(value="Pronto")

        self.mode_var = ttk.StringVar(value="DEG")
        self.ctrl_var = ttk.StringVar(value="")
        self.shift_var = ttk.StringVar(value="")

        self.expression_disp_var = ttk.StringVar(value="")
        self.result_disp_var = ttk.StringVar(value="")

        self._configure_styles()
        self._build_layout()
        self._bind_keyboard()
        self.root.focus_set()

        # RF-09: the external monitor is always plugged in with the calculator
        # already running, so this front has to notice it and step aside.
        self.video_watch = VideoOutputWatch(self.root, self.speech, DisplayMode.LCD)

        self.expression_var.trace_add("write", lambda *_: self._update_display())
        self.result_var.trace_add("write", lambda *_: self._update_display())

    def _configure_styles(self) -> None:
        """Fontes fixas: o painel tem tamanho conhecido e não redimensiona."""
        self.style.configure(
            "Display.TLabel", font=("Segoe UI", FONT_SIZES["expression"]), padding=8,
            foreground=DISPLAY_FOREGROUND, background=DISPLAY_BACKGROUND,
        )
        self.style.configure(
            "Result.TLabel", font=("Segoe UI", FONT_SIZES["result"], "bold"), padding=8,
            foreground=DISPLAY_FOREGROUND, background=DISPLAY_BACKGROUND,
        )
        self.style.configure("Indicator.TLabel", font=("Segoe UI", FONT_SIZES["indicator"], "bold"))
        self.style.configure("History.TLabel", font=("Segoe UI", FONT_SIZES["history"]))
        self.style.configure(
            "HistoryValue.TLabel", font=("Segoe UI", FONT_SIZES["history"], "bold"),
        )

    def run(self) -> DisplayMode | None:
        """Run until closed.

        Returns the mode that should take over when the video output changed
        under us, or None when the user simply quit.
        """
        self.speech.say("Calculadora pronta")
        self.video_watch.start()
        self.root.mainloop()

        if self.video_watch.changed_to is None:
            self.speech.stop()
        return self.video_watch.changed_to

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self.root, padding=10)
        root_frame.pack(fill=BOTH, expand=True)
        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(0, weight=0)  # indicadores
        root_frame.rowconfigure(1, weight=1)  # display / histórico

        indicators = ttk.Frame(root_frame)
        indicators.grid(row=0, column=0, sticky=EW, pady=(0, 6))
        ttk.Label(indicators, textvariable=self.mode_var, bootstyle="info", style="Indicator.TLabel").pack(side=LEFT, padx=5)
        ttk.Label(indicators, textvariable=self.ctrl_var, bootstyle="warning", style="Indicator.TLabel").pack(side=LEFT, padx=5)
        ttk.Label(indicators, textvariable=self.shift_var, bootstyle="success", style="Indicator.TLabel").pack(side=LEFT, padx=5)

        # Display e histórico ocupam a MESMA célula; o histórico é levantado por
        # cima quando aberto (Ctrl + Ans) e baixado ao fechar.
        self.stack = ttk.Frame(root_frame)
        self.stack.grid(row=1, column=0, sticky=NSEW)
        self.stack.columnconfigure(0, weight=1)
        self.stack.rowconfigure(0, weight=1)

        self.display = ttk.Frame(self.stack, bootstyle="secondary", padding=12)
        self.display.grid(row=0, column=0, sticky=NSEW)
        self.display.columnconfigure(0, weight=1)
        self.display.rowconfigure(0, weight=1)
        self.display.rowconfigure(1, weight=2)

        ttk.Label(
            self.display, textvariable=self.expression_disp_var, anchor=E,
            style="Display.TLabel", bootstyle="inverse-secondary",
        ).grid(row=0, column=0, sticky=NSEW)

        ttk.Label(
            self.display, textvariable=self.result_disp_var, anchor=E,
            style="Result.TLabel", bootstyle="inverse-secondary",
        ).grid(row=1, column=0, sticky=NSEW)

        self.history_view = ttk.Frame(self.stack, bootstyle="secondary", padding=12)
        self.history_view.grid(row=0, column=0, sticky=NSEW)
        self.history_view.columnconfigure(0, weight=1)
        self.display.tkraise()

    def _update_display(self) -> None:
        expr = format_expression_for_display(self.expression_var.get())
        res = self.result_var.get()

        if len(expr) > MAX_EXPRESSION_CHARS:
            self.expression_disp_var.set("..." + expr[-(MAX_EXPRESSION_CHARS - 3):])
        else:
            self.expression_disp_var.set(expr)

        if len(res) > MAX_RESULT_CHARS:
            self.result_disp_var.set(".." + res[-(MAX_RESULT_CHARS - 2):])
        else:
            self.result_disp_var.set(res)

    # ------------------------------------------------------------------
    # Histórico (só por teclado: Ctrl + Ans)
    # ------------------------------------------------------------------

    def _toggle_history(self) -> None:
        if self.history_open:
            self._close_history()
        else:
            self._open_history()

    def _open_history(self) -> None:
        for child in self.history_view.winfo_children():
            child.destroy()

        ttk.Label(
            self.history_view, text="Historico", anchor=W,
            style="Indicator.TLabel", bootstyle="inverse-secondary",
        ).grid(row=0, column=0, sticky=EW, pady=(0, 6))

        recent = recent_entries(self.state.history, _HISTORY_VISIBLE_ROWS)
        if not recent:
            ttk.Label(
                self.history_view, text="Nenhuma operacao realizada.", anchor=W,
                style="History.TLabel", bootstyle="inverse-secondary",
            ).grid(row=1, column=0, sticky=EW)
            self.speech.interrupt_and_say(spoken_history(recent))
        else:
            for index, result in enumerate(recent, start=1):
                row = ttk.Frame(self.history_view)
                row.grid(row=index, column=0, sticky=EW, pady=1)
                row.columnconfigure(0, weight=1)
                ttk.Label(
                    row, text=format_expression_for_display(result.expression), anchor=W,
                    style="History.TLabel",
                ).grid(row=0, column=0, sticky=EW)
                ttk.Label(
                    row, text=f"= {result.display}", anchor=E, style="HistoryValue.TLabel",
                ).grid(row=0, column=1, sticky=E)

            self.speech.interrupt_and_say(spoken_history(recent))

        self.history_view.tkraise()
        self.history_open = True

    def _close_history(self) -> None:
        self.display.tkraise()
        self.history_open = False
        self.speech.say("Histórico fechado")

    # ------------------------------------------------------------------
    # Entrada (somente teclado físico - RF-05)
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
        # A tecla Ans carrega o histórico como função de Ctrl (ver ui/shared/keypad.py),
        # então o atalho é o mesmo no PC e na matriz 6x7.
        if primary == "Ans" and secondary is None:
            secondary = HISTORY_TOKEN

        if primary == "Ctrl":
            self.ctrl_active = not self.ctrl_active
            self.ctrl_var.set("CTRL" if self.ctrl_active else "")
            self.speech.say("Controle ativo" if self.ctrl_active else "Controle desativado")
            return

        if primary == "Shift":
            self.shift_active = not self.shift_active
            self.shift_var.set("SHIFT" if self.shift_active else "")
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
        elif self.ctrl_active and secondary:
            token = secondary
            self.ctrl_active = False
            self.ctrl_var.set("")

        if token == HISTORY_TOKEN:
            self._toggle_history()
            return

        # Qualquer outra tecla com o histórico aberto volta para o display.
        if self.history_open:
            self._close_history()

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


def main() -> None:
    CalculatorApp().run()


if __name__ == "__main__":
    main()
