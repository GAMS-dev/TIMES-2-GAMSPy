# utils.py
# Put shared Python helpers here. Keep this file Python-native.

from typing import Iterable

from gamspy import Set


def add_elements_to_1d_set(symbol: Set, elements: Iterable) -> None:
    """
    Helper to extend a 1D GAMSPy Set with additional elements, preserving existing records.
    """
    # NOTE: keep your existing implementation here if you already have one.
    # This skeleton uses a conservative approach.
    try:
        existing = set(symbol.records) if symbol.records is not None else set()
    except Exception:
        existing = set()

    new = list(existing | set(elements))
    symbol.setRecords(new)
