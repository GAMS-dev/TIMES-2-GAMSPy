from collections.abc import Sequence
from typing import Any


class EscapeStack(Exception):
    """Helper function to safely return back to surface while testing."""

    pass


def expand_set(symbol: Any, elements: Sequence[str | tuple[str, str]]) -> None:
    """
    Expands a 1D GAMSPy Set with additional elements,
    preserving existing records (and their text) and avoiding duplicates.
    Accepts elements as a Sequence of strings or (element, text) tuples.
    """
    updated_records = []
    existing_keys = set()

    # 1. Extract existing elements AND their text
    if symbol.records is not None and not symbol.records.empty:
        df = symbol.records.astype(object).fillna("")

        for row in df.values.tolist():
            uni = row[0]
            text = row[1] if len(row) > 1 else ""

            updated_records.append((uni, text))
            existing_keys.add(uni)

    # 2. Append the new elements (Handles strings or tuples dynamically)
    for item in elements:
        if isinstance(item, tuple):
            new_el, new_text = item
        else:
            new_el, new_text = item, ""

        # Avoid duplicates
        if new_el not in existing_keys:
            updated_records.append((new_el, new_text))
            existing_keys.add(new_el)

    # 3. Update the GAMSPy symbol with the combined list of tuples
    symbol.setRecords(updated_records)
