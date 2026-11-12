"""A request-scoped message the phone displays instead of the action result."""
from threading import local

_state = local()


def set(text: str) -> None:
    _state.pending = {"D8aznm56": "1", "5oHZM9zK": "6", "Wk1v6upb": str(text).replace("@", " ")}


def take() -> dict | None:
    message = getattr(_state, "pending", None)
    clear()
    return message


def clear() -> None:
    if hasattr(_state, "pending"):
        del _state.pending
