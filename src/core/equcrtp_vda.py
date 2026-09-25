# equcrtp_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * EQ_UCRTP.MOD : Annual bounds for process dynamic development                 *
# *==============================================================================*
# * arg1 - jump label
# * arg2 - eq. declaration type
# * arg3 - eq. definition type
# * arg4 - bound type


from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Domain, Loop, Number, Ord, Set, SpecialValues, Sum, sparse
from gamspy.math import power, same_as

from core.base_class import GamsClass
from core.prepparm_gms import PrepparmGmsConfig, prepparm
from core.utils import generate_equation, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

EqucrtpPhases = Literal["INIT_EXT", "PREP_EXT", "PPM_EXT", "EQU_EXT"]


@dataclass
class EqucrtpVdaConfig:
    """Strongly typed data contract replacing legacy positional batch-include loops."""

    arg1: Literal[EqucrtpPhases]
    arg2: Literal["E", "N", ""] = ""
    arg3: Literal["E", "G", "L", ""] = ""
    arg4: tuple[Set | Alias | Literal["FX"]] | tuple[()] = ()


class EqucrtpVda(GamsClass):
    """Translation unit for equcrtp.vda."""

    # Instance attributes
    module_name: str = "equcrtp_vda"
    gams_source: str = "equcrtp.vda"

    def __init__(
        self: EqucrtpVda,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqucrtpVdaConfig,
    ):
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self: EqucrtpVda) -> None:
        cc = self.config
        if cc.arg1 == "INIT_EXT":
            self.tc.enqueue(self.init_ext)
        elif cc.arg1 == "PREP_EXT":
            self.label_prep_ext()
        elif cc.arg1 == "PPM_EXT":
            self.tc.enqueue(self.ppm_ext)
        elif cc.arg1 == "EQU_EXT":
            sense = cc.arg3
            if sense not in ["E", "G", "L"]:
                raise ValueError(f"Incompatible sense {sense}.")
            self.label_equ_ext(sense)  # type: ignore[arg-type]

    def init_ext(self: EqucrtpVda) -> None:
        g = self.tc
        (
            UcDynbnd,
            uncd1,
            ucnA,
            bd,
            prc_dynuc,
            ucn,
            side,
            r,
            ll,
            p,
            uc_cap,
            uc_ncap,
            uc_act,
            uc_com,
            c,
            Annual,
            s,
            uc_comnet,
            uc_comprd,
            comvar,
            Miyr1,
            Lastll,
        ) = (
            g.UcDynbnd,
            g.uncd1,
            g.ucnA,
            g.bd,
            g.prc_dynuc,
            g.ucn,
            g.side,
            g.r,
            g.ll,
            g.p,
            g.uc_cap,
            g.uc_ncap,
            g.uc_act,
            g.uc_com,
            g.c,
            g.Annual,
            g.s,
            g.uc_comnet,
            g.uc_comprd,
            g.comvar,
            g.Miyr1,
            g.Lastll,
        )
        # Move dynamic bounds to dedicated attribute
        if len(UcDynbnd):
            uncd1.setRecords(None)
            with Loop(UcDynbnd[ucnA, bd]):
                uncd1[ucnA] = True

            prc_dynuc[ucn, side, r, ll, p, "CAP", bd].where[UcDynbnd[ucn, bd]] = sparse(
                uc_cap[ucn, side, r, ll, p]
            )
            prc_dynuc[ucn, side, r, ll, p, "NCAP", bd].where[UcDynbnd[ucn, bd]] = (
                sparse(uc_ncap[ucn, side, r, ll, p])
            )
            prc_dynuc[ucn, side, r, ll, p, "ACT", bd].where[UcDynbnd[ucn, bd]] = sparse(
                uc_act[ucn, side, r, ll, p, "ANNUAL"]
            )
            uc_com[ucn[uncd1], "NET", side, r, ll, c, Annual[s], "UCN"] = sparse(
                uc_comnet[ucn, side, r, ll, c, s]
            )
            uc_com[ucn[uncd1], "PRD", side, r, ll, c, Annual[s], "UCN"] = sparse(
                uc_comprd[ucn, side, r, ll, c, s]
            )
            uc_cap[ucn[uncd1], side, r, ll, p] = 0
            uc_ncap[ucn[uncd1], side, r, ll, p] = 0
            uc_act[ucn[uncd1], side, r, ll, p, s] = 0
            uc_comprd[ucn[uncd1], side, r, ll, c, s] = 0
            uc_comnet[ucn[uncd1], side, r, ll, c, s] = 0

            # Set LHS default IE to 5 and RHS default to 10
            uc_com[ucnA[uncd1], comvar, "LHS", r, ll.lag(Ord(ll)), c, s, "UCN"].where[
                ~uc_com[ucnA, comvar, "LHS", r, "0", c, s, "UCN"]
                & uc_com[ucnA, comvar, "LHS", r, ll, c, s, "UCN"]
            ] = 5
            uc_com[ucnA[uncd1], comvar, "RHS", r, ll.lag(Ord(ll)), c, s, "UCN"].where[
                ~uc_com[ucnA, comvar, "RHS", r, "0", c, s, "UCN"]
                & uc_com[ucnA, comvar, "RHS", r, ll, c, s, "UCN"]
            ] = (
                uc_com[ucnA, comvar, "LHS", r, "0", c, s, "UCN"]
                + (Number(10)).where[~uc_com[ucnA, comvar, "LHS", r, "0", c, s, "UCN"]]
            )

            # If no RHS/LHS defined, set it to EPS/1 for all other side years except
            # for the IE option as on other side
            uc_com[ucnA, comvar, "RHS", r, ll, c, s, "UCN"].where[
                ~uc_com[ucnA, comvar, "RHS", r, "0", c, s, "UCN"]
                & uc_com[ucnA, comvar, "LHS", r, ll, c, s, "UCN"]
            ] = (
                Number(SpecialValues.EPS).where[~Miyr1[ll]]
                + uc_com[ucnA, comvar, "LHS", r, ll, c, s, "UCN"].where[Lastll[ll]]
            )
            uc_com[ucnA, comvar, "LHS", r, ll, c, s, "UCN"].where[
                ~uc_com[ucnA, comvar, "LHS", r, "0", c, s, "UCN"]
                & uc_com[ucnA, comvar, "RHS", r, ll, c, s, "UCN"]
            ] = (
                1
                + (uc_com[ucnA, comvar, "RHS", r, ll, c, s, "UCN"] - 1).where[
                    Lastll[ll]
                ]
            )

    def label_prep_ext(self: EqucrtpVda) -> None:
        self.env.set_scoped("reset", 1)
        self.add_records_to_universe_item(records=["PRC_DYNUC"])
        self.tc.enqueue(
            self.manipulate_lhs_and_rhs,
            dflbl=self.env.dflbl,
            def_iebd=self.env.def_iebd,
            reset=self.env.reset,
        )

    def manipulate_lhs_and_rhs(
        self: EqucrtpVda, dflbl: str, def_iebd: str, reset: int
    ) -> None:
        g = self.tc
        ucn, side, r, p = g.ucn, g.side, g.r, g.p
        t, ucgrptype, bd = g.t, g.ucgrptype, g.bd
        prc_dynuc = g.prc_dynuc

        if prc_dynuc.number_records:
            ll, UcGmapP, Lastll = g.ll, g.UcGmapP, g.Lastll
            # Set LHS default IE to 5 and RHS default to 10
            prc_dynuc[ucn, "LHS", r, ll.lag(Ord(ll)), p, ucgrptype, bd].where[
                ~prc_dynuc[ucn, "LHS", r, "0", p, ucgrptype, bd]
                & prc_dynuc[ucn, "LHS", r, ll, p, ucgrptype, bd]
            ] = 5
            prc_dynuc[ucn, "RHS", r, ll.lag(Ord(ll)), p, ucgrptype, bd].where[
                ~prc_dynuc[ucn, "RHS", r, "0", p, ucgrptype, bd]
                & prc_dynuc[ucn, "RHS", r, ll, p, ucgrptype, bd]
            ] = (
                prc_dynuc[ucn, "LHS", r, "0", p, ucgrptype, bd]
                + (Number(10)).where[~prc_dynuc[ucn, "LHS", r, "0", p, ucgrptype, bd]]
            )
            with Loop(bd):
                UcGmapP[r, ucn, ucgrptype, p].where[
                    prc_dynuc[ucn, "RHS", r, "0", p, ucgrptype, bd]
                ] = True
            # If no RHS defined, set RHS to EPS for all LHS years except for the IE option according to LHS
            prc_dynuc[ucn, "RHS", r, ll, p, ucgrptype, bd].where[
                ~prc_dynuc[ucn, "RHS", r, "0", p, ucgrptype, bd]
                & prc_dynuc[ucn, "LHS", r, ll, p, ucgrptype, bd]
            ] = (
                SpecialValues.EPS
                + prc_dynuc[ucn, "LHS", r, ll, p, ucgrptype, bd].where[Lastll[ll]]
            )
            # If no LHS defined, set LHS to 1 for all RHS years except for the IE option according to RHS
            prc_dynuc[ucn, "LHS", r, ll, p, ucgrptype, bd].where[
                ~prc_dynuc[ucn, "LHS", r, "0", p, ucgrptype, bd]
                & prc_dynuc[ucn, "RHS", r, ll, p, ucgrptype, bd]
            ] = (
                1
                + (prc_dynuc[ucn, "RHS", r, ll, p, ucgrptype, bd] - 1).where[Lastll[ll]]
            ).where[~same_as("NCAP", ucgrptype)]

            prepparm(
                module=self,
                cc=PrepparmGmsConfig(
                    arg1="PRC_DYNUC",
                    arg2=(ucn, side, r),
                    arg3=(p, ucgrptype, bd),
                    arg4=(),
                    arg5=t,
                    arg6=Number(1),
                    arg7=1,
                ),
                dflbl=dflbl,
                def_iebd=int(def_iebd),
                reset=reset,
            )

            (
                prc_dynuc,
                ucnA,
                Rhs,
                Rtp,
                tt,
                Miyr1,
                UcGmapP,
                UcJmap,
            ) = (
                g.prc_dynuc,
                g.ucnA,
                g.Rhs,
                g.Rtp,
                g.tt,
                g.Miyr1,
                g.UcGmapP,
                g.UcJmap,
            )
            # Disable growth/decay equation in first period of availability if no constant specified
            prc_dynuc[ucnA, Rhs, Rtp[r, tt[t + 1], p], ucgrptype, bd].where[
                Rtp[r, t, p] - Miyr1[tt]
                & ~UcGmapP[r, ucnA, ucgrptype, p]
                & prc_dynuc[ucnA, "LHS", r, "0", p, ucgrptype, bd]
            ] = 0
            # Set final UC_GMAPs for REDUCE
            with Loop(bd):
                UcJmap["1", ucnA, Rhs, r, t[Miyr1], p, ucgrptype].where[
                    prc_dynuc[ucnA, Rhs, r, "0", p, ucgrptype, bd]
                ] = True

        UcDynbnd, ucnA, UcTSucc = g.UcDynbnd, g.ucnA, g.UcTSucc
        with Loop(UcDynbnd[ucnA, bd]):
            UcTSucc[r, ucnA, "0"] = True

    def ppm_ext(self: EqucrtpVda) -> None:
        g = self.tc
        UcDynbnd, ucnA, bd, UcOn, r, UcRSum, UcREach = (
            g.UcDynbnd,
            g.ucnA,
            g.bd,
            g.UcOn,
            g.r,
            g.UcRSum,
            g.UcREach,
        )
        # Make sure that standard UCs are not generated
        with Loop(UcDynbnd[ucnA, bd]):
            UcOn[r, ucnA] = False
            UcRSum[r, ucnA] = False
            UcREach[r, ucnA] = False

    def label_equ_ext(self: EqucrtpVda, sense: Literal["E", "G", "L"]) -> None:
        self.define_eq_ucrtp(sense)

        if self.config.arg2.upper() != "E":
            self.define_eq_ucrtc(sense)

    def define_eq_ucrtp(self, sense: Literal["E", "G", "L"]) -> None:
        g = self.tc
        cc = self.config
        (
            ucn,
            Rtp,
            p,
            ucgrptype,
            bd,
            t,
            v,
            tt,
            prc_dynuc,
            r,
            lead,
            Bdupx,
            RtpVintyr,
            Modlyear,
            PrcTs,
            s,
            RtpVara,
        ) = (
            g.ucn,
            g.Rtp,
            g.p,
            g.ucgrptype,
            g.bd,
            g.t,
            g.v,
            g.tt,
            g.prc_dynuc,
            g.r,
            g.lead,
            g.Bdupx,
            g.RtpVintyr,
            g.Modlyear,
            g.PrcTs,
            g.s,
            g.RtpVara,
        )

        r_t = self.env.r_t_GP
        sws = self.env.sws_GP
        sow = self.env.sow_GP
        swt = self.env.swt_GP
        vartt_id, vartt_set = self.env.vartt_GP

        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
        VARTT_ACT = g.get_variable(f"{vartt_id}_ACT")
        eqe_ucrtp = g.get_equation(f"{self.env.eq}{cc.arg2}_UCRTP")

        eqe_ucrtp[ucn, Rtp[*r_t, p], ucgrptype, bd[*cc.arg4], *swt].where[
            macro.prc_dynuc_mx.prc_dynuc_GP(ucn, "RHS", r, t, p, ucgrptype, bd)
        ] = generate_equation(
            (
                # * Difference in capacity between previous and current period
                Sum(
                    same_as(t - 1, v[tt]).where[Rtp[r, v, p]],
                    power(prc_dynuc[ucn, "LHS", r, t, p, ucgrptype, bd], lead[t])
                    * macro.VAR_CAP_GP(self.env.varv_GP, r, v, p, sws),
                )
                * (1 - (Number(2)).where[Bdupx[bd]])
                - macro.VAR_CAP_GP(self.env.var, r, t, p, sow)
                * (1 - (Number(2)).where[Bdupx[bd]])
            ).where[same_as("CAP", ucgrptype)]
            + (
                # * Difference in NCAP between previous and current period
                Sum(
                    same_as(t - 1, v[tt]).where[Rtp[r, v, p]],
                    power(prc_dynuc[ucn, "LHS", r, t, p, ucgrptype, bd], lead[t])
                    * macro.VAR_NCAP_GP(self.env.varv_GP, r, v, p, sws),
                )
                * (1 - (Number(2)).where[Bdupx[bd]])
                - macro.VAR_NCAP_GP(self.env.var, r, t, p, sow)
                * (1 - (Number(2)).where[Bdupx[bd]])
            ).where[same_as("NCAP", ucgrptype)]
            + (
                # * Difference in ACT between previous and current period
                Sum(
                    same_as(t - 1, v[tt]).where[RtpVara[r, v, p]],
                    power(prc_dynuc[ucn, "LHS", r, t, p, ucgrptype, bd], lead[t])
                    * Sum(
                        Domain(RtpVintyr[r, Modlyear, v, p], PrcTs[r, p, s]),
                        wrap_in_sum(VARTT_ACT[r, Modlyear, v, p, s, *sws], vartt_set),
                    ),
                )
                * (1 - (Number(2)).where[Bdupx[bd]])
                - Sum(
                    Domain(RtpVintyr[r, Modlyear, t, p], PrcTs[r, p, s]),
                    VAR_ACT[r, Modlyear, t, p, s, *sow],
                )
                * (1 - (Number(2)).where[Bdupx[bd]])
            ).where[same_as("ACT", ucgrptype)],
            sense,
            (
                # * RHS constant term
                prc_dynuc[ucn, "RHS", r, t, p, ucgrptype, bd]
                * lead[t]
                * (-1 + (Number(2)).where[Bdupx[bd]])
            ),
        )

    def define_eq_ucrtc(self, sense: Literal["E", "G", "L"]) -> None:
        g = self.tc
        cc = self.config
        (
            ucn,
            comvar,
            Rtc,
            c,
            Annual,
            s,
            bd,
            t,
            Y,
            tt,
            uc_com,
            lead,
            RhsCombal,
            r,
            Bdupx,
            RhsComprd,
            UcDynbnd,
        ) = (
            g.ucn,
            g.comvar,
            g.Rtc,
            g.c,
            g.Annual,
            g.s,
            g.bd,
            g.t,
            g.Y,
            g.tt,
            g.uc_com,
            g.lead,
            g.RhsCombal,
            g.r,
            g.Bdupx,
            g.RhsComprd,
            g.UcDynbnd,
        )

        r_t = self.env.r_t_GP
        sws = self.env.sws_GP
        sow = self.env.sow_GP
        swt = self.env.swt_GP
        vartt_id, vartt_set = self.env.vartt_GP

        VAR_COMNET = g.get_variable(f"{self.env.var}_COMNET")
        VAR_COMPRD = g.get_variable(f"{self.env.var}_COMPRD")
        VARTT_COMNET = g.get_variable(f"{vartt_id}_COMNET")
        VARTT_COMPRD = g.get_variable(f"{vartt_id}_COMPRD")
        eqe_ucrtc = g.get_equation(f"{self.env.eq}{cc.arg2}_UCRTC")

        VARTT_COMNET_expr = wrap_in_sum(VARTT_COMNET[r, Y, c, s, *sws], vartt_set)
        VARTT_COMPRD_expr = wrap_in_sum(VARTT_COMPRD[r, Y, c, s, *sws], vartt_set)

        eqe_ucrtc[ucn, comvar, Rtc[*r_t, c], Annual[s], bd[*cc.arg4], *swt].where[
            uc_com[ucn, comvar, "RHS", Rtc, s, "UCN"] & UcDynbnd[ucn, bd]
        ] = generate_equation(
            (
                # * Difference in COMNET between previous and current period
                Sum(
                    same_as(t - 1, Y[tt]).where[Rtc[r, Y, c]],
                    power(uc_com[ucn, comvar, "LHS", Rtc, s, "UCN"], lead[t])
                    * Sum(
                        RhsCombal[r, Y, c, s],
                        VARTT_COMNET_expr,
                    ),
                )
                * (1 - (Number(2)).where[Bdupx[bd]])
                - Sum(RhsCombal[r, t, c, s], VAR_COMNET[r, t, c, s, *sow])
                * (1 - (Number(2)).where[Bdupx[bd]])
            ).where[same_as("NET", comvar)]
            + (
                # * Difference in COMPRD between previous and current period
                Sum(
                    same_as(t - 1, Y[tt]).where[Rtc[r, Y, c]],
                    power(uc_com[ucn, comvar, "LHS", Rtc, s, "UCN"], lead[t])
                    * Sum(
                        RhsComprd[r, Y, c, s],
                        VARTT_COMPRD_expr,
                    ),
                )
                * (1 - (Number(2)).where[Bdupx[bd]])
                - Sum(RhsComprd[r, t, c, s], VAR_COMPRD[r, t, c, s, *sow])
                * (1 - (Number(2)).where[Bdupx[bd]])
            ).where[same_as("PRD", comvar)],
            sense,
            # * RHS constant term
            (
                uc_com[ucn, comvar, "RHS", r, t, c, s, "UCN"]
                * lead[t]
                * (-1 + (Number(2)).where[Bdupx[bd]])
            ),
        )
