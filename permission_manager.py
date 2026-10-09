"""
FRIDAY PERMISSION & SAFETY MANAGER

Central confirmation layer for sensitive local actions.
"""

class PermissionManager:

    CONFIRM_WORDS = {
        "yes", "yeah", "yep", "confirm", "confirmed",
        "do it", "proceed", "go ahead", "sure", "okay", "ok"
    }

    CANCEL_WORDS = {
        "no", "nope", "cancel", "stop", "don't", "do not"
    }

    def __init__(self):
        self.pending_command = None

    def _normalize(self, text):
        return " ".join(text.lower().strip().split())

    def is_confirmation(self, text):
        return self._normalize(text) in self.CONFIRM_WORDS

    def is_cancellation(self, text):
        return self._normalize(text) in self.CANCEL_WORDS

    def requires_confirmation(self, command):
        text = self._normalize(command)

        sensitive_patterns = (
            "close browser",
            "close the browser",
            "close window",
            "close the current window",
            "close the active window",
            "close this window",
            "shutdown",
            "shut down",
            "restart computer",
            "restart the computer",
            "delete file",
            "delete the file",
            "remove file",
            "remove the file",
            "empty recycle bin",
            "empty the recycle bin",
        )

        return any(pattern in text for pattern in sensitive_patterns)

    def request_confirmation(self, command):
        self.pending_command = command
        return (
            f"That action can change or close something on your computer. "
            f"Do you want me to proceed?"
        )

    def handle_response(self, response):
        if self.is_confirmation(response):
            command = self.pending_command
            self.pending_command = None
            return "confirmed", command

        if self.is_cancellation(response):
            self.pending_command = None
            return "cancelled", None

        return None, None

    def has_pending(self):
        return self.pending_command is not None

    def clear(self):
        self.pending_command = None
