# macros.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from gamspy import Domain, Sum
from gamspy.math import Max, power, sqrt

from core.utils import SET_OR_ALIAS, SowGPType, extract_var_domain, wrap_in_sum

if TYPE_CHECKING:
    from gamspy import Alias, Equation, Expression, Number, Set
    from gamspy._algebra.condition import Condition
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
class RtcsFrContext:
    """$macro RTCS_FR(R,T,C,S,TS) of recurrin.stc, active when S_COM_FR is defined.

    RTCS_FR(R,T,C,S,TS) = RTCS_FRMX(R,T,C,S,TS)
        + SUM(SW_T2W(SOW,T,W,T0), RCS_SSFR(R,C,S,TS,W,T0))
    """

    active: bool = False

    def activate(self, g: TimesModelClass) -> None:
        self.g = g
        self.active = True

    def deactivate(self) -> None:
        self.active = False

    def rtcs_frmx(self, r: str, t: str, c: str, s: str, ts: str) -> str:
        """Raw-text form of whichever real parameter RTCS_FRMX refers to
        (recurrin.stc line 42: $MACRO RTCS_FRMX RTCS_FR, when inactive;
        line 47: PARAMETER RTCS_FRMX(...), when active). For callers still
        emitting raw GAMS text (e.g. stages.stc)."""
        name = "RTCS_FRMX" if self.active else "RTCS_FR"
        return f"{name}({r},{t},{c},{s},{ts})"

    def rtcs_frmx_GP(self, *domain: SET_OR_ALIAS | str) -> ImplicitParameter:
        """Native counterpart of rtcs_frmx: the value RTCS_FRMX(...) currently
        reads/writes as, for callers that index/assign into it themselves
        (e.g. ppmain.mod's RTCS_FR%MX% assignment target). `domain` is
        whatever the caller would pass directly to g.rtcs_frmx/g.rtcs_fr -
        5 separate r,t,c,s,ts, or a combined subset (e.g. an RTC tuple) in
        place of separate r,t,c."""
        g = self.g
        base = g.rtcs_frmx if self.active else g.rtcs_fr
        return base[domain]

    def rtcs_fr(self, r: str, t: str, c: str, s: str, ts: str) -> str:
        """String counterpart of rtcs_fr_GP, for callers still emitting raw
        GAMS text (see class docstring for the SOW caveat, which applies
        identically here: leave the literal SOW token untouched)."""
        if not self.active:
            return f"RTCS_FR({r},{t},{c},{s},{ts})"
        return (
            f"RTCS_FRMX({r},{t},{c},{s},{ts})"
            f"+SUM(SW_T2W(SOW,{t},W,T0),RCS_SSFR({r},{c},{s},{ts},W,T0))"
        )

    def rtcs_fr_GP(
        self,
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
        ts: SET_OR_ALIAS | str,
        sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()],
    ) -> Any:
        """SOW is not one of RTCS_FR's formal params: GAMS's textual $macro
        expansion makes it refer to whichever SOW is already bound by the
        calling equation's own domain, so callers pass their own current
        `sow` (e.g. self.env.sow_GP or cc.sow).
        """
        g = self.g
        if not self.active:
            return g.rtcs_fr[r, t, c, s, ts]
        sow_scalar = sow[0] if sow else None
        return self.rtcs_frmx_GP(r, t, c, s, ts) + Sum(
            Domain(g.w, g.T0).where[g.SwT2w[sow_scalar, t, g.w, g.T0]],
            g.rcs_ssfr[r, c, s, ts, g.w, g.T0],
        )


@dataclass
class ComFrContext:
    """$macro COM_FRMX(R,T,C,S) of recurrin.stc, active when S_COM_FR is defined.

    recurrin.stc line 49:
    COM_FRMX(R,T,C,S) = COM_FR(R,T,C,S) * %SW1%(%SW2%1+S_COM_FR(R,T,C,S,'1',SOW))
    """

    active: bool = False
    sw1: str = ""
    sw2: str = ""
    sw2_GP: tuple[SET_OR_ALIAS] | tuple[()] = ()

    def activate(
        self,
        g: TimesModelClass,
        sw1: str,
        sw2: str,
        sw2_GP: tuple[SET_OR_ALIAS] | tuple[()],
    ) -> None:
        self.g = g
        self.active = True
        self.sw1 = sw1
        self.sw2 = sw2
        self.sw2_GP = sw2_GP

    def deactivate(self) -> None:
        self.active = False

    def com_fr(self, mx: str, r: str, t: str, c: str, s: str) -> str:
        """String counterpart of com_fr_GP, for callers still emitting raw
        GAMS text. `mx` mirrors the caller's own %MX% BATINCLUDE arg (empty
        string when not passed)."""
        if not self.active or not mx:
            # recurrin.stc line 43: $MACRO COM_FRMX COM_FR (plain rename)
            return f"COM_FR({r},{t},{c},{s})"
        inner = f"{self.sw2}1+S_COM_FR({r},{t},{c},{s},'1',SOW)"
        return f"COM_FR({r},{t},{c},{s})*{self.sw1}({inner})"

    def com_fr_GP(
        self,
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
    ) -> Any:
        g = self.g
        if not self.active or mx == ():
            # recurrin.stc line 43 (or recurrin never reached DEFPAR at all)
            return g.com_fr[r, t, c, s]
        # recurrin.stc line 49: COM_FR(...)*%SW1%(%SW2%1+S_COM_FR(...,SOW))
        sow_domain = self.sw2_GP[0] if self.sw2_GP else None
        factor = 1 + g.s_com_fr[r, t, c, s, "1", g.Sow]
        return g.com_fr[r, t, c, s] * wrap_in_sum(factor, sow_domain)


