from typing import Iterable


def expand_set(symbol, elements: Iterable) -> None:
    """
    Expands a 1D GAMSPy Set with additional elements,
    preserving any existing records and avoiding duplicates.
    """
    # 1. Extract existing elements from the DataFrame (column 0 is usually 'uni')
    if symbol.records is not None and not symbol.records.empty:
        existing = set(symbol.records.iloc[:, 0])
    else:
        existing = set()

    # 2. Perform a union to ensure all elements are unique
    updated_elements = list(existing | set(elements))

    # 3. Update the GAMSPy symbol with the combined list
    symbol.setRecords(updated_elements)
