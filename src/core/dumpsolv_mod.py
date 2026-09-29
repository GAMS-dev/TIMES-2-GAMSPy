# dumpsolv_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * DUMPSOLV.MOD outputs the actual solution values when vintage index
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

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class DumpsolvMod(GamsClass):
    """Python translation of dumpsolv.mod."""

    module_name: str = "dumpsolv_mod"
    gams_source: str = "dumpsolv.mod"

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
        self.tc.enqueue(
            self.exec_dumpsolv,
            # TODO: not sure how to handle soldump without knowing how post-solve phase is executed.
            # out=self.tc.soldump,
            out=Path("SOLDUMP"),
            whtype=self.arg1,
            symbols=self.symbols,
        )

    def exec_dumpsolv(
        self: DumpsolvMod,
        out: TextIO | Path,
        whtype: str,
        symbols: list[str],
    ) -> None:
        # TODO: needs to change
        if isinstance(out, Path):
            out = out.open("a", encoding="utf-8")

        for symbol_name in symbols:
            if symbol_name not in self.tc.container.listSymbols():
                out.write(f"{'*** UNKNOWN':>20}{'NAME':>6}{symbol_name:>10}\n")
                continue

            symbol = self.tc.container[symbol_name]
            dim = int(symbol.dimension)

            if dim < 4:
                continue
            if dim > 9:
                logger.warning("Unsupported dimension %s for %s", dim, symbol)
                continue

            _write_vtable(
                out=out,
                container=self.tc.container,
                whtype=whtype,
                symbol_name=symbol_name,
                symbol=symbol,
            )


def _value_column(symbol: Any, whtype: str | None = None) -> str:
    if hasattr(symbol, "value") and not hasattr(symbol, "level"):
        return "value"

    if not whtype:
        return "value"

    mapping = {
        "L": "level",
        "M": "marginal",
        "LO": "lower",
        "UP": "upper",
        "S": "scale",
    }

    return mapping.get(whtype.upper(), "level")


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


def _coef_pvt(container: Any, reg: Any, fil: Any) -> float:
    if "COEF_PVT" not in container.listSymbols():
        return 1.0

    coef = container["COEF_PVT"]
    records = coef.records
    if records is None or records.empty:
        return 1.0

    domain_cols = coef.domain_labels
    value_col = _value_column(coef)

    if len(domain_cols) < 2:
        return 1.0

    matched = records[
        (records[domain_cols[0]].astype(str) == str(reg))
        & (records[domain_cols[1]].astype(str) == str(fil))
    ]

    if matched.empty:
        return 1.0

    try:
        return float(matched.iloc[0][value_col])
    except Exception:
        return 1.0


def _write_vtable(
    *,
    out: TextIO,
    container: Any,
    whtype: str,
    symbol_name: str,
    symbol: Any,
) -> None:
    records = symbol.records
    if records is None or records.empty:
        return

    domain_cols = symbol.domain_labels
    value_col = _value_column(symbol, whtype)

    if value_col not in records.columns:
        out.write(f"{'*** UNKNOWN':>20}{'NAME':>6}{symbol_name:>10}\n")
        return

    if len(domain_cols) < 4:
        return

    reg_col = domain_cols[0]
    # vintage_col = domain_cols[1]
    year_col = domain_cols[2]
    row_cols = domain_cols[3:]

    active_records = records[records[value_col].map(_nonzero)]
    if active_records.empty:
        return

    years = list(dict.fromkeys(active_records[year_col].astype(str).tolist()))
    active_keys = {
        tuple(row[col] for col in [reg_col, *row_cols])
        for _, row in active_records.iterrows()
    }

    description = getattr(symbol, "description", "")

    out.write(
        f"\n{' ':9}{whtype}: Solution Reference {symbol_name:<10} '{description:40}'\n"
    )
    _write_year_header(out, years)

    grouped = records.groupby([reg_col, *row_cols], dropna=False)
    for key, group in grouped:
        key_tuple = key if isinstance(key, tuple) else (key,)
        if key_tuple not in active_keys:
            continue

        reg = key_tuple[0]
        row_key = key_tuple[1:]
        row_label = ".".join(str(v) for v in row_key)

        values_by_year: dict[str, float] = {}
        for year, year_group in group.groupby(year_col, dropna=False):
            year_label = str(year)

            if year_label not in years:
                continue

            z = float(year_group[value_col].sum())

            if whtype == "M":
                disc = _coef_pvt(container, reg, year)
                z = z / disc

            values_by_year[year_label] = z

        prefix = f"{reg}.{row_label}" if row_label else str(reg)
        _write_vtable_row(out, prefix, years, values_by_year)

    out.write("\n")


def _write_year_header(out: TextIO, years: list[str]) -> None:
    out.write(" " * 34)
    for year in years[:19]:
        out.write(f"{year:<11}")
    out.write("\n")


def _write_vtable_row(
    out: TextIO,
    prefix: str,
    years: list[str],
    values_by_year: dict[str, Any],
) -> None:
    start = 0
    first = True

    while start < len(years):
        chunk = years[start : start + 19]
        if first:
            out.write(f"{'':4}{prefix:<30}")
            first = False
        else:
            out.write(f"{'':10}{years[start]:<4}{'':16}+++")

        for year in chunk:
            value = values_by_year.get(year, 0)
            out.write(_format_value(value) if _nonzero(value) else " " * 11)
        out.write("\n")
        start += 19
