# dumpsol1_mod.py
#  *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * DUMPSOLV.MOD outputs the actual solution values
# *  Dumps output SET, SCALARS, PARAMETER, TABLE
# *
# *  1   - type indicator = 'L'evel/'M'arginal
# *  2-n - for rest of line = component names
# *
# *      - Note that (declaration) is not output
# *      - $BATINCLUDE dumpsol.mod ITEM1 ITEM2 ... must fit on one line
# *
# *=============================================================================*
# *GaG Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

import pandas as pd

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class Dumpsol1Mod(GamsClass):
    """Python translation of dumpsol1.mod."""

    module_name: str = "dumpsol1_mod"
    gams_source: str = "dumpsol1.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
        arg7: str = "",
        arg8: str = "",
        arg9: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.symbols = [
            s for s in (arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9) if s
        ]
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        dump = self.tc.dump0.toValue()
        assert isinstance(dump, float)
        self.tc.enqueue(
            self.exec_dumpsol1,
            # TODO: not sure how to handle soldump without knowing how post-solve phase is executed.
            # out=self.tc.soldump,
            out=Path("SOLDUMP"),
            whtype=self.arg1,
            dump0=int(dump),
            symbols=self.symbols,
        )

    def exec_dumpsol1(
        self: Dumpsol1Mod,
        out: TextIO | Path,
        whtype: str,
        dump0: int,
        symbols: list[str],
    ) -> None:
        # TODO: needs to change
        if isinstance(out, Path):
            out = out.open("a", encoding="utf-8")

        preditem = ""

        for symbol_name in symbols:
            if symbol_name not in self.tc.container.listSymbols():
                out.write(f"{'*** UNKNOWN':>20}{'NAME':>6}{symbol_name:>10}\n")
                preditem = "unknown"
                continue

            symbol = self.tc.container[symbol_name]
            dim = symbol.dimension

            if dim == 0:
                _write_scalar(
                    out, symbol_name, symbol, print_header=preditem != "scalar"
                )
                preditem = "scalar"
            elif dim == 1:
                _write_parameter_1d(out, symbol_name, symbol)
                preditem = "parameter"
            elif dim == 2:
                _write_parameter_2d(out, symbol_name, symbol)
                preditem = "parameter"
            elif dim >= 3:
                _write_table(out, dump0, whtype, symbol_name, symbol)
                preditem = "table"


def _symbol_text(symbol: Any) -> str:
    return getattr(symbol, "description", "")


_SUFFIX_COLUMNS = {
    "L": "level",
    "M": "marginal",
    "LO": "lower",
    "UP": "upper",
    "S": "scale",
}


def _value_column(symbol: Any, whtype: str | None = None) -> str:
    """Pick the records column holding the values to dump.

    Decided from the columns actually present rather than by sniffing attributes
    on the symbol: a Parameter's records carry ``value`` while a Variable's carry
    ``level``/``marginal``, and ``hasattr(symbol, "value")`` does not reliably
    tell the two apart. It also handles the whtypes that name no suffix at all --
    dumpsol.mod calls ``dumpsol1.mod 'T' VARACT`` on a Parameter, which used to
    map to "level" and raise KeyError.
    """
    records = getattr(symbol, "records", None)
    columns = set(records.columns) if records is not None else set()

    if whtype:
        suffix = _SUFFIX_COLUMNS.get(whtype.upper())
        if suffix is not None and suffix in columns:
            return suffix

    if "value" in columns:
        return "value"

    return _SUFFIX_COLUMNS.get((whtype or "").upper(), "level")


def _format_value(value: Any) -> str:
    try:
        return f"{float(value):<10.5g}"
    except Exception:
        return f"{value!s:<10}"


def _nonzero(value: Any) -> bool:
    try:
        return float(value) != 0.0
    except Exception:
        return bool(value)


def _write_scalar(
    out: TextIO,
    symbol_name: str,
    symbol: Any,
    *,
    print_header: bool,
) -> None:
    if print_header:
        out.write(f"\n{' ':9}SCALARS\n")

    value = symbol.toValue() if hasattr(symbol, "toValue") else 0
    out.write(f"{' ':15}{symbol_name:<10}/ {_format_value(value)} /\n")


def _write_parameter_1d(out: TextIO, symbol_name: str, symbol: Any) -> None:
    records = symbol.records
    if records is None or records.empty:
        return

    domain_cols = symbol.domain_labels
    value_col = _value_column(symbol)
    row_col = domain_cols[0]

    rows = records[records[value_col].map(_nonzero)]
    if rows.empty:
        return

    out.write(f"\n{' ':9}PARAMETER{symbol_name:>10}'{_symbol_text(symbol):40}' /\n")
    out.writelines(
        f"{' ':15}{row[row_col]!s:<29}{_format_value(row[value_col])}\n"
        for _, row in rows.iterrows()
    )
    out.write(f"{'':69}/\n\n")


