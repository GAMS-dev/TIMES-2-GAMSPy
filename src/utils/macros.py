# macros.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from gamspy import Sum
from gamspy.math import Max, power, sqrt

from core.utils import SET_OR_ALIAS

if TYPE_CHECKING:
    from gamspy import Equation, Expression, Number, Variable
    from gamspy._algebra.expression import ShiftExpression
    from gamspy._symbols.implicits import (
        ImplicitParameter,
        ImplicitSet,
        ImplicitVariable,
    )

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass


@dataclass
class VarSiftContext:
    active: bool = False
    var: str = ""
    sow: str = ""

    def activate(
        self,
        g: TimesModelClass,
        var: str,
        sow: str,
        sow_GP: tuple[Literal["0", "1"] | SET_OR_ALIAS] | tuple[()],
    ) -> None:
        self.g = g
        self.active = True
        self.var = var
        self.sow = sow
        self.sow_GP = sow_GP

    def deactivate(self) -> None:
        self.active = False
        self.var = ""
        self.sow = ""

    def render(self, v: str, s: str, lA: str) -> str:
        if self.active:
            return f"{self.var}_udp(r,{v},t,p,{s},{lA}{self.sow})*prc_capact(r,p)*rs_stgprd(r,{s})/8760"
        return f"VAR_SIFT({v},{s},{lA})"

    def render_GP(
        self, v: SET_OR_ALIAS | str, s: SET_OR_ALIAS, lA: SET_OR_ALIAS | str
    ) -> Expression | ImplicitParameter | Any:
        g = self.g
        if self.active:
            var_udp = g.get_variable(f"{self.var}_udp")
            return (
                var_udp[g.r, v, g.t, g.p, s, lA, *self.sow_GP]
                * g.prc_capact[g.r, g.p]
                * g.rs_stgprd[g.r, s]
                / 8760
            )
        return g.var_sift[v, s, lA]


@dataclass
class VarStsContext:
    active: bool = False
    var: str = ""
    sow: str = ""

    def activate(
        self,
        g: TimesModelClass,
        var: str,
        sow: str,
        sow_GP: tuple[Literal["0", "1"] | SET_OR_ALIAS] | tuple[()],
    ) -> None:
        self.g = g
        self.active = True
        self.var = var
        self.sow = sow
        self.sow_GP = sow_GP

    def deactivate(self) -> None:
        self.active = False
        self.var = ""
        self.sow = ""
        self.sow_GP = ()

    def render(self, r: str, v: str, t: str, p: str, ts: str, bd: str) -> str:
        if self.active:
            return f"sum(rp_stl({r},{p},tsl,{bd})$ts_group({r},tsl,{ts}),{self.var}_udp({r},{v},{t},{p},{ts},{bd}{self.sow}))"
        return f"VAR_STS({r},{v},{t},{p},{ts},{bd})"

    def render_GP(
        self,
        r: SET_OR_ALIAS,
        v: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        ts: SET_OR_ALIAS,
        bd: SET_OR_ALIAS | str,
    ) -> Sum | ImplicitParameter:
        g = self.g
        if self.active:
            var_udp = g.get_variable(f"{self.var}_udp")
            return Sum(
                g.RpStl[r, p, g.tsl, bd].where[g.TsGroup[r, g.tsl, ts]],
                var_udp[r, v, t, p, ts, bd, *self.sow_GP],
            )
        return g.var_sts[r, v, t, p, ts, bd]


@dataclass
class UpscapsContext:
    active: bool = False
    var: str = ""
    sow: str = ""

    def activate(
        self,
        g: TimesModelClass,
        var: str,
        sow: str,
        sow_GP: tuple[Literal["0", "1"] | SET_OR_ALIAS] | tuple[()],
    ) -> None:
        self.g = g
        self.active = True
        self.var = var
        self.sow = sow
        self.sow_GP = sow_GP

    def deactivate(self) -> None:
        self.active = False
        self.var = ""
        self.sow = ""
        self.sow_GP = ()

    def render(self) -> str:
        if self.active:
            return f"-SUM(TS_MAP(R,ALL_TS,S)$RPS_UPS(R,P,ALL_TS),{self.var}_UPS(R,V,T,P,ALL_TS,'N'{self.sow}))"
        else:
            raise NotImplementedError

    def render_GP(
        self,
    ) -> Expression:
        g = self.g
        if self.active:
            var_ups = g.get_variable(f"{self.var}_UPS")
            expr = -Sum(
                g.TsMap[g.r, g.allts, g.s].where[g.RpsUps[g.r, g.p, g.allts]],
                var_ups[g.r, g.v, g.t, g.p, g.allts, "N", *self.sow_GP],
            )
            return expr
        else:
            raise NotImplementedError


