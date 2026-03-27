"""Operational metrics helper functions."""

from flask import current_app


def _safe_store():
    return current_app.extensions.get("ops_metrics")


def increment_counter(name: str, delta: int = 1):
    store = _safe_store()
    if not store:
        return
    store[name] = int(store.get(name, 0)) + int(delta)


def increment_labeled_counter(name: str, label: str, delta: int = 1):
    store = _safe_store()
    if not store:
        return
    values = store.get(name)
    if not isinstance(values, dict):
        values = {}
        store[name] = values
    values[label] = int(values.get(label, 0)) + int(delta)

