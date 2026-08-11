# macros.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from gamspy import Alias, Set, Sum

if TYPE_CHECKING:
    from gamspy import Expression
    from gamspy._symbols.implicits.implicit_parameter import ImplicitParameter

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
        sow_GP: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
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
        self, v: Set | Alias, s: Set | Alias, lA: Set | Alias
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
        sow_GP: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
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
        r: Set | Alias,
        v: Set | Alias,
        t: Set | Alias,
        p: Set | Alias,
        ts: Set | Alias,
        bd: Set | Alias | str,
    ) -> Sum | ImplicitParameter:
        g = self.g
        if self.active:
            var_udp = g.get_variable(f"{self.var}_udp")
            return Sum(
                g.RpStl[r, p, g.tsl, bd].where[g.TsGroup[r, g.tsl, ts]],
                var_udp[r, v, t, p, ts, bd, *self.sow_GP],
            )
        return g.var_sts[r, v, t, p, ts, bd]


class Macros:
    def __init__(self) -> None:
        self._g: TimesModelClass
        self._active: dict[str, bool] = {}
        self.var_sift = VarSiftContext()
        self.var_sts = VarStsContext()

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
        self, r: Set | Alias, y: Set | Alias, p: Set | Alias, m: Set | Alias
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
        self, r: Set | Alias, y: Set | Alias, p: Set | Alias, m: Set | Alias
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
        self, r: Set | Alias, y: Set | Alias, p: Set | Alias, m: Set | Alias
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
        self, r: Set | Alias, y: Set | Alias, p: Set | Alias, m: Set | Alias
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
        self, r: Set | Alias, y: Set | Alias, p: Set | Alias, m: Set | Alias
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
        self, r: Set | Alias, y: Set | Alias, p: Set | Alias, m: Set | Alias
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
        r: Set | Alias,
        y: Set | Alias,
        p: Set | Alias,
        c: Set | Alias,
        s: Set | Alias,
        m: Set | Alias,
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
        r: Set | Alias,
        y: Set | Alias,
        p: Set | Alias,
        c: Set | Alias,
        s: Set | Alias,
        m: Set | Alias,
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
        self, s: Set | Alias, env: CompileEnvironment, g: TimesModelClass
    ) -> Set | Alias:
        # Return environment variable
        if self.rts_active:
            rts = env.rts_GP(s)
            assert isinstance(rts, (Set | Alias)), (
                f"rts returned an enexpected value {rts=}"
            )
            return rts
        # Return the Alias
        return g.rts


macro_config = Macros()