@dataclass
class RecurrinSymbol:
    name: str
    symbol: Equation | Variable

    def __getitem__(self, indices: Any) -> Any:
        keys = list(indices) if isinstance(indices, tuple) else [indices]
        dimension = sum(getattr(key, "dimension", 1) for key in keys)
        if dimension != self.symbol.dimension or (
            keys and getattr(keys[-1], "dimension", 1) != 1
        ):
            raise ValueError(
                f"$macro {self.name} expands to {self.symbol.name}, which needs "
                f"{self.symbol.dimension} indices ending on the state, got: {keys}"
            )
        return self.symbol[(*keys[:-1], "1")]

    def __getattr__(self, item: str) -> Any:
        raise NotImplementedError(
            f"$macro {self.name} is only translated for indexing, not for '.{item}'"
        )


@dataclass
class RecurrinContext:
    active: bool = False
    solveda: bool = False

    prefixes: ClassVar[dict[str, str]] = {"Q": "ES", "Z": "VAS"}
    pinned_variables: ClassVar[frozenset[str]] = frozenset(
        {"CAP", "NCAP", "RCAP", "SCAP", "SNCAP", "XCAP"}
    )
    pinned_solveda_variables: ClassVar[frozenset[str]] = frozenset(
        {"CUMCOM", "CUMFLO", "CUMCST"}
    )
    pinned_solveda_equations: ClassVar[frozenset[str]] = frozenset(
        {
            "BNDCST",
            "CUMNET",
            "CUMPRD",
            "CUMFLO",
            "E_UC",
            "E_UCR",
            "E_UCSU",
            "E_UCSUS",
            "E_UCRSU",
            "E_UCRSUS",
            "L_SCAP",
        }
    )

    def activate(self, g: TimesModelClass, solveda: bool) -> None:
        self.g = g
        self.active = True
        self.solveda = solveda

    def deactivate(self) -> None:
        self.active = False
        self.solveda = False

    def equation_GP(self, name: str) -> Any:
        """%EQ%_xxx of a SPINES run, i.e. the ES_xxx equation the Q_xxx $macro aliases."""
        pinned = self.pinned_solveda_equations if self.solveda else frozenset()
        return self._expand(name, pinned, is_equation=True)

    def variable_GP(self, name: str) -> Any:
        """%VAR%_xxx of a SPINES run, i.e. the VAS_xxx variable the Z_xxx $macro aliases."""
        pinned = self.pinned_variables
        if self.solveda:
            pinned = pinned | self.pinned_solveda_variables
        return self._expand(name, pinned, is_equation=False)

    def _expand(self, name: str, pinned: frozenset[str], is_equation: bool) -> Any:
        name = name.upper()
        alias = self.prefixes.get(name[:1]) if self.active else None
        if alias is None:
            # not a macro of recurrin.stc, so report the symbol as the getters would
            raise AttributeError(f"'TimesModelClass' object has no attribute '{name}'")
        aliased = f"{alias}{name[1:]}"
        symbol = (
            self.g.get_equation(aliased)
            if is_equation
            else self.g.get_variable(aliased)
        )
        if name[1:].lstrip("_") not in pinned:
            return symbol
        return RecurrinSymbol(name=name, symbol=symbol)