@dataclass
class CoefAfMxContext:
    """$macro COEF_AFMX(R,V,T,P,S,BD) of recurrin.stc, active when S_NCAP_AFS is defined.

    recurrin.stc line 46:
    COEF_AFMX(R,V,T,P,S,BD) = COEF_AF(R,V,T,P,S,BD) * %SW1%(%SW2%1+RTP_SAFS(R,T,P,S,SOW))
    """

    active: bool = False
    sw1: str = ""
    sw2: str = ""
    sw2_GP: tuple[SET_OR_ALIAS] | tuple[()] = ()

    def activate(
        self,
        g: TimesModelClass,
        sw1: str,
        sw2: str,
        sw2_GP: tuple[SET_OR_ALIAS] | tuple[()],
    ) -> None:
        self.g = g
        self.active = True
        self.sw1 = sw1
        self.sw2 = sw2
        self.sw2_GP = sw2_GP

    def deactivate(self) -> None:
        self.active = False

    def coef_af(self, mx: str, r: str, v: str, t: str, p: str, s: str, bd: str) -> str:
        """String counterpart of coef_af_GP, for callers still emitting raw
        GAMS text. `mx` mirrors the caller's own %MX% BATINCLUDE arg (empty
        string when not passed)."""
        if not self.active or not mx:
            # recurrin.stc line 41: $MACRO COEF_AFMX COEF_AF (plain rename)
            return f"COEF_AF({r},{v},{t},{p},{s},{bd})"
        # recurrin.stc line 46: COEF_AF(...)*%SW1%(%SW2%1+RTP_SAFS(...,SOW))
        inner = f"{self.sw2}1+RTP_SAFS({r},{t},{p},{s},SOW)"
        return f"COEF_AF({r},{v},{t},{p},{s},{bd})*{self.sw1}({inner})"

    def coef_af_GP(
        self,
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        r: SET_OR_ALIAS,
        v: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        s: SET_OR_ALIAS,
        bd: SET_OR_ALIAS | str,
    ) -> ImplicitParameter | Expression:
        g = self.g
        coef_af = g.get_parameter("COEF_AF")
        if not self.active or mx == ():
            # recurrin.stc line 41 (or recurrin never reached DEFPAR at all)
            return coef_af[r, v, t, p, s, bd]
        # recurrin.stc line 46: COEF_AF(...)*%SW1%(%SW2%1+RTP_SAFS(...,SOW))
        sow_domain = self.sw2_GP[0] if self.sw2_GP else None
        factor = 1 + g.rtp_safs[r, t, p, s, g.Sow]
        return coef_af[r, v, t, p, s, bd] * wrap_in_sum(factor, sow_domain)


@dataclass
class PrcDynucMxContext:
    """$macro PRC_DYNUCMX(UC,SIDE,R,T,P,GRP,BD) of recurrin.stc, active when SPINES is YES.

    PRC_DYNUCMX(UC,SIDE,R,T,P,GRP,BD) = PRC_DYNUC(UC,SIDE,R,T,P,GRP,BD)$UCRTPSW1(GRP,SOW)

    SOW is not one of PRC_DYNUCMX's formal params: GAMS's textual $macro
    expansion makes it refer to whichever SOW is already bound by the
    calling equation's own domain, so callers must pass their own current
    `sow` rather than a fresh dummy.
    """

    active: bool = False

    def activate(self, g: TimesModelClass) -> None:
        self.g = g
        self.active = True

    def deactivate(self) -> None:
        self.active = False

    def prc_dynuc(
        self, uc: str, side: str, r: str, t: str, p: str, grp: str, bd: str
    ) -> str:
        base = f"PRC_DYNUC({uc},{side},{r},{t},{p},{grp},{bd})"
        if not self.active:
            return base
        return f"{base}$UCRTPSW1({grp},'SOW')"

    def prc_dynuc_GP(
        self,
        uc: SET_OR_ALIAS,
        side: SET_OR_ALIAS | str,
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        grp: SET_OR_ALIAS,
        bd: SET_OR_ALIAS | str,
    ) -> ImplicitParameter | Condition:
        g = self.g
        base = g.prc_dynuc[uc, side, r, t, p, grp, bd]
        if not self.active:
            return base
        return base.where[g.UcrtpSw1[grp, g.Sow]]


