from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import pandas as pd
from gamspy import (
    Alias,
    Domain,
    Expression,
    Model,
    Parameter,
    Set,
    SpecialValues,
    Sum,
    Variable,
)
from gamspy._algebra.condition import Condition
from gamspy._internals import MODEL_ATTRIBUTE_MAP
from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet, ImplicitVariable
from gamspy.math import rpower

if TYPE_CHECKING:
    from collections.abc import Sequence

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

SET_OR_ALIAS = Set | ImplicitSet | Alias
EquationSenseTypes = Literal["E", "N", "L", "G"]
TargetType = Expression | Sum | Variable | ImplicitVariable | Condition
DomainType = (
    SET_OR_ALIAS
    | tuple[ImplicitSet | Condition, ImplicitParameter]
    | Condition
    | Domain
    | None
)
SowGPType = tuple[Literal["0", "1"] | Set | Alias] | tuple[()]


class EscapeStack(Exception):
    """Helper function to safely return back to surface while testing."""


@dataclass(kw_only=True)
class BaseUcModConfig:
    """Base config containing the fields shared across all 7 variations."""

    arg1: Domain | ImplicitSet | None
    arg2: (
        SET_OR_ALIAS
        | Condition
        | tuple[Condition | ImplicitSet, ImplicitParameter]
        | None
    )
    arg3: Domain | ImplicitSet | None
    arg4: SET_OR_ALIAS  # TT or T
    arg5: SET_OR_ALIAS | str  # SIDE, "LHS"
    arg6: Literal["S", 1, 2, 0]
    arg7: SET_OR_ALIAS | tuple[()] = ()


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
        data = symbol.records.astype(object).fillna("")

        for row in data.values.tolist():  # noqa: PD011
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
        env.set_scoped("sow_GP", ())
        env.set_scoped("swt", "")
        env.set_scoped("swt_GP", ())
        env.set_scoped("swd", "")
        env.set_scoped("swd_GP", ())
        env.set_scoped("swtd", "")
        env.set_scoped("swtd_GP", ())
        env.set_scoped("swsw", "")
        env.set_scoped("swsw_GP", ())
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
    # $SETGLOBAL EWISPINE SET EQ %EQ% of recurrin.stc: %EQ% there is resolved
    # at $SETGLOBAL-definition time (while %EQ%=='Q', from apply_witspine), so
    # invoking %EWISPINE% later restores EQ to its pre-witspine value, i.e. EQS.
    env.set_scoped("eq", env.eqs)