class Macros:
    def __init__(self) -> None:
        self._g: TimesModelClass
        self._active: dict[str, bool] = {}
        self.var_sift = VarSiftContext()
        self.var_sts = VarStsContext()
        self.upscaps = UpscapsContext()
        self.recurrin = RecurrinContext()

    # ICOST
    @property
    def obj_icost_active(self) -> bool:
        return self._active.get("OBJ_ICOST", False)

    @obj_icost_active.setter
    def obj_icost_active(self, value: bool) -> None:
        self._active["OBJ_ICOST"] = value

    def obj_icost(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_icost_active:
            return f"OB_ICOST({r},{p},{m},{y})"
        return f"OBJ_ICOST({r},{y},{p},{m})"

    def obj_icost_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_icost_active:
            return self._g.ob_icost[r, p, m, y]
        return self._g.obj_icost[r, y, p, m]

    # ISUB
    @property
    def obj_isub_active(self) -> bool:
        return self._active.get("OBJ_ISUB", False)

    @obj_isub_active.setter
    def obj_isub_active(self, value: bool) -> None:
        self._active["OBJ_ISUB"] = value

    def obj_isub(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_isub_active:
            return f"OB_ISUB({r},{p},{m},{y})"
        return f"OBJ_ISUB({r},{y},{p},{m})"

    def obj_isub_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_isub_active:
            return self._g.ob_isub[r, p, m, y]
        return self._g.obj_isub[r, y, p, m]

    # ITAX
    @property
    def obj_itax_active(self) -> bool:
        return self._active.get("OBJ_ITAX", False)

    @obj_itax_active.setter
    def obj_itax_active(self, value: bool) -> None:
        self._active["OBJ_ITAX"] = value

    def obj_itax(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_itax_active:
            return f"OB_ITAX({r},{p},{m},{y})"
        return f"OBJ_ITAX({r},{y},{p},{m})"

    def obj_itax_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_itax_active:
            return self._g.ob_itax[r, p, m, y]
        return self._g.obj_itax[r, y, p, m]

    # FOM
    @property
    def obj_fom_active(self) -> bool:
        return self._active.get("OBJ_FOM", False)

    @obj_fom_active.setter
    def obj_fom_active(self, value: bool) -> None:
        self._active["OBJ_FOM"] = value

    def obj_fom(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_fom_active:
            return f"OB_FOM({r},{p},{m},{y})"
        return f"OBJ_FOM({r},{y},{p},{m})"

    def obj_fom_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_fom_active:
            return self._g.ob_fom[r, p, m, y]
        return self._g.obj_fom[r, y, p, m]

    # FSB
    @property
    def obj_fsb_active(self) -> bool:
        return self._active.get("OBJ_FSB", False)

    @obj_fsb_active.setter
    def obj_fsb_active(self, value: bool) -> None:
        self._active["OBJ_FSB"] = value

    def obj_fsb(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_fsb_active:
            return f"OB_FSB({r},{p},{m},{y})"
        return f"OBJ_FSB({r},{y},{p},{m})"

    def obj_fsb_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_fsb_active:
            return self._g.ob_fsb[r, p, m, y]
        return self._g.obj_fsb[r, y, p, m]

    # FTX
    @property
    def obj_ftx_active(self) -> bool:
        return self._active.get("OBJ_FTX", False)

    @obj_ftx_active.setter
    def obj_ftx_active(self, value: bool) -> None:
        self._active["OBJ_FTX"] = value

    def obj_ftx(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_ftx_active:
            return f"OB_FTX({r},{p},{m},{y})"
        return f"OBJ_FTX({r},{y},{p},{m})"

    def obj_ftx_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_ftx_active:
            return self._g.ob_ftx[r, p, m, y]
        return self._g.obj_ftx[r, y, p, m]

    # DCOST
    @property
    def obj_dcost_active(self) -> bool:
        return self._active.get("OBJ_DCOST", False)

    @obj_dcost_active.setter
    def obj_dcost_active(self, value: bool) -> None:
        self._active["OBJ_DCOST"] = value

    def obj_dcost(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_dcost_active:
            return f"OB_DCC({r},{p},{m},{y})"
        return f"OBJ_DCOST({r},{y},{p},{m})"

    def obj_dcost_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_dcost_active:
            return self._g.ob_dcc[r, p, m, y]
        return self._g.obj_dcost[r, y, p, m]

    # DLAGC
    @property
    def obj_dlagc_active(self) -> bool:
        return self._active.get("OBJ_DLAGC", False)

    @obj_dlagc_active.setter
    def obj_dlagc_active(self, value: bool) -> None:
        self._active["OBJ_DLAGC"] = value

    def obj_dlagc(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_dlagc_active:
            return f"OB_DLC({r},{p},{m},{y})"
        return f"OBJ_DLAGC({r},{y},{p},{m})"

    def obj_dlagc_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_dlagc_active:
            return self._g.ob_dlc[r, p, m, y]
        return self._g.obj_dlagc[r, y, p, m]

    # ACOST
    @property
    def obj_acost_active(self) -> bool:
        return self._active.get("OBJ_ACOST", False)

    @obj_acost_active.setter
    def obj_acost_active(self, value: bool) -> None:
        self._active["OBJ_ACOST"] = value

    def obj_acost(self, r: str, y: str, p: str, m: str) -> str:
        if self.obj_acost_active:
            return f"OB_ACT({r},{p},{m},{y})"
        return f"OBJ_ACOST({r},{y},{p},{m})"

    def obj_acost_GP(
        self, r: SET_OR_ALIAS, y: SET_OR_ALIAS, p: SET_OR_ALIAS, m: SET_OR_ALIAS
    ) -> ImplicitParameter:
        if self.obj_acost_active:
            return self._g.ob_act[r, p, m, y]
        return self._g.obj_acost[r, y, p, m]

    # FCOST
    @property
    def obj_fcost_active(self) -> bool:
        return self._active.get("OBJ_FCOST", False)

    @obj_fcost_active.setter
    def obj_fcost_active(self, value: bool) -> None:
        self._active["OBJ_FCOST"] = value

    def obj_fcost(self, r: str, y: str, p: str, c: str, s: str, m: str) -> str:
        if self.obj_fcost_active:
            return f"OB_FCOS({r},{p},{c},{s},{m},{y})"
        return f"OBJ_FCOST({r},{y},{p},{c},{s},{m})"

    def obj_fcost_GP(
        self,
        r: SET_OR_ALIAS,
        y: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
        m: SET_OR_ALIAS,
    ) -> ImplicitParameter:
        if self.obj_fcost_active:
            return self._g.ob_fcos[r, p, c, s, m, y]
        return self._g.obj_fcost[r, y, p, c, s, m]

    # FDELV
    @property
    def obj_fdelv_active(self) -> bool:
        return self._active.get("OBJ_FDELV", False)

    @obj_fdelv_active.setter
    def obj_fdelv_active(self, value: bool) -> None:
        self._active["OBJ_FDELV"] = value

    def obj_fdelv(self, r: str, y: str, p: str, c: str, s: str, m: str) -> str:
        if self.obj_fdelv_active:
            return f"OB_FDEL({r},{p},{c},{s},{m},{y})"
        return f"OBJ_FDELV({r},{y},{p},{c},{s},{m})"

    def obj_fdelv_GP(
        self,
        r: SET_OR_ALIAS,
        y: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
        m: SET_OR_ALIAS,
    ) -> ImplicitParameter:
        if self.obj_fdelv_active:
            return self._g.ob_fdel[r, p, c, s, m, y]
        return self._g.obj_fdelv[r, y, p, c, s, m]

    # FTAX
    @property
    def obj_ftax_active(self) -> bool:
        return self._active.get("OBJ_FTAX", False)

    @obj_ftax_active.setter
    def obj_ftax_active(self, value: bool) -> None:
        self._active["OBJ_FTAX"] = value

    def obj_ftax(self, r: str, y: str, p: str, c: str, s: str, m: str) -> str:
        if self.obj_ftax_active:
            return f"OB_FTAX({r},{p},{c},{s},{m},{y})"
        return f"OBJ_FTAX({r},{y},{p},{c},{s},{m})"

    def obj_ftax_GP(
        self,
        r: SET_OR_ALIAS,
        y: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
        m: SET_OR_ALIAS,
    ) -> ImplicitParameter:
        if self.obj_ftax_active:
            return self._g.ob_ftax[r, p, c, s, m, y]
        return self._g.obj_ftax[r, y, p, c, s, m]

    # RTS
    @property
    def rts_active(self) -> bool:
        return self._active.get("RTS", False)

    @rts_active.setter
    def rts_active(self, value: bool) -> None:
        self._active["RTS"] = value

    def rts(self, s: Any, env: CompileEnvironment, g: TimesModelClass) -> Any:
        # Return environment variable
        if self.rts_active:
            return env.rts(s)
        # Return the Alias
        return "RTS"

    def rts_GP(
        self, s: SET_OR_ALIAS, env: CompileEnvironment, g: TimesModelClass
    ) -> SET_OR_ALIAS:
        # Return environment variable
        if self.rts_active:
            rts = env.rts_GP(s)
            assert isinstance(rts, (SET_OR_ALIAS)), (
                f"rts returned an enexpected value {rts=}"
            )
            return rts
        # Return the Alias
        return g.rts

    # From gasgrids_vda

    # VAR_GG_PRU
    @property
    def var_gg_pru_active(self) -> bool:
        return self._active.get("VAR_GG_PRU", False)

    @var_gg_pru_active.setter
    def var_gg_pru_active(self, value: bool) -> None:
        self._active["VAR_GG_PRU"] = value

    def var_gg_pru_GP(
        self,
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
    ) -> Sum:
        g = self._g
        if self.var_gg_pru_active:
            return Sum(g.Actcg[g.com2], g.VAR_GG_PDIF[r, t, p, c, r, g.com2, s])

        raise NotImplementedError(
            "var_gg_pru is only implemented as a macro and wasn't activeted."
        )

    # VAR_GG_Y2
    @property
    def var_gg_y2_active(self) -> bool:
        return self._active.get("VAR_GG_Y2", False)

    @var_gg_y2_active.setter
    def var_gg_y2_active(self, value: bool) -> None:
        self._active["VAR_GG_Y2"] = value

    def var_gg_y2_GP(
        self,
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        Reg: SET_OR_ALIAS,
        Com: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
    ) -> Expression | ImplicitSet:
        g = self._g
        if self.var_gg_y2_active:
            return (
                g.VAR_GG_Y[r, t, p, c, s].where[g.GgTop[r, c, Reg, Com, p]]
                + (1.0 - g.VAR_GG_Y[Reg, t, p, Com, s]).where[
                    g.GgTop[Reg, Com, r, c, p]
                ]
            )

        raise NotImplementedError(
            "var_gg_y2 is only implemented as a macro and wasn't activeted."
        )

    # VAR_GG_PRIO
    @property
    def var_gg_prio_active(self) -> bool:
        return self._active.get("VAR_GG_PRIO", False)

    @var_gg_prio_active.setter
    def var_gg_prio_active(self, value: bool) -> None:
        self._active["VAR_GG_PRIO"] = value

    def var_gg_prio_GP(
        self,
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
    ) -> Expression | ImplicitSet:
        g = self._g
        if self.var_gg_prio_active:
            return (
                g.VAR_GG_PR[r, t, c, s]
                + g.VAR_GG_PADD[r, t, p, c, s].where[g.gg_gamma[r, t, p, c]]
            )

        raise NotImplementedError(
            "var_gg_prio is only implemented as a macro and wasn't activeted."
        )

    # VAR_GG_HLIP
    @property
    def var_gg_hlip_active(self) -> bool:
        return self._active.get("VAR_GG_HLIP", False)

    @var_gg_hlip_active.setter
    def var_gg_hlip_active(self, value: bool) -> None:
        self._active["VAR_GG_HLIP"] = value

    def var_gg_hlip_GP(
        self,
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        s: SET_OR_ALIAS | ShiftExpression,
    ) -> ImplicitVariable:
        g = self._g
        if self.var_gg_hlip_active:
            return g.VAR_GG_PADD[r, t, p, g.env.pgprim, s]

        raise NotImplementedError(
            "var_gg_hlip is only implemented as a macro and wasn't activeted."
        )

    # VAR_GG_WSLAC
    @property
    def var_gg_wslac_active(self) -> bool:
        return self._active.get("VAR_GG_WSLAC", False)

    @var_gg_wslac_active.setter
    def var_gg_wslac_active(self, value: bool) -> None:
        self._active["VAR_GG_WSLAC"] = value

    def var_gg_wslac_GP(
        self,
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        Reg: SET_OR_ALIAS,
        Com: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
    ) -> Sum | ImplicitParameter:
        g = self._g
        if self.var_gg_wslac_active:
            return Sum(
                g.com2[g.Actcg].where[g.gg_kgf[r, t, p, c]],
                g.VAR_GG_PDIF[r, t, p, g.com2, r, c, s]
                + 8.0
                / 11.0
                * g.VAR_GG_PDIF[Reg, t, p, g.com2, Reg, Com, s].where[
                    g.GgWink[Reg, p, Com, r, c] & ((~(g.gg_m1)) | (0.0))
                ],
            )

        raise NotImplementedError(
            "var_gg_wslac is only implemented as a macro and wasn't activeted."
        )

    # VAR_GG_PDMAX
    @property
    def var_gg_pdmax_active(self) -> bool:
        return self._active.get("VAR_GG_PDMAX", False)

    @var_gg_pdmax_active.setter
    def var_gg_pdmax_active(self, value: bool) -> None:
        self._active["VAR_GG_PDMAX"] = value

    def var_gg_pdmax_GP(
        self,
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        Reg: SET_OR_ALIAS,
        Com: SET_OR_ALIAS,
        ts: SET_OR_ALIAS,
        z: Number,
        with_sqrt: bool,
    ) -> Expression:
        g = self._g
        if self.var_gg_pdmax_active:
            firstpart = Max(
                power(
                    g.gg_prbd[r, t, c, "UP"] * Max(1.0, g.gg_gamma[r, t, p, c]),
                    z,
                )
                - power(g.gg_prbd[Reg, t, Com, "LO"], z),
                0.0,
            )

            secondpart = (
                g.VAR_GG_Y[r, t, p, c, ts].where[g.GgTop[r, c, Reg, Com, p]]
                + (1.0 - g.VAR_GG_Y[Reg, t, p, Com, ts]).where[
                    g.GgTop[Reg, Com, r, c, p]
                ]
            )

            if with_sqrt:
                firstpart = sqrt(firstpart)

            return firstpart * secondpart

        raise NotImplementedError(
            "var_gg_pdmax is only implemented as a macro and wasn't activeted."
        )


macro_config = Macros()