@dataclass
class EqUcContext:
    """EQ_UC/ESE_UC{suffix}/QE_UC{suffix} of recurrin.stc."""

    active: bool = False
    _REDIRECTED_SUFFIXES = frozenset({"", "R", "SU", "SUS", "RSU", "RSUS"})
    #: recurrin.stc's $macro QE_UC(uc,sow) ESE_UC(uc,'1') etc.: the SOW
    #: literal every Q_UC* redirect pins to, single source of truth for
    #: both this equation's own domain (below) and any expression that
    #: embeds a SOW-sensitive $macro inside such a redirected equation
    #: (e.g. RtcsFrContext.rtcs_fr_GP).
    PINNED_SOW: ClassVar[tuple[Literal["1"]]] = ("1",)

    def activate(self, g: TimesModelClass) -> None:
        self.g = g
        self.active = True

    def deactivate(self) -> None:
        self.active = False

    def redirects(self, arg1: str, suffix: str) -> bool:
        """True when QE_UC{suffix} is $macro-redirected to ESE_UC{suffix}
        with SOW pinned to PINNED_SOW: only for arg1=="E" and one of the
        six covered suffixes."""
        return self.active and arg1 == "E" and suffix in self._REDIRECTED_SUFFIXES

    def EQ_UC(self, eq: str, arg1: str, suffix: str, sow: str) -> tuple[str, str]:
        """String counterpart of EQ_UC_GP, for callers still emitting raw
        GAMS text: returns (equation name, sow text) for the caller to
        combine into its own call."""
        if self.redirects(arg1, suffix):
            return f"ESE_UC{suffix}", f"'{self.PINNED_SOW[0]}'"
        return f"{eq}{arg1}_UC{suffix}", sow

    def EQ_UC_GP(
        self,
        eq: str,
        arg1: str,
        suffix: str,
        sow: SowGPType,
    ) -> tuple[Equation, SowGPType]:
        """QE_UC/QE_UCR/QE_UCSU/QE_UCSUS/QE_UCRSU/QE_UCRSUS(...,sow): each
        renames to ESE_UC{suffix}, with sow pinned to PINNED_SOW."""
        g = self.g
        if self.redirects(arg1, suffix):
            return g.get_equation(f"ESE_UC{suffix}"), self.PINNED_SOW
        return g.get_equation(f"{eq}{arg1}_UC{suffix}"), sow


