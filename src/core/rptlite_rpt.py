# rptlite_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * RPTLITE.rpt is the main driver for the light-weight report writer for TIMES
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Loop, Number, Parameter, Set, Sum
from gamspy.math import project

from core.base_class import GamsClass
from core.cost_ann_rpt import CostAnnRpt, CostAnnRptConfig, cost_ann_rpt
from core.par_uc_rpt import declare_par_uc_rpt_params, par_uc_rpt
from core.rpt_obj_rpt import rpt_obj_rpt
from core.rptmisc_rpt import rptmisc_rpt
from core.sol_flo_red import sol_flo_red
from core.sol_ire_rpt import sol_ire_rpt
from core.solsetv_v3 import SolsetvV3
from core.solsysd_v3 import SolsysdV3
from core.utils import add_records, apply_v_scope, resolve_ctst

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


# rptlite.rpt:143-144: $BATINCLUDE sol_flo.red PAR_FLO '' .L / M .M - both
# calls leave sol_flo.red's %4 blank, single source of truth for every
# caller (RptliteRpt._label_report, solve_stc.py) that must resolve V
# (sol_flo.red:11's SET%4 V VAR) before reaching rptlite_rpt_part1, which
# has no env access of its own to do it.
SOL_FLO_RED_V_SCOPE = "SCOPED"


@dataclass
class RptliteRptConfig:
    arg1: str = ""  # Alias s
    arg2: tuple[Alias] | tuple[()] = ()  # Alias ww
    arg3: tuple[Literal["'1',"] | Alias | Set] | tuple[()] = ()
    arg4: tuple[Literal["NO"]] | tuple[()] | str = ()