def _write_parameter_2d(out: TextIO, symbol_name: str, symbol: Any) -> None:
    records = symbol.records
    if records is None or records.empty:
        return

    domain_cols = symbol.domain_labels
    value_col = _value_column(symbol)

    reg_col = domain_cols[0]
    row_col = domain_cols[1]

    rows = records[records[value_col].map(_nonzero)]
    if rows.empty:
        return

    out.write(f"\n{' ':9}PARAMETER{symbol_name:>10}'{_symbol_text(symbol):40}' /\n")
    for _, row in rows.iterrows():
        item = f"{row[reg_col]!s}.{row[row_col]!s}"
        out.write(f"{' ':15}{item:<29}{_format_value(row[value_col])}\n")
    out.write(f"{'':69}/\n\n")


def _write_table(
    out: TextIO, dump0: int, whtype: str, symbol_name: str, symbol: Any
) -> None:
    records = symbol.records
    if records is None or records.empty:
        return

    value_col = _value_column(symbol, whtype)
    domain_cols = symbol.domain_labels

    if len(domain_cols) < 3:
        return

    reg_col = domain_cols[0]
    col_col = domain_cols[1]
    row_cols = domain_cols[2:]

    active_records = records[records[value_col].map(_nonzero)]
    if active_records.empty:
        return

    cols = list(dict.fromkeys(active_records[col_col].astype(str).tolist()))
    active_keys = {
        tuple(row[col] for col in [reg_col, *row_cols])
        for _, row in active_records.iterrows()
    }

    if whtype in ("L", "M"):
        title = f"{whtype}: Solution Reference "
        at = 24
    elif whtype == "P":
        _write_parameter_table(
            out, dump0, symbol_name, symbol, records, domain_cols, value_col
        )
        return
    else:
        title = "TABLE"
        at = 44

    out.write(f"\n{' ':9}{title}{symbol_name:<10} '{_symbol_text(symbol):40}'\n")
    _write_column_header(out, cols, at)

    grouped = records.groupby([reg_col, *row_cols], dropna=False)
    for key, group in grouped:
        key_tuple = key if isinstance(key, tuple) else (key,)
        if key_tuple not in active_keys:
            continue

        reg = key_tuple[0]
        row_key = key_tuple[1:]
        row_label = ".".join(str(v) for v in row_key)
        row_values = {str(r[col_col]): r[value_col] for _, r in group.iterrows()}

        if not dump0 and not any(_nonzero(v) for v in row_values.values()):
            continue

        prefix = f"{reg}.{row_label}" if row_label else f"{reg}"
        _write_table_row(out, prefix, cols, row_values, at)

    out.write("\n")


def _write_column_header(out: TextIO, cols: list[str], at: int) -> None:
    out.write(" " * at)
    out.writelines(f"{col:<11}" for col in cols[:19])
    out.write("\n")


def _write_table_row(
    out: TextIO,
    prefix: str,
    cols: list[str],
    row_values: dict[str, Any],
    at: int,
) -> None:
    start = 0
    first = True

    while start < len(cols):
        chunk = cols[start : start + 19]
        if first:
            out.write(f"{'':4}{prefix:<{at - 4}}")
            first = False
        else:
            out.write(f"{'':10}{cols[start]:<4}{'':{at - 14}}+++")

        for col in chunk:
            value = row_values.get(col, 0)
            out.write(_format_value(value) if _nonzero(value) else " " * 11)
        out.write("\n")
        start += 19


def _write_parameter_table(
    out: TextIO,
    dump0: int,
    symbol_name: str,
    symbol: Any,
    records: pd.DataFrame,
    domain_cols: list[str],
    value_col: str,
) -> None:
    reg_col = domain_cols[0]
    col_col = domain_cols[1]
    row_cols = domain_cols[2:]

    active_records = records[records[value_col].map(_nonzero)]
    if active_records.empty:
        return

    rows_to_print = records if dump0 else active_records

    out.write(f"\n{' ':9}PARAMETER{symbol_name:>10} '{_symbol_text(symbol):40}'\n")
    for _, row in rows_to_print.iterrows():
        value = row[value_col]
        if not dump0 and not _nonzero(value):
            continue

        row_part = ".".join(str(row[col]) for col in row_cols)
        parts = [str(row[reg_col]), str(row[col_col])]
        if row_part:
            parts.append(row_part)

        key = ".".join(parts)
        out.write(f"{' ':15}{key:<51}{_format_value(value)}\n")
    out.write("\n")