class Macros:
    def __init__(self) -> None:
        self._g: TimesModelClass
        self.reset()

    def bind(self, g: TimesModelClass) -> None:
        """Give this build's model to every sub-context."""
        self._g = g
        for context in (
            self.var_sift,
            self.var_sts,
            self.upscaps,
            self.rtcs_fr,
            self.com_fr,
            self.coef_af_mx,
            self.prc_dynuc_mx,
            self.eq_uc,
        ):
            context.g = g

    def reset(self) -> None:
        """Clear all $macro activation state left over from a prior model build."""
        self._active: dict[str, bool] = {}
        self.var_sift = VarSiftContext()
        self.var_sts = VarStsContext()
        self.upscaps = UpscapsContext()
        self.rtcs_fr = RtcsFrContext()
        self.com_fr = ComFrContext()
        self.coef_af_mx = CoefAfMxContext()
        self.prc_dynuc_mx = PrcDynucMxContext()
        self.eq_uc = EqUcContext()

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

    # VAR_CAP / VAS_CAP / Z_CAP
    @property
    def z_cap_active(self) -> bool:
        return self._active.get("Z_CAP", False)

    @z_cap_active.setter
    def z_cap_active(self, value: bool) -> None:
        self._active["Z_CAP"] = value

    def VAR_CAP(self, var: str, r: str, t: str, p: str, sow: str) -> str:
        if self.z_cap_active:
            return f"VAS_CAP({r},{t},{p},'1')"
        return f"{var}_CAP({r},{t},{p}{sow})"

    def VAR_CAP_GP(
        self,
        var: str | tuple[str, ImplicitSet | None],
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()],
    ) -> ImplicitVariable | Sum:
        if self.z_cap_active:
            return self._g.VAS_CAP[r, t, p, "1"]
        else:
            var_id, var_set = extract_var_domain(var)
            cap = self._g.get_variable(f"{var_id}_CAP")
            return wrap_in_sum(cap[r, t, p, *sow], var_set)

    # VAR_NCAP / VAS_NCAP / Z_NCAP
    # $macro Z_NCAP(r,t,p,sow)    VAS_NCAP(r,t,p,'1')
    @property
    def z_ncap_active(self) -> bool:
        return self._active.get("Z_NCAP", False)

    @z_ncap_active.setter
    def z_ncap_active(self, value: bool) -> None:
        self._active["Z_NCAP"] = value

    def VAR_NCAP(self, var: str, r: str, t: str, p: str, sow: str) -> str:
        if self.z_ncap_active:
            return f"VAS_NCAP({r},{t},{p},'1')"
        return f"{var}_NCAP({r},{t},{p}{sow})"

    def VAR_NCAP_GP(
        self,
        var: str | tuple[str, ImplicitSet | None],
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()],
        is_output: bool = False,
    ) -> ImplicitVariable | Sum:
        if self.z_ncap_active:
            ncap_var = self._g.VAS_NCAP.l if is_output else self._g.VAS_NCAP
            return ncap_var[r, t, p, "1"]  # type: ignore[return-value]
        else:
            var_id, var_set = extract_var_domain(var)
            NCAP = self._g.get_variable(f"{var_id}_NCAP")
            ncap_var = NCAP.l if is_output else NCAP
            return wrap_in_sum(ncap_var[r, t, p, *sow], var_set)  # type: ignore[arg-type]

    # VAR_RCAP / VAS_RCAP / Z_RCAP
    # $macro Z_RCAP(r,v,t,p,sow)  VAS_RCAP(r,v,t,p,'1')
    @property
    def z_rcap_active(self) -> bool:
        return self._active.get("Z_RCAP", False)

    @z_rcap_active.setter
    def z_rcap_active(self, value: bool) -> None:
        self._active["Z_RCAP"] = value

    def VAR_RCAP(self, var: str, r: str, v: str, t: str, p: str, sow: str) -> str:
        if self.z_rcap_active:
            return f"VAS_RCAP({r},{v},{t},{p},'1')"
        return f"{var}_RCAP({r},{v},{t},{p}{sow})"

    def VAR_RCAP_GP(
        self,
        var: str | tuple[str, ImplicitSet | None],
        r: SET_OR_ALIAS,
        v: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()],
    ) -> ImplicitVariable | Sum:
        if self.z_rcap_active:
            return self._g.VAS_RCAP[r, v, t, p, "1"]
        else:
            var_id, var_set = extract_var_domain(var)
            rcap = self._g.get_variable(f"{var_id}_RCAP")
            return wrap_in_sum(rcap[r, v, t, p, *sow], var_set)

    # VAR_SCAP / VAS_SCAP / Z_SCAP
    # $macro Z_SCAP(r,v,t,p,sow)  VAS_SCAP(r,v,t,p,'1')
    @property
    def z_scap_active(self) -> bool:
        return self._active.get("Z_SCAP", False)

    @z_scap_active.setter
    def z_scap_active(self, value: bool) -> None:
        self._active["Z_SCAP"] = value

    def VAR_SCAP(self, var: str, r: str, v: str, t: str, p: str, sow: str) -> str:
        if self.z_scap_active:
            return f"VAS_SCAP({r},{v},{t},{p},'1')"
        return f"{var}_SCAP({r},{v},{t},{p}{sow})"

    def VAR_SCAP_GP(
        self,
        var: tuple[str, ImplicitSet | None],
        r: SET_OR_ALIAS,
        v: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()],
        is_output: bool = False,
    ) -> ImplicitVariable | Sum:
        if self.z_scap_active:
            scap_var = self._g.VAS_SCAP.l if is_output else self._g.VAS_SCAP
            return scap_var[r, v, t, p, "1"]  # type: ignore[return-value]
        else:
            var_id, var_set = var
            SCAP = self._g.get_variable(f"{var_id}_SCAP")
            scap_var = SCAP.l if is_output else SCAP
            return wrap_in_sum(scap_var[r, v, t, p, *sow], var_set)  # type: ignore[arg-type]

    # VAR_DRCAP / VAS_DRCAP / Z_DRCAP
    # $macro Z_DRCAP(r,v,t,p,w,j) VAS_DRCAP(r,v,t,p,'1',j)
    @property
    def z_drcap_active(self) -> bool:
        return self._active.get("Z_DRCAP", False)

    @z_drcap_active.setter
    def z_drcap_active(self, value: bool) -> None:
        self._active["Z_DRCAP"] = value

    def VAR_DRCAP(
        self, var: str, r: str, v: str, t: str, p: str, sow: str, j: str
    ) -> str:
        if self.z_drcap_active:
            return f"VAS_DRCAP({r},{v},{t},{p},'1',{j})"
        return f"{var}_DRCAP({r},{v},{t},{p}{sow},{j})"

    def VAR_DRCAP_GP(
        self,
        var: str | tuple[str, ImplicitSet | None],
        r: SET_OR_ALIAS,
        v: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()],
        j: SET_OR_ALIAS | str,
    ) -> ImplicitVariable | Sum:
        if self.z_drcap_active:
            return self._g.VAS_DRCAP[r, v, t, p, "1", j]
        else:
            var_id, var_set = extract_var_domain(var)
            drcap = self._g.get_variable(f"{var_id}_DRCAP")
            return wrap_in_sum(drcap[r, v, t, p, *sow, j], var_set)

    # VAR_DNCAP / VAS_DNCAP / Z_DNCAP
    # $macro Z_DNCAP(r,t,p,sow,j) VAS_DNCAP(r,t,p,'1',j)
    @property
    def z_dncap_active(self) -> bool:
        return self._active.get("Z_DNCAP", False)

    @z_dncap_active.setter
    def z_dncap_active(self, value: bool) -> None:
        self._active["Z_DNCAP"] = value

    def VAR_DNCAP(self, var: str, r: str, t: str, p: str, sow: str, j: str) -> str:
        if self.z_dncap_active:
            return f"VAS_DNCAP({r},{t},{p},'1',{j})"
        return f"{var}_DNCAP({r},{t},{p}{sow},{j})"

    def VAR_DNCAP_GP(
        self,
        var: str | tuple[str, ImplicitSet | None],
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()],
        j: SET_OR_ALIAS | str,
    ) -> ImplicitVariable | Sum:
        if self.z_dncap_active:
            return self._g.VAS_DNCAP[r, t, p, "1", j]
        else:
            var_id, var_set = extract_var_domain(var)
            dncap = self._g.get_variable(f"{var_id}_DNCAP")
            return wrap_in_sum(dncap[r, t, p, *sow, j], var_set)

    # VAR_SNCAP / VAS_SNCAP / Z_SNCAP
    # $macro Z_SNCAP(r,t,p,sow)   VAS_SNCAP(r,t,p,'1')
    @property
    def z_sncap_active(self) -> bool:
        return self._active.get("Z_SNCAP", False)

    @z_sncap_active.setter
    def z_sncap_active(self, value: bool) -> None:
        self._active["Z_SNCAP"] = value

    def VAR_SNCAP(self, var: str, r: str, t: str, p: str, sow: str) -> str:
        if self.z_sncap_active:
            return f"VAS_SNCAP({r},{t},{p},'1')"
        return f"{var}_SNCAP({r},{t},{p}{sow})"

    def VAR_SNCAP_GP(
        self,
        var: str | tuple[str, ImplicitSet | None],
        r: SET_OR_ALIAS,
        t: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()],
    ) -> ImplicitVariable | Sum:
        if self.z_sncap_active:
            return self._g.VAS_SNCAP[r, t, p, "1"]
        else:
            var_id, var_set = extract_var_domain(var)
            sncap = self._g.get_variable(f"{var_id}_SNCAP")
            return wrap_in_sum(sncap[r, t, p, *sow], var_set)

    # VAR_XCAP / VAS_XCAP / Z_XCAP
    # $macro Z_XCAP(r,t,p,sow)  VAS_XCAP(r,t,p,'1')
    @property
    def z_xcap_active(self) -> bool:
        return self._active.get("Z_XCAP", False)

    @z_xcap_active.setter
    def z_xcap_active(self, value: bool) -> None:
        self._active["Z_XCAP"] = value

    def VAR_XCAP(self, var: str, r: str, t: str, p: str, sow: str) -> str:
        if self.z_xcap_active:
            return f"VAS_XCAP({r},{t},{p},'1')"
        return f"{var}_XCAP({r},{t},{p}{sow})"

    # EQ_OBJINV / ES_OBJINV / Q_OBJINV
    @property
    def q_objinv_active(self) -> bool:
        return self._active.get("Q_OBJINV", False)

    @q_objinv_active.setter
    def q_objinv_active(self, value: bool) -> None:
        self._active["Q_OBJINV"] = value

    def EQ_OBJINV_GP(
        self,
        eq: str,
        sow: SowGPType,
    ) -> tuple[Any, SowGPType]:
        """$macro Q_OBJINV(rc,sow) ES_OBJINV(rc,SOW('1')) of recurrin.stc."""
        if self.q_objinv_active:
            return self._g.es_objinv, ("1",)
        return self._g.get_equation(f"{eq}_OBJINV"), sow

    # EQ_OBJFIX / ES_OBJFIX / Q_OBJFIX
    @property
    def q_objfix_active(self) -> bool:
        return self._active.get("Q_OBJFIX", False)

    @q_objfix_active.setter
    def q_objfix_active(self, value: bool) -> None:
        self._active["Q_OBJFIX"] = value

    def EQ_OBJFIX_GP(
        self,
        eq: str,
        sow: SowGPType,
    ) -> tuple[Any, SowGPType]:
        """$macro Q_OBJFIX(rc,sow) ES_OBJFIX(rc,SOW('1')) of recurrin.stc."""
        if self.q_objfix_active:
            return self._g.es_objfix, ("1",)
        return self._g.get_equation(f"{eq}_OBJFIX"), sow

    # EQ_OBJSALV / ES_OBJSALV / Q_OBJSALV
    @property
    def q_objsalv_active(self) -> bool:
        return self._active.get("Q_OBJSALV", False)

    @q_objsalv_active.setter
    def q_objsalv_active(self, value: bool) -> None:
        self._active["Q_OBJSALV"] = value

    def EQ_OBJSALV_GP(
        self,
        eq: str,
        sow: SowGPType,
    ) -> tuple[Any, SowGPType]:
        """$macro Q_OBJSALV(rc,sow) ES_OBJSALV(rc,SOW('1')) of recurrin.stc."""
        if self.q_objsalv_active:
            return self._g.es_objsalv, ("1",)
        return self._g.get_equation(f"{eq}_OBJSALV"), sow

    # EQ_CPT / ES{G,E,L}_CPT / Q{G,E,L}_CPT
    @property
    def q_cpt_active(self) -> bool:
        return self._active.get("Q_CPT", False)

    @q_cpt_active.setter
    def q_cpt_active(self, value: bool) -> None:
        self._active["Q_CPT"] = value

    def EQ_CPT_GP(
        self,
        eq: str,
        sense: Literal["G", "E", "L"],
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
    ) -> tuple[Any, tuple[Literal["1"] | SET_OR_ALIAS, ...] | tuple[()]]:
        """$macro QG_CPT/QE_CPT/QL_CPT(rtp,swt) ES{G,E,L}_CPT(rtp,T,SOW('1')) of
        recurrin.stc."""

        if self.q_cpt_active:
            return self._g.get_equation(f"ES{sense}_CPT"), (self._g.t, "1")
        return self._g.get_equation(f"{eq}{sense}_CPT"), swt

    # EQ_DSCRET / ES_DSCRET / Q_DSCRET
    @property
    def q_dscret_active(self) -> bool:
        return self._active.get("Q_DSCRET", False)

    @q_dscret_active.setter
    def q_dscret_active(self, value: bool) -> None:
        self._active["Q_DSCRET"] = value

    def EQ_DSCRET_GP(
        self,
        eq: str,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
    ) -> tuple[Any, tuple[Literal["1"] | SET_OR_ALIAS, ...] | tuple[()]]:
        """$macro Q_DSCRET(cpt,sw) ES_DSCRET(cpt,T,SOW('1')) of recurrin.stc."""
        if self.q_dscret_active:
            return self._g.es_dscret, (self._g.t, "1")
        return self._g.get_equation(f"{eq}_DSCRET"), swt

    # EQ_CUMRET / ES_CUMRET / Q_CUMRET
    @property
    def q_cumret_active(self) -> bool:
        return self._active.get("Q_CUMRET", False)

    @q_cumret_active.setter
    def q_cumret_active(self, value: bool) -> None:
        self._active["Q_CUMRET"] = value

    def EQ_CUMRET_GP(
        self,
        eq: str,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
    ) -> tuple[Any, tuple[Literal["1"] | SET_OR_ALIAS, ...] | tuple[()]]:
        """$macro Q_CUMRET(r,v,p,w) ES_CUMRET(r,v,p,T,SOW('1')) of
        recurrin.stc: the equation is always ES_CUMRET, and its swt argument
        is pinned to '1'."""
        if self.q_cumret_active:
            return self._g.es_cumret, (self._g.t, "1")
        return self._g.get_equation(f"{eq}_CUMRET"), swt

    # EQL_REFIT / ESL_REFIT / QL_REFIT
    @property
    def ql_refit_active(self) -> bool:
        return self._active.get("QL_REFIT", False)

    @ql_refit_active.setter
    def ql_refit_active(self, value: bool) -> None:
        self._active["QL_REFIT"] = value

    def EQL_REFIT_GP(
        self,
        eq: str,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
    ) -> tuple[Any, tuple[Literal["1"] | SET_OR_ALIAS, ...] | tuple[()]]:
        """$macro QL_REFIT(rttp,l,swt) ESL_REFIT(rttp,l,T,SOW('1')) of
        recurrin.stc: the equation is always ESL_REFIT, and its swt argument
        is pinned to '1'."""
        if self.ql_refit_active:
            return self._g.esl_refit, (self._g.t, "1")
        return self._g.get_equation(f"{eq}L_REFIT"), swt

    # EQL_SCAP / ESL_SCAP / QL_SCAP (solveda=="1" only; the solveda!="1" case
    # is the plain g.ql_scap = g.esl_scap alias set in recurrin_stc.py)
    @property
    def ql_scap_active(self) -> bool:
        return self._active.get("QL_SCAP", False)

    @ql_scap_active.setter
    def ql_scap_active(self, value: bool) -> None:
        self._active["QL_SCAP"] = value

    def EQL_SCAP_GP(
        self,
        eq: str,
        sow: SowGPType,
    ) -> tuple[Any, SowGPType]:
        """$macro QL_SCAP(rtp,ip,sow) ESL_SCAP(rtp,ip,'1') of recurrin.stc"""
        if self.ql_scap_active:
            return self._g.esl_scap, ("1",)
        return self._g.get_equation(f"{eq}L_SCAP"), sow

    # EQ_DSCNCAP / ES_DSCNCAP / Q_DSCNCAP
    @property
    def q_dscncap_active(self) -> bool:
        return self._active.get("Q_DSCNCAP", False)

    @q_dscncap_active.setter
    def q_dscncap_active(self, value: bool) -> None:
        self._active["Q_DSCNCAP"] = value

    def EQ_DSCNCAP_GP(
        self,
        eq: str,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
    ) -> tuple[Any, tuple[Literal["1"] | SET_OR_ALIAS, ...] | tuple[()]]:
        """$macro Q_DSCNCAP(rtp,sw) ES_DSCNCAP(rtp,T,SOW('1')) of
        recurrin.stc."""
        if self.q_dscncap_active:
            return self._g.es_dscncap, (self._g.t, "1")
        return self._g.get_equation(f"{eq}_DSCNCAP"), swt

    # EQ_DSCONE / ES_DSCONE / Q_DSCONE
    @property
    def q_dscone_active(self) -> bool:
        return self._active.get("Q_DSCONE", False)

    @q_dscone_active.setter
    def q_dscone_active(self, value: bool) -> None:
        self._active["Q_DSCONE"] = value

    def EQ_DSCONE_GP(
        self,
        eq: str,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
    ) -> tuple[Any, tuple[Literal["1"] | SET_OR_ALIAS, ...] | tuple[()]]:
        """$macro Q_DSCONE(rtp,swt) ES_DSCONE(rtp,T,SOW('1')) of recurrin.stc."""
        if self.q_dscone_active:
            return self._g.es_dscone, (self._g.t, "1")
        return self._g.get_equation(f"{eq}_DSCONE"), swt

    # EQ_CUM / ES_CUM{NET,PRD} / Q_CUM{NET,PRD}
    @property
    def q_cum_active(self) -> bool:
        return self._active.get("Q_CUM", False)

    @q_cum_active.setter
    def q_cum_active(self, value: bool) -> None:
        self._active["Q_CUM"] = value

    def EQ_CUM_GP(
        self,
        eq: str,
        arg2: Literal["NET", "PRD"],
        sow: SowGPType,
    ) -> tuple[Any, SowGPType]:
        """$macro Q_CUMNET/Q_CUMPRD(rc,y1,y2,sow) ES_CUM{NET,PRD}(rc,y1,y2,'1')
        of recurrin.stc."""
        if self.q_cum_active:
            return self._g.get_equation(f"ES_CUM{arg2}"), ("1",)
        return self._g.get_equation(f"{eq}_CUM{arg2}"), sow

    # VAR_CUMCOM / VAS_CUMCOM / Z_CUMCOM
    @property
    def z_cumcom_active(self) -> bool:
        return self._active.get("Z_CUMCOM", False)

    @z_cumcom_active.setter
    def z_cumcom_active(self, value: bool) -> None:
        self._active["Z_CUMCOM"] = value

    def VAR_CUMCOM_GP(
        self,
        var: str,
        r: SET_OR_ALIAS,
        c: SET_OR_ALIAS,
        cv: SET_OR_ALIAS | str,
        y1: SET_OR_ALIAS,
        y2: SET_OR_ALIAS,
        w: SowGPType,
    ) -> ImplicitVariable:
        """$macro Z_CUMCOM(r,c,cv,y1,y2,w) VAS_CUMCOM(r,c,cv,y1,y2,'1') of
        recurrin.stc.
        """
        if self.z_cumcom_active:
            return self._g.VAS_CUMCOM[r, c, cv, y1, y2, "1"]
        cumcom = self._g.get_variable(f"{var}_CUMCOM")
        return cumcom[r, c, cv, y1, y2, *w]

    # EQ_CUMFLO / ES_CUMFLO / Q_CUMFLO
    @property
    def q_cumflo_active(self) -> bool:
        return self._active.get("Q_CUMFLO", False)

    @q_cumflo_active.setter
    def q_cumflo_active(self, value: bool) -> None:
        self._active["Q_CUMFLO"] = value

    def EQ_CUMFLO_GP(
        self,
        eq: str,
        sow: SowGPType,
    ) -> tuple[Any, SowGPType]:
        """$macro Q_CUMFLO(rpcyy,sw) ES_CUMFLO(rpcyy,'1') of recurrin.stc
        (solveda=="1" branch): the equation is always ES_CUMFLO, and its sw
        argument is pinned to '1'."""
        if self.q_cumflo_active:
            return self._g.es_cumflo, ("1",)
        return self._g.get_equation(f"{eq}_CUMFLO"), sow

    # VAR_CUMFLO / VAS_CUMFLO / Z_CUMFLO
    @property
    def z_cumflo_active(self) -> bool:
        return self._active.get("Z_CUMFLO", False)

    @z_cumflo_active.setter
    def z_cumflo_active(self, value: bool) -> None:
        self._active["Z_CUMFLO"] = value

    def VAR_CUMFLO_GP(
        self,
        var: str,
        r: SET_OR_ALIAS,
        p: SET_OR_ALIAS,
        cv: SET_OR_ALIAS | str,
        y1: SET_OR_ALIAS,
        y2: SET_OR_ALIAS,
        w: SowGPType | tuple[SET_OR_ALIAS, ...],
    ) -> ImplicitVariable:
        """$macro Z_CUMFLO(r,p,cv,y1,y2,w) VAS_CUMFLO(r,p,cv,y1,y2,'1') of
        recurrin.stc .
        """
        if self.z_cumflo_active:
            return self._g.VAS_CUMFLO[r, p, cv, y1, y2, "1"]
        cumflo = self._g.get_variable(f"{var}_CUMFLO")
        return cumflo[r, p, cv, y1, y2, *w]

    # EQ_BNDCST / ES_BNDCST / Q_BNDCST
    @property
    def q_bndcst_active(self) -> bool:
        return self._active.get("Q_BNDCST", False)

    @q_bndcst_active.setter
    def q_bndcst_active(self, value: bool) -> None:
        self._active["Q_BNDCST"] = value

    def EQ_BNDCST_GP(
        self,
        eq: str,
        sow: SowGPType,
    ) -> tuple[Any, SowGPType]:
        """$macro Q_BNDCST(r,y,y2,c,m,w) ES_BNDCST(r,y,y2,c,m,'1') of
        recurrin.stc"""
        if self.q_bndcst_active:
            return self._g.get_equation("ES_BNDCST"), ("1",)
        return self._g.get_equation(f"{eq}_BNDCST"), sow

    # VAR_CUMCST / VAS_CUMCST / Z_CUMCST
    @property
    def z_cumcst_active(self) -> bool:
        return self._active.get("Z_CUMCST", False)

    @z_cumcst_active.setter
    def z_cumcst_active(self, value: bool) -> None:
        self._active["Z_CUMCST"] = value

    def VAR_CUMCST_GP(
        self,
        var: str,
        r: SET_OR_ALIAS,
        y1: SET_OR_ALIAS,
        y2: SET_OR_ALIAS,
        cg: SET_OR_ALIAS,
        m: SET_OR_ALIAS,
        w: SowGPType,
    ) -> ImplicitVariable:
        """$macro Z_CUMCST(r,y1,y2,cg,m,w) VAS_CUMCST(r,y1,y2,cg,m,'1')"""
        if self.z_cumcst_active:
            return self._g.VAS_CUMCST[r, y1, y2, cg, m, "1"]
        cumcst = self._g.get_variable(f"{var}_CUMCST")
        return cumcst[r, y1, y2, cg, m, *w]

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
