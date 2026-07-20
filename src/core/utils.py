from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Literal

import pandas as pd
from gamspy import Parameter, SpecialValues
from gamspy.math import rpower

if TYPE_CHECKING:
    from gamspy import Alias, Set, SpecialValues

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass


class EscapeStack(Exception):
    """Helper function to safely return back to surface while testing."""

    pass


def expand_set(symbol: Set | Alias, elements: Sequence[str | tuple[str, str]]) -> None:
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


def add_records(symbol: Parameter, elements: pd.DataFrame) -> None:
    assert symbol.records is not None
    existing_records = symbol.records
    elements.columns = existing_records.columns

    merged_records = pd.concat(
        [existing_records, elements], ignore_index=True
    ).drop_duplicates()
    symbol.setRecords(merged_records)


def resolve_ctst(exp: Any, val: Literal["", "**EPS", "**0", "1"]) -> Any:
    match val:
        case "":
            return exp
        case "**EPS":
            return rpower(exp, SpecialValues.EPS)
        case "**0":
            return rpower(exp, 0)
        case "1":
            raise ValueError(f"Unexpected value {val} for CTST.")


def apply_sw_tags(env: CompileEnvironment, g: TimesModelClass) -> None:
    if (
        env.sw_tags
        == "SET EQ 'ES' SET VAR 'VAS' SET SWD ',WW' SET SWTD ',T,WW' SET SWS ',W)' SET SOW ',SOW' SET SWT ',SW_T(T,SOW)' SET VART 'SUM(SW_TSW(SOW,T,W),VAS' SET VARV 'SUM(SW_TSW(SOW,V,W),VAS' SET VARM 'SUM(SW_TSW(SOW,MODLYEAR,W),VAS'"
    ):
        env.set_scoped("eq", "ES")
        env.set_scoped("var", "VAS")
        env.set_scoped("swd", ",WW")
        env.set_scoped("swd_GP", (g.ww,))
        env.set_scoped("swtd", ",T,WW")
        env.set_scoped("swtd_GP", (g.t, g.ww))
        env.set_scoped("sws", ",W)")
        env.set_scoped("sws_GP", (g.w,))
        env.set_scoped("sow", ",SOW")
        env.set_scoped("sow_GP", (g.Sow,))
        env.set_scoped("swt", ",SW_T(T,SOW)")
        env.set_scoped("swt_GP", (g.SwT[g.t, g.Sow],))
        env.set_scoped("vart", "SUM(SW_TSW(SOW,T,W),VAS")
        env.set_scoped("vart_GP", ("VAS", g.SwTsw[g.Sow, g.t, g.w]))
        env.set_scoped("varv", "SUM(SW_TSW(SOW,V,W),VAS")
        env.set_scoped("varv_GP", ("VAS", g.SwTsw[g.Sow, g.v, g.w]))
        env.set_scoped("varm", "SUM(SW_TSW(SOW,MODLYEAR,W),VAS")
        env.set_scoped("varm_GP", ("VAS", g.SwTsw[g.Sow, g.Modlyear, g.w]))
    else:
        raise ValueError(f"Unknown value in sw_tags: {env.sw_tags}")


def apply_sw_notags(env: CompileEnvironment) -> None:
    """Applies a list of compile time variable changes"""
    if (
        env.sw_notags
        == "SET EQ 'EQ' SET VAR 'VAR' SET SWS '' SET SOW '' SET SWT '' SET SWD '' SET SWTD '' SET SWSW '' SET VART 'VAR' SET VARV 'VAR' SET VARM 'VAR' SET VARTT VAR"
    ):
        env.set_scoped("eq", "EQ")
        env.set_scoped("var", "VAR")
        env.set_scoped("sws", "")
        env.set_scoped("sws_GP", ())
        env.set_scoped("sow", "")
        env.set_scoped("sow_GP", tuple())
        env.set_scoped("swt", "")
        env.set_scoped("swt_GP", tuple())
        env.set_scoped("swd", "")
        env.set_scoped("swd_GP", tuple())
        env.set_scoped("swtd", "")
        env.set_scoped("swtd_GP", tuple())
        env.set_scoped("swsw", "")
        env.set_scoped("vart", "VAR")
        env.set_scoped("vart_GP", ("VAR", None))
        env.set_scoped("varv", "VAR")
        env.set_scoped("varv_GP", ("VAR", None))
        env.set_scoped("varm", "VAR")
        env.set_scoped("varm_GP", ("VAR", None))
        env.set_scoped("vartt", "VAR")
        env.set_scoped("vartt_GP", ("VAR", None))
    else:
        raise ValueError(f"Unknown value in sw_notags: {env.sw_notags}")


def apply_witspine(env: CompileEnvironment) -> None:
    # rf"SET EQS '{self.env.eq}' SET EQ 'Q'")
    env.set_scoped("eqs", env.eq)
    env.set_scoped("eq", "Q")


def apply_ewispine(env: CompileEnvironment) -> None:
    # rf"SET EQ {self.env.eq}"
    env.set_scoped("eq", env.eq)


def apply_sw_stvars(
    env: CompileEnvironment, g: TimesModelClass, witspine: bool = False
) -> None:
    if witspine:
        apply_witspine(env=env)

    if (
        env.sw_stvars
        == "SET VARTT 'SUM(SW_TSW(SOW,TT,W),VAS' SET SWSW SW_TSW(SOW,T,WW),"
    ):
        env.set_scoped("vartt", "SUM(SW_TSW(SOW,TT,W),VAS")
        env.set_scoped("vartt_GP", ("VAS", g.SwTsw[g.Sow, g.tt, g.w]))
        env.set_scoped("swsw", "SW_TSW(SOW,T,WW),")
    else:
        raise ValueError(f"Unknown value in sw_stvars: {env.sw_stvars}")


def generate_equation(lhs: Any, type: Literal["E", "N", "L", "G"], rhs: Any) -> Any:
    match type:
        case "E" | "N":
            return lhs == rhs
        case "L":
            return lhs <= rhs
        case "G":
            return lhs >= rhs
        case _:
            raise ValueError(
                f"CRITICAL: Unrecognized compilation operator type flag: '{type}'"
            )


def get_callable_parameter_type(
    symbol_or_func: Parameter | Callable[..., Any] | None,
    *indices: Any,
) -> Any:
    """
    Return a GAMSPy expression from either a Parameter or a callable macro replacement.

    This is useful for GAMS symbols that may be either a normal parameter
    or a compile-time macro depending on model settings.

    Examples:
        get_callable_parameter_type(g.rtcs_fr, r, t, c, s, ts)

    Behavior:
        - Callable: call it with the provided indices.
        - Parameter: index it with the provided indices.
        - None: raise a clear error.
    """
    if symbol_or_func is None:
        raise RuntimeError(
            "Expected a GAMSPy Parameter or callable macro replacement, but got None."
        )

    if callable(symbol_or_func):
        return symbol_or_func(*indices)

    if isinstance(symbol_or_func, Parameter):
        return symbol_or_func[*indices]

    raise TypeError(
        "Expected a GAMSPy Parameter or callable macro replacement, "
        f"but got {type(symbol_or_func).__name__}."
    )