def apply_v_scope(env: CompileEnvironment, scope: str, value: str) -> None:
    """sol_flo.red:11: SET%4 V VAR"""
    scope_upper = scope.upper()
    if scope_upper == "LOCAL":
        env.set_local("v", value)
    elif scope_upper == "GLOBAL":
        env.set_global("v", value)
    else:
        env.set_scoped("v", value)


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
        env.set_scoped("swsw_GP", (g.SwTsw[g.Sow, g.t, g.ww],))
    elif (
        env.sw_stvars
        == "SET VAR 'Z' SET VART 'SUM(SW_TSW(SOW,T,W),Z' SET VARM 'SUM(SW_TSW(SOW,MODLYEAR,W),Z' SET VARV 'SUM(SW_TSW(SOW,V,W),Z'"
    ):
        env.set_scoped("var", "Z")
        env.set_scoped("vart", "SUM(SW_TSW(SOW,T,W),Z")
        env.set_scoped("vart_GP", ("Z", g.SwTsw[g.Sow, g.t, g.w]))
        env.set_scoped("varm", "SUM(SW_TSW(SOW,MODLYEAR,W),Z")
        env.set_scoped("varm_GP", ("Z", g.SwTsw[g.Sow, g.Modlyear, g.w]))
        env.set_scoped("varv", "SUM(SW_TSW(SOW,V,W),Z")
        env.set_scoped("varv_GP", ("Z", g.SwTsw[g.Sow, g.v, g.w]))
    elif (
        env.sw_stvars
        == "SET VAR 'Z' SET VART 'SUM(SW_TSW(SOW,T,W),Z' SET VARM 'SUM(SW_TSW(SOW,MODLYEAR,W),Z' SET VARV 'SUM(SW_TSW(SOW,V,W),Z' SET VARTT 'SUM(SW_TSW(W,TT,W),SW_TPROB(TT,W)*Z' SET SWSW SW_TSW(SOW(WW),T,WW),SW_TPROB(T,WW)*"
    ):
        env.set_scoped("var", "Z")
        env.set_scoped("vart", "SUM(SW_TSW(SOW,T,W),Z")
        env.set_scoped("vart_GP", ("Z", g.SwTsw[g.Sow, g.t, g.w]))
        env.set_scoped("varm", "SUM(SW_TSW(SOW,MODLYEAR,W),Z")
        env.set_scoped("varm_GP", ("Z", g.SwTsw[g.Sow, g.Modlyear, g.w]))
        env.set_scoped("varv", "SUM(SW_TSW(SOW,V,W),Z")
        env.set_scoped("varv_GP", ("Z", g.SwTsw[g.Sow, g.v, g.w]))
        env.set_scoped("vartt", "SUM(SW_TSW(W,TT,W),SW_TPROB(TT,W)*Z")
        env.set_scoped(
            "vartt_GP",
            ("Z", (g.SwTsw[g.w, g.tt, g.w], g.sw_tprob[g.tt, g.w])),
        )
        env.set_scoped("swsw", "SW_TSW(SOW(WW),T,WW),SW_TPROB(T,WW)*")
        env.set_scoped(
            "swsw_GP", (g.SwTsw[g.Sow[g.ww], g.t, g.ww], g.sw_tprob[g.t, g.ww])
        )
    else:
        raise ValueError(f"Unknown value in sw_stvars: {env.sw_stvars}")


def generate_equation(lhs: Any, type: EquationSenseTypes, rhs: Any) -> Any:
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


def wrap_in_sum[T: TargetType](target: T, domain: DomainType) -> T | Sum:
    """
    Wraps a target expression or variable in a Sum based on the provided domain/condition.
    Returns the unmodified target if the expression is None.
    """
    match domain:
        case None:
            return target
        case (condition, imp_param) if imp_param is not None:
            return Sum(condition, imp_param * target)  # type: ignore[arg-type]
        case (condition,) if isinstance(condition, SET_OR_ALIAS | Condition):
            return Sum(condition, target)
        case condition if isinstance(condition, SET_OR_ALIAS | Condition):
            return Sum(condition, target)
        case _:
            raise TypeError(
                f"Unexpected argument type: {type(domain).__name__} for {domain}"
            )


def model_status_symbol(model: Model) -> Parameter:
    """
    Returns a symbolic handle on %MODEL_NAME%.MODELSTAT that tracks the live
    value at GAMS execution time, including for solves queued inside a
    GAMSPy Loop/For (where model.status in Python is still the pre-solve
    value). Must be called outside any Loop, since it emits a declaration.

    Stopgap: relies on GAMSPy internals (MODEL_ATTRIBUTE_MAP and
    Model._attr_symbol_names). GAMSPy declares one autogenerated scalar per
    model attribute on Model construction and assigns it after every solve;
    this re-declares that scalar as a Parameter we can reference. Replace once
    GAMSPy exposes model attributes as symbols publicly.

    GAMSPy only assigns that scalar after its own model.solve(); a raw-GAMS
    ``SOLVE %MODEL_NAME% ...`` emitted via add_gams_code() leaves it stale.
    Any such raw solve must be followed by
    ``{tc.model_status_GP.name} = %MODEL_NAME%.MODELSTAT;`` in the same raw
    block (see rpt_ext_mlf.py's Negishi loop).
    """
    attr_symbols = dict(zip(MODEL_ATTRIBUTE_MAP, model._attr_symbol_names, strict=True))
    return Parameter(model.container, name=attr_symbols["modelStat"])


def extract_var_domain(var: str | tuple[str, Any]) -> tuple[str, ImplicitSet | None]:
    if isinstance(var, tuple) and len(var) > 1:
        var_id, var_set = var
    else:
        var_id = var
        var_set = None
    return var_id, var_set
