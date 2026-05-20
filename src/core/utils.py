from typing import Any


class EscapeStack(Exception):
    """Helper function to safely return back to surface while testing."""

    pass


def expand_set(symbol: Any, elements: list[str]) -> None:
    """
    Expands a 1D GAMSPy Set with additional elements,
    preserving existing records (and their text) and avoiding duplicates.
    """
    updated_records = []
    existing_keys = set()

    # 1. Extract existing elements AND their text
    if symbol.records is not None and not symbol.records.empty:
        # allowing .fillna("") to safely inject empty strings!
        df = symbol.records.astype(object).fillna("")

        for row in df.values.tolist():
            uni = row[0]
            text = row[1] if len(row) > 1 else ""

            updated_records.append((uni, text))
            existing_keys.add(uni)

    # 2. Append the new elements
    for new_el in elements:
        if new_el not in existing_keys:
            # Pair new elements with a blank description to match the tuple format
            updated_records.append((new_el, ""))
            existing_keys.add(new_el)  # Prevent duplicates within the new list itself

    # 3. Update the GAMSPy symbol with the combined list of tuples
    symbol.setRecords(updated_records)
