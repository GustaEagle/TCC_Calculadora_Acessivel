"""Backwards-compatible re-export: the text now lives in software/ui_common.

Both fronts must announce the same PRD §13 code with the same meaning, so the
catalogue moved to ui_common/. This shim keeps existing imports working.
"""

from software.ui_common.error_messages import (
    ERROR_MESSAGES,
    friendly_message,
    spoken_priority_prefix,
)

__all__ = ["ERROR_MESSAGES", "friendly_message", "spoken_priority_prefix"]