class RptliteRpt(GamsClass):
    """Translation unit for rptlite.rpt."""

    module_name: str = "rptlite_rpt"
    gams_source: str = "rptlite.rpt"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: RptliteRptConfig
    ):
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        cc = self.config

        # $IF NOT %SOLVEDA%==1 $SHIFT SHIFT SHIFT
        if self.env.solveda != "1":
            cc.arg1 = cc.arg4  # type: ignore
            cc.arg2 = ()
            cc.arg3 = ()
            cc.arg4 = ()

        if cc.arg4 == ("NO",):
            self._label_report(cc=cc)
            return

        self.include(
            SolsysdV3(
                self.tc,
                self.env,
                mode="SYSUC",
                set_name="SYSUC",
                map=True,
                set_prefix=self.env.sysprefix,
                labels=[
                    "VAR",
                    "VARX",
                    "INV",
                    "INVX",
                    "INV+",
                    "INVX+",
                    "FIX",
                    "FIXX",
                    "IRE",
                    "COM",
                    "ACT",
                    "FLO",
                    "ELS",
                    "DAM",
                    "DAS",
                    "DAM-EXT+",
                ],
            )
        )
        self.include(
            SolsysdV3(
                self.tc,
                self.env,
                mode="SYSUC",
                map=False,
                set_name="SYSUC",
                set_prefix=self.env.sysprefix,
                labels=[
                    "INSTCAP",
                    "LUMPINV",
                    "LUMPIX",
                    "COST",
                    "CGAP",
                    "GGAP",
                    "RNGLO",
                    "RNGUP",
                    "RATIO",
                    "GRATIO",
                    "LEVCOST",
                ],
            )
        )

        # Moved up to rptmain_mod.py
        # g.ww = Alias(m, name="WW", alias_with=g.allsow)

        if self.env.is_set("rpt_opt"):
            if g.rpt_opt is not None:
                add_records(g.rpt_opt, self.env.rpt_opt)
            else:
                g.rpt_opt = Parameter(m, name="RPT_OPT", records=self.env.rpt_opt)

        self.tc.enqueue(self.exec1, rpt_flots=self.env.rpt_flots == "COM")

        (
            j,
            r,
            allyear,
            p,
            cur,
            ll,
            t,
            c,
            ts,
            reg,
            com,
            prc,
            bd,
            year,
            sysuc,
            io,
            s,
            item,
            cg,
            ie,
            allr,
            ucn,
            costagg,
            ucgrptype,
        ) = (
            g.j,
            g.r,
            g.allyear,
            g.p,
            g.cur,
            g.ll,
            g.t,
            g.c,
            g.ts,
            g.Reg,
            g.Com,
            g.prc,
            g.bd,
            g.year,
            g.sysuc,
            g.io,
            g.s,
            g.item,
            g.cg,
            g.ie,
            g.allr,
            g.ucn,
            g.costagg,
            g.ucgrptype,
        )

        g.rtp_obj = Parameter(m, name="RTP_OBJ", domain=[j, r, allyear, p, cur])
        g.rtp_npv = Parameter(m, name="RTP_NPV", domain=[j, r, allyear, p, cur])
        g.par_actc = Parameter(m, name="PAR_ACTC", domain=[j, r, ll, t, p, c, cur])
        g.par_floc = Parameter(m, name="PAR_FLOC", domain=[j, r, ll, t, p, c, cur])
        g.par_comc = Parameter(m, name="PAR_COMC", domain=[j, r, t, c, cur])
        g.par_rpmx = Parameter(m, name="PAR_RPMX", domain=[r, p, j, ll, t, c, cur])
        g.par_rcmx = Parameter(m, name="PAR_RCMX", domain=[r, c, j, t, cur])
        g.par_objcap = Parameter(m, name="PAR_OBJCAP", domain=[r, allyear, p, cur])
        g.par_xpri = Parameter(m, name="PAR_XPRI", domain=[r, t, p, c, ts, reg, com])
        g.coef_objinv = Parameter(m, name="COEF_OBJINV", domain=[r, allyear, prc])
        if not g.declared(g.coef_obinv):
            g.coef_obinv = Parameter(m, name="COEF_OBINV", domain=[r, allyear, p, cur])
        if not g.declared(g.coef_obfix):
            g.coef_obfix = Parameter(m, name="COEF_OBFIX", domain=[r, allyear, p, cur])
        if not g.declared(g.coef_crf):
            g.coef_crf = Parameter(m, name="COEF_CRF", domain=[r, allyear, p, cur])
        g.var_ncaprng = Parameter(m, name="VAR_NCAPRNG", domain=[r, allyear, p, bd])
        g.cstvnt = Parameter(m, name="CSTVNT", domain=[j, r, ll, year, p, sysuc])
        g.cstvpj = Parameter(m, name="CSTVPJ", domain=[r, ll, p, j, sysuc, year])
        g.f_vio = Parameter(m, name="F_VIO", domain=[r, allyear, t, p, io])
        g.f_ios = Parameter(m, name="F_IOS", domain=[r, allyear, t, p, c, s])
        g.f_inout = Parameter(m, name="F_INOUT", domain=[r, allyear, t, p, c, io])
        g.f_inouts = Parameter(m, name="F_INOUTS", domain=[r, allyear, t, p, c, s, io])
        g.reg_obj = Parameter(m, name="REG_OBJ", domain=[reg])
        g.bc_invact = Parameter(m, name="BC_INVACT", domain=[r, allyear, ll, prc, s])
        g.bc_invtot = Parameter(m, name="BC_INVTOT", domain=[r, allyear, prc])
        g.val_flo = Parameter(m, name="VAL_FLO", domain=[r, allyear, ll, prc, c])
        g.par_rtcs = Parameter(m, name="PAR_RTCS", domain=[r, t, c, s])
        g.par_top = Parameter(m, name="PAR_TOP", domain=[r, t, p, c, io])

        g.NcapYes = Set(m, name="NCAP_YES", domain=[r, allyear, p])
        g.FIoset = Set(m, name="F_IOSET", domain=[r, allyear, t, p, c, s, io])
        g.Rvtpc = Set(m, name="RVTPC", domain=[r, allyear, t, p, c])
        g.Rttc = Set(m, name="RTTC", domain=[r, allyear, c])
        g.pastcv = Set(m, name="PASTCV", records=["0", "€"])
        rpm = g.rpm = Set(m, name="RPM", records=["-", "+"])
        g.Rnglim = Set(m, name="RNGLIM", domain=[sysuc])
        g.Sysinv = Set(m, name="SYSINV", domain=[sysuc])
        g.Sysinv = Set(m, name="SYSINV", domain=[sysuc])
        g.Sucmap = Set(
            m,
            name="SUCMAP",
            domain=[j, sysuc],
            records=[
                ("2", f"{self.env.sysprefix}LUMPINV"),
                ("2", f"{self.env.sysprefix}INV+"),
                ("1", f"{self.env.sysprefix}LUMPIX"),
                ("1", f"{self.env.sysprefix}INVX+"),
            ],
        )
        g.Rngmap = Set(
            m,
            name="RNGMAP",
            domain=[sysuc, bd],
            records=[
                (f"{self.env.sysprefix}RNGLO", "LO"),
                (f"{self.env.sysprefix}RNGUP", "UP"),
            ],
        )

        self.tc.enqueue(self.exec3)

        g.objval_1 = Parameter(m, name="OBJVAL_1", records=0)
        g.objval_2 = Parameter(m, name="OBJVAL_2", records=0)

        g.sysone = Parameter(
            m, name="SYSONE", domain=[sysuc], records=[(f"{self.env.sysprefix}INV", 1)]
        )
        g.sysplit = Parameter(m, name="SYSPLIT", domain=[sysuc])

        arg1 = next(iter(cc.arg1), "")
        g.set_parameter(
            name=f"{arg1}CST_PVC",
            parameter=Parameter(
                m, name=f"{arg1}CST_PVC", domain=[*cc.arg2, sysuc, r, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_PVC",
            parameter=Parameter(
                m, name=f"{arg1}CST_PVC", domain=[*cc.arg2, sysuc, r, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_PVP",
            parameter=Parameter(
                m, name=f"{arg1}CST_PVP", domain=[*cc.arg2, sysuc, r, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}F_IN",
            parameter=Parameter(
                m, name=f"{arg1}F_IN", domain=[*cc.arg2, r, allyear, t, p, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}F_OUT",
            parameter=Parameter(
                m, name=f"{arg1}F_OUT", domain=[*cc.arg2, r, allyear, t, p, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}P_OUT",
            parameter=Parameter(
                m, name=f"{arg1}P_OUT", domain=[*cc.arg2, r, t, p, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}AGG_OUT",
            parameter=Parameter(
                m, name=f"{arg1}AGG_OUT", domain=[*cc.arg2, r, t, c, ts]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_ACTL",
            parameter=Parameter(
                m, name=f"{arg1}PAR_ACTL", domain=[*cc.arg2, r, ll, ll, p, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_ACTM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_ACTM", domain=[*cc.arg2, r, ll, ll, p, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_PASTI",
            parameter=Parameter(
                m, name=f"{arg1}PAR_PASTI", domain=[*cc.arg2, r, t, p, item]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_CAPL",
            parameter=Parameter(
                m, name=f"{arg1}PAR_CAPL", domain=[*cc.arg2, r, year, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_CAPM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_CAPM", domain=[*cc.arg2, r, year, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_CAPBD",
            parameter=Parameter(
                m, name=f"{arg1}PAR_CAPBD", domain=[*cc.arg2, r, year, p, bd]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_CUMRET",
            parameter=Parameter(
                m, name=f"{arg1}PAR_CUMRET", domain=[*cc.arg2, r, year, year, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_NCAPL",
            parameter=Parameter(
                m, name=f"{arg1}PAR_NCAPL", domain=[*cc.arg2, r, allyear, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_NCAPM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_NCAPM", domain=[*cc.arg2, r, allyear, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_NCAPR",
            parameter=Parameter(
                m, name=f"{arg1}PAR_NCAPR", domain=[*cc.arg2, r, allyear, p, item]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_OBJSAL",
            parameter=Parameter(
                m, name=f"{arg1}PAR_OBJSAL", domain=[*cc.arg2, r, allyear, p, cur]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_COMPRDL",
            parameter=Parameter(
                m, name=f"{arg1}PAR_COMPRDL", domain=[*cc.arg2, r, allyear, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_COMPRDM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_COMPRDM", domain=[*cc.arg2, r, allyear, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_COMNETL",
            parameter=Parameter(
                m, name=f"{arg1}PAR_COMNETL", domain=[*cc.arg2, r, allyear, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_COMNETM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_COMNETM", domain=[*cc.arg2, r, allyear, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_COMBALEM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_COMBALEM", domain=[*cc.arg2, r, allyear, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_COMBALGM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_COMBALGM", domain=[*cc.arg2, r, allyear, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_IPRIC",
            parameter=Parameter(
                m, name=f"{arg1}PAR_IPRIC", domain=[*cc.arg2, r, allyear, p, c, ts, ie]
            ),
        )

        g.set_parameter(
            name=f"{arg1}PAR_PEAKM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_PEAKM", domain=[*cc.arg2, r, allyear, cg, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_UCSL",
            parameter=Parameter(
                m, name=f"{arg1}PAR_UCSL", domain=[*cc.arg2, ucn, "*", "*", "*"]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_UCSM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_UCSM", domain=[*cc.arg2, ucn, "*", "*", "*"]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_UCMRK",
            parameter=Parameter(
                m, name=f"{arg1}PAR_UCMRK", domain=[*cc.arg2, r, t, item, c, s]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_UCMAX",
            parameter=Parameter(
                m, name=f"{arg1}PAR_UCMAX", domain=[*cc.arg2, ucn, allr, item, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_CUMFLOL",
            parameter=Parameter(
                m, name=f"{arg1}PAR_CUMFLOL", domain=[*cc.arg2, r, p, c, ll, ll]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_CUMFLOM",
            parameter=Parameter(
                m, name=f"{arg1}PAR_CUMFLOM", domain=[*cc.arg2, r, p, c, ll, ll]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_CUMCST",
            parameter=Parameter(
                m, name=f"{arg1}PAR_CUMCST", domain=[*cc.arg2, r, ll, ll, costagg, cur]
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_UCRTP",
            parameter=Parameter(
                m, name=f"{arg1}PAR_UCRTP", domain=[*cc.arg2, ucn, r, t, p, ucgrptype]
            ),
        )
        g.reg_wobj = Parameter(m, name="REG_WOBJ", domain=[reg, item, cur])
        g.set_parameter(
            name=f"{arg1}REG_WOBJ",
            parameter=Parameter(
                m, name=f"{arg1}REG_WOBJ", domain=[*cc.arg2, reg, item, cur]
            ),
        )
        g.set_parameter(
            name=f"{arg1}REG_IREC",
            parameter=Parameter(m, name=f"{arg1}REG_IREC", domain=[*cc.arg2, reg]),
        )
        g.set_parameter(
            name=f"{arg1}REG_ACOST",
            parameter=Parameter(
                m, name=f"{arg1}REG_ACOST", domain=[*cc.arg2, r, allyear, item]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_INVC",
            parameter=Parameter(
                m, name=f"{arg1}CST_INVC", domain=[*cc.arg2, r, allyear, t, p, sysuc]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_INVX",
            parameter=Parameter(
                m, name=f"{arg1}CST_INVX", domain=[*cc.arg2, r, allyear, t, p, sysuc]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_DECC",
            parameter=Parameter(
                m, name=f"{arg1}CST_DECC", domain=[*cc.arg2, r, allyear, t, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_FIXC",
            parameter=Parameter(
                m, name=f"{arg1}CST_FIXC", domain=[*cc.arg2, r, allyear, t, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_FIXX",
            parameter=Parameter(
                m, name=f"{arg1}CST_FIXX", domain=[*cc.arg2, r, allyear, t, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_ACTC",
            parameter=Parameter(
                m, name=f"{arg1}CST_ACTC", domain=[*cc.arg2, r, allyear, t, p, rpm]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_FLOC",
            parameter=Parameter(
                m, name=f"{arg1}CST_FLOC", domain=[*cc.arg2, r, allyear, t, p, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_FLOX",
            parameter=Parameter(
                m, name=f"{arg1}CST_FLOX", domain=[*cc.arg2, r, allyear, t, p, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_IREC",
            parameter=Parameter(
                m, name=f"{arg1}CST_IREC", domain=[*cc.arg2, r, allyear, t, p, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_COMC",
            parameter=Parameter(
                m, name=f"{arg1}CST_COMC", domain=[*cc.arg2, r, allyear, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_COMX",
            parameter=Parameter(
                m, name=f"{arg1}CST_COMX", domain=[*cc.arg2, r, allyear, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_COME",
            parameter=Parameter(
                m, name=f"{arg1}CST_COME", domain=[*cc.arg2, r, allyear, c]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_SALV",
            parameter=Parameter(
                m, name=f"{arg1}CST_SALV", domain=[*cc.arg2, r, allyear, p]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_TIME",
            parameter=Parameter(
                m, name=f"{arg1}CST_TIME", domain=[*cc.arg2, r, allyear, s, sysuc]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CAP_NEW",
            parameter=Parameter(
                m, name=f"{arg1}CAP_NEW", domain=[*cc.arg2, r, allyear, p, t, sysuc]
            ),
        )
        # * Damage cost and custom parameters
        g.set_parameter(
            name=f"{arg1}DAM_OBJ",
            parameter=Parameter(
                m, name=f"{arg1}DAM_OBJ", domain=[*cc.arg2, r, t, c, cur]
            ),
        )
        g.set_parameter(
            name=f"{arg1}CST_DAM",
            parameter=Parameter(
                m,
                name=f"{arg1}CST_DAM",
                domain=[*cc.arg2, reg, t, com],
                description="Damage costs",
            ),
        )
        g.set_parameter(
            name=f"{arg1}PAR_EOUT",
            parameter=Parameter(
                m,
                name=f"{arg1}PAR_EOUT",
                domain=[*cc.arg2, r, allyear, t, p, c],
            ),
        )

        self.tc.enqueue(self.exec4, ctst=self.env.ctst)

        if self.env.sensis.upper() == "YES":
            self.include(SolsetvV3(self.tc, self.env))

        self.tc.enqueue(self.exec5)

        if self.env.solveda == "1":
            return

        self._label_report(cc=cc)

    def _label_report(self, cc: RptliteRptConfig) -> None:
        if self.env.var_uc != "YES":
            declare_par_uc_rpt_params(self.tc)

        # Snapshot V (sol_flo.red:11's SET%4 V VAR) right before the enqueue
        # below, matching sol_flo_red.py's own SolFloRed.compile().
        apply_v_scope(self.env, SOL_FLO_RED_V_SCOPE, self.env.var)

        self.tc.enqueue(
            self.exec_label_report_part1,
            config=cc,
            sow=self.env.sow,
            sysprefix=self.env.sysprefix,
            sensis=self.env.sensis,
            stages=self.env.stages,
            var=self.env.var,
            v=self.env.v,
            pgprim=self.env.pgprim,
            bencost=self.env.bencost,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            etl=self.env.etl,
            capjd=self.env.capjd,
            capwd=self.env.capwd,
            timesed=self.env.timesed,
            obj=self.env.obj,
            varcost=self.env.varcost,
            vnret_defined=self.tc.defined("VNRET"),
            varv=self.env.varv,
            sws=self.env.sws,
            varm=self.env.varm,
            mx=self.env.mx,
            discshift=self.env.discshift,
        )

        # * Calculation of annual costs
        # $ BATINCLUDE cost_ann.rpt '%1' "%3"
        self.include(
            CostAnnRpt(
                self.tc,
                self.env,
                config=CostAnnRptConfig(
                    arg1=next(iter(cc.arg1), ""),
                    arg2=tuple(
                        arg.strip("',") if isinstance(arg, str) else arg
                        for arg in cc.arg3
                    ),
                ),
            )
        )

        self.tc.enqueue(
            self.exec_label_report_part2,
            config=cc,
            sow=self.env.sow,
            sysprefix=self.env.sysprefix,
            sensis=self.env.sensis,
            var_uc=self.env.var_uc,
            stages=self.env.stages,
            obmac=self.env.obmac,
            abs_=self.env.abs,
            var=self.env.var,
            vnret_defined=self.tc.defined("VNRET"),
            sws=self.env.sws,
            vart=self.env.vart,
            cufscal=self.env.cufscal,
            model_name=self.env.model_name,
            eq=self.env.eq,
            rpt_flots=self.env.rpt_flots,
            solans=self.env.solans,
            eqe_ucrtp_defined=self.tc.defined("EQE_UCRTP"),
            eq_g_ucmax_not_defined=not self.tc.defined(f"{self.env.eq}G_UCMAX"),
        )

    def exec_label_report_part1(
        self: RptliteRpt,
        config: RptliteRptConfig,
        sow: str,
        sysprefix: str,
        sensis: str,
        stages: str,
        var: str,
        v: str,
        pgprim: str,
        rtp_ffcs_defined: bool,
        etl: str,
        capjd: str,
        capwd: str,
        timesed: str,
        obj: str,
        varcost: str,
        vnret_defined: bool,
        varv: str,
        sws: str,
        bencost: str,
        varm: str,
        mx: str,
        discshift: float,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rptlite_rpt_part1(
                config=config,
                sow=sow,
                sysprefix=sysprefix,
                sensis=sensis,
                stages=stages,
                var=var,
                v=v,
                pgprim=pgprim,
                rtp_ffcs_defined=rtp_ffcs_defined,
                bencost=bencost,
                etl=etl,
                capjd=capjd,
                capwd=capwd,
                timesed=timesed,
                obj=obj,
                varcost=varcost,
                vnret_defined=vnret_defined,
                varv=varv,
                sws=sws,
                varm=varm,
                mx=mx,
                discshift=discshift,
            ),
        )

    def exec_label_report_part2(
        self: RptliteRpt,
        config: RptliteRptConfig,
        sow: str,
        sysprefix: str,
        sensis: str,
        var_uc: str,
        stages: str,
        obmac: str,
        abs_: str,
        var: str,
        vnret_defined: bool,
        sws: str,
        vart: str,
        cufscal: str,
        model_name: str,
        eq: str,
        rpt_flots: str,
        solans: str,
        eqe_ucrtp_defined: bool,
        eq_g_ucmax_not_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rptlite_rpt_part2(
                config=config,
                sow=sow,
                sysprefix=sysprefix,
                sensis=sensis,
                var_uc=var_uc,
                stages=stages,
                obmac=obmac,
                abs_=abs_,
                var=var,
                vnret_defined=vnret_defined,
                sws=sws,
                vart=vart,
                cufscal=cufscal,
                model_name=model_name,
                eq=eq,
                rpt_flots=rpt_flots,
                solans=solans,
                eqe_ucrtp_defined=eqe_ucrtp_defined,
                eq_g_ucmax_not_defined=eq_g_ucmax_not_defined,
            ),
        )

    def exec1(self: RptliteRpt, rpt_flots: bool) -> None:
        g = self.tc

        rpt_opt, item, j = g.rpt_opt, g.item, g.j

        if rpt_flots:
            rpt_opt["FLO", "1"] = 1

        rpt_opt[item, j].where[rpt_opt[item, j] == 0] = 0
        rpt_opt["FLO", "1"].where[rpt_opt["FLO", "3"]] = 1

    def exec3(self: RptliteRpt) -> None:
        g = self.tc
        project(source=g.Rngmap, target=g.Rnglim)

    def exec4(self: RptliteRpt, ctst: Literal["", "**EPS", "**0", "1"]) -> None:
        """
        Prepare some sets and parameters that can be used for all SOW
        """
        g = self.tc
        number = resolve_ctst(Number(0), ctst)
        # ctst = float(self.env.ctst) if self.env.ctst else 0
        p, v, r, salv_inv, cur, objVflo, c, com, ie, ts, io, t = (
            g.p,
            g.v,
            g.r,
            g.salv_inv,
            g.cur,
            g.ObjVflo,
            g.c,
            g.Com,
            g.ie,
            g.ts,
            g.io,
            g.t,
        )

        salv_inv[g.ObjSums[g.r, g.Pastmile[v], p], v] = Sum(
            g.ObjIcur[r, v, p, g.cur].where[g.obj_pasti[r, v, p, cur]],
            salv_inv[r, v, p, v]
            * (g.ncap_pasti[r, v, p] / g.obj_pasti[r, v, p, cur])
            * (1.0 - number),
        )
        # * Hold on to costs

        objVflo[r, p, c, cur, g.UcCost].where[~g.Rdcur[r, cur]] = False
        sparseExpression = objVflo[r, p, c, cur, "SUB"]
        objVflo[r, p, c, cur, "TAX"].where[sparseExpression] = sparseExpression

        g.Sysinv[g.sysuc].where[g.sysone[g.sysuc]] = g.sysone[g.sysuc]

        # * Hold on to auxliary flows and past investments
        with Loop(g.RpcIre[r, p, com, ie]):
            g.FIoset[g.RtpVintyr[r, v, t, p], c, ts, io].where[
                (
                    g.RpcsVar[r, p, com, ts].where[
                        g.ire_flosum[r, t, p, com, ts, ie, c, io]
                    ]
                )
            ] = g.Rc[r, c]

    def exec5(self: RptliteRpt) -> None:
        self.tc.coef_rtp.setRecords(None)


def rptlite_rpt(
    *,
    config: RptliteRptConfig,
    sow: str,
    sysprefix: str,
    sensis: str,
    var_uc: str,
    stages: str,
    obmac: str,
    abs_: str,
    var: str,
    v: str,
    pgprim: str,
    rtp_ffcs_defined: bool,
    etl: str,
    capjd: str,
    capwd: str,
    timesed: str,
    obj: str,
    varcost: str,
    vnret_defined: bool,
    invlif: str,
    anncost: str,
    varv: str,
    sws: str,
    varm: str,
    obj_combal_defined: bool,
    vart: str,
    micro: str,
    mi_agc_defined: bool,
    cufscal: str,
    model_name: str,
    eq: str,
    rpt_flots: str,
    solans: str,
    bencost: str,
    mx: str,
    discshift: float,
    eqe_ucrtp_defined: bool,
    eq_g_ucmax_not_defined: bool,
) -> str:
    """Legacy GAMS text of the rptlite.rpt REPORT block, cost_ann.rpt included.

    Kept for solve.stc, which embeds the whole block into a GAMS ``LOOP`` it
    builds itself. :class:`RptliteRpt` instead emits part 1, runs the translated
    :class:`~core.cost_ann_rpt.CostAnnRpt` and then emits part 2.

    TODO: drop once solve.stc is translated. Also drops the need for arg3 to
    carry raw GAMS text (e.g. "'1',") for this function, and thus the
    ``.strip("',")`` adapter in :meth:`RptliteRpt._label_report`.
    """
    arg1 = next(iter(config.arg1), "")
    arg3_raw = next(iter(config.arg3), "")
    arg3 = f"{arg3_raw.name}," if isinstance(arg3_raw, (Set | Alias)) else arg3_raw

    return (
        rptlite_rpt_part1(
            config=config,
            sow=sow,
            sysprefix=sysprefix,
            sensis=sensis,
            stages=stages,
            var=var,
            v=v,
            pgprim=pgprim,
            rtp_ffcs_defined=rtp_ffcs_defined,
            etl=etl,
            capjd=capjd,
            capwd=capwd,
            timesed=timesed,
            obj=obj,
            varcost=varcost,
            vnret_defined=vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
            bencost=bencost,
            mx=mx,
            discshift=discshift,
        )
        + cost_ann_rpt(
            arg1=arg1,
            arg2=arg3,
            stages=stages,
            etl=etl,
            invlif=invlif,
            anncost=anncost,
            sysprefix=sysprefix,
            pgprim=pgprim,
            tpulse=tpulse_expression(obj=obj, varcost=varcost),
            is_vnret_defined=vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
            is_obj_combal_defined=obj_combal_defined,
            sow=sow,
            var=var,
            vart=vart,
            micro=micro,
            is_mi_agc_defined=mi_agc_defined,
        )
        + rptlite_rpt_part2(
            config=config,
            sow=sow,
            sysprefix=sysprefix,
            sensis=sensis,
            var_uc=var_uc,
            stages=stages,
            obmac=obmac,
            abs_=abs_,
            var=var,
            vnret_defined=vnret_defined,
            sws=sws,
            vart=vart,
            cufscal=cufscal,
            model_name=model_name,
            eq=eq,
            rpt_flots=rpt_flots,
            solans=solans,
            eqe_ucrtp_defined=eqe_ucrtp_defined,
            eq_g_ucmax_not_defined=eq_g_ucmax_not_defined,
        )
    )


def tpulse_expression(obj: str, varcost: str) -> str:
    """%TPULSE% of rptlite.rpt as passed on to cost_ann.rpt."""
    if varcost.upper() == "LIN":
        return "Y_EOH$OBJ_LINT(R,T,Y_EOH,CUR),OBJ_LINT(R,T,Y_EOH,CUR)*"
    if obj.upper() == "LIN":
        return "TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR)*"
    if obj.upper() == "ALT":
        return "PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR)* OBJ_ALTV(R,T)*"
    return "PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR)*"


def rptlite_rpt_part1(
    *,
    config: RptliteRptConfig,
    sow: str,
    sysprefix: str,
    sensis: str,
    stages: str,
    var: str,
    v: str,
    pgprim: str,
    rtp_ffcs_defined: bool,
    etl: str,
    capjd: str,
    capwd: str,
    timesed: str,
    obj: str,
    varcost: str,
    vnret_defined: bool,
    varv: str,
    sws: str,
    varm: str,
    bencost: str,
    mx: str,
    discshift: float,
) -> str:
    """rptlite.rpt REPORT block up to the annual cost calculation."""
    arg1 = next(iter(config.arg1), "")
    arg3_raw = next(iter(config.arg3), "")
    arg3 = f"{arg3_raw.name}," if isinstance(arg3_raw, (Set | Alias)) else arg3_raw

    return rf"""
*------------------------------------------------------------------------------
* Reports based on SOW-specific values
*------------------------------------------------------------------------------
* Calculation of solution values for (due to reduction) substituted flows
*------------------------------------------------------------------------------
  OPTION CLEAR=PAR_FLO,CLEAR=PAR_FLOM;

{
        sol_flo_red(
            arg1="PAR_FLO",
            arg2="",
            arg3=".L",
            v=v,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )
    }
{
        sol_flo_red(
            arg1="PAR_FLO",
            arg2="M",
            arg3=".M",
            v=v,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )
    }
{sol_ire_rpt(v=v, sow=sow, mx=mx, rtp_ffcs_defined=rtp_ffcs_defined)}

*------------------------------------------------------------------------------
* Objective function
*------------------------------------------------------------------------------
  OPTION CLEAR=COEF_OBJINV;

{
        rpt_obj_rpt(
            arg1=arg1,
            arg2=arg3,
            arg3=sow,
            arg4=sysprefix,
            stages=stages,
            sysprefix=sysprefix,
            etl=etl,
            capjd=capjd,
            capwd=capwd,
            var=var,
            varv=varv,
            varm=varm,
            sws=sws,
            pgprim=pgprim,
            bencost=bencost,
            timesed=timesed,
            obj=obj,
            varcost=varcost,
            discshift=discshift,
            vnret_defined=vnret_defined,
        )
    }

* Calculation of annual costs
"""


def rptlite_rpt_part2(
    *,
    config: RptliteRptConfig,
    sow: str,
    sysprefix: str,
    sensis: str,
    var_uc: str,
    stages: str,
    obmac: str,
    abs_: str,
    var: str,
    vnret_defined: bool,
    sws: str,
    vart: str,
    cufscal: str,
    model_name: str,
    eq: str,
    rpt_flots: str,
    solans: str,
    eqe_ucrtp_defined: bool,
    eq_g_ucmax_not_defined: bool,
) -> str:
    """rptlite.rpt REPORT block from the miscellaneous reportings onwards."""
    sensis_yes = sensis.upper() == "YES"
    var_uc_yes = var_uc == "YES"
    stages_yes = stages == "YES"
    obmac_yes = obmac.upper() == "YES"
    abs_yes = abs_.upper() == "YES"
    arg1 = next(iter(config.arg1), "")
    arg3_raw = next(iter(config.arg3), "")
    arg3 = f"{arg3_raw.name}," if isinstance(arg3_raw, (Set | Alias)) else arg3_raw

    return rf"""
* Miscellaneous reportings
{
        rptmisc_rpt(
            arg1=arg1,
            arg2=arg3,
            arg3=sow,
            arg4=sws,
            arg5=sow,
            var=var,
            cufscal=cufscal,
            sysprefix=sysprefix,
            model_name=model_name,
            vart=vart,
            sws=sws,
            eq=eq,
            if_defined_vnret=vnret_defined,
            rpt_flots=rpt_flots,
            stages=stages,
            if_defined_eqe_ucrtp=eqe_ucrtp_defined,
            var_uc=var_uc,
            if_not_defined_eq_g_ucmax=eq_g_ucmax_not_defined,
            solans=solans,
        )
    }

* Add aggregation levels
{
        rf'''LOOP(NRG_TYPE,Z=RPT_OPT(NRG_TYPE,'1'); IF(Z,PAR_RTCS(RTCS_VARC(R,T,C,S))$NRG_TMAP(R,NRG_TYPE,C)={arg1}AGG_OUT({arg3}R,T,C,S)/G_YRFR(R,S)/Z));'''
        if not sensis_yes
        else ""
    }

{"" if var_uc_yes else par_uc_rpt(arg1="SM", arg2="EQE", arg3=arg1, arg4=arg3)}
{"" if var_uc_yes else par_uc_rpt(arg1="SM", arg2="EQG", arg3=arg1, arg4=arg3)}
{"" if var_uc_yes else par_uc_rpt(arg1="SM", arg2="EQL", arg3=arg1, arg4=arg3)}

{
        r'''REG_WOBJ(R,ITEM,CUR) $= SUM(W$SREG_WOBJ(W,R,ITEM,CUR),SW_PROB(W)*SREG_WOBJ(W,R,ITEM,CUR));'''
        if stages_yes
        else (
            rf'''REG_WOBJ(R,ITEM,CUR) $= {arg1}REG_WOBJ({arg3}R,ITEM,CUR);'''
            if stages.upper() != "YES"
            else ""
        )
    }

{"$ONDOTL" if obmac_yes else ""}

{
        rf'''Z=RPT_OPT('RATE','1'); IF(Z,TRACKPC(BS_BSC)=YES; TRACKPC(BS_STGP(R,P),C)$=BS_RTYPE(R,C));
{arg1}P_OUT({arg3}RTP(R,T,P),C,S)$(PRC_TS(R,P,S)$BS_COMTS(R,C,S)$TRACKPC(R,P,C)$Z)=SUM(RTP_VINTYR(R,V,T,P),VAR_BSFSP(R,V,T,P,C,S)+VAR_BSFNSP(R,V,T,P,C,S))*PRC_CAPACT(R,P)/Z;'''
        if abs_yes
        else ""
    }

OPTION CLEAR=TRACKPC;
"""
