# solsetv_v3.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * SOLSETV.VDA
# *
# * Output routine - creating flat Sets for VEDA
# *
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, Ord, Parameter, Product, Set, SpecialValues, Sum, sparse
from gamspy.math import abs, project

from core.base_class import GamsClass
from core.solsysd_v3 import SolsysdV3

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolsetvV3(GamsClass):
    """Translation unit for solsetv.v3."""

    module_name: str = "solsetv_v3"
    gams_source: str = "solsetv.v3"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if self.arg1 != "":
            if self.arg1 == "ADESCVDD":
                self._label_adescvdd()
                self._label_rest()
                return
            if self.arg1 == "REST":
                self._label_rest()
                return
            if self.arg1 == "FINISHUP":
                self._label_finishup()
                return
            raise ValueError(f"Unknown label for solsetv.v3: {self.arg1}")

        # Scenario index defaulting to 1
        if self.env.stages != "YES":
            self.tc.enqueue(self.exec1)

        # Make sure CLI attributes are defined
        if self.env.cli == "YES":
            self._label_adescvdd()
            self._label_rest()
            return
        g = self.tc
        m = g.container

        if self.env.solveda == "1":
            g.cm_sresult = Parameter(
                m, name="CM_SRESULT", domain=[g.allsow, g.item, g.item, g.allyear]
            )
            g.cm_smaxc_m = Parameter(
                m, name="CM_SMAXC_M", domain=[g.allsow, g.item, g.allyear]
            )

        self._label_adescvdd()
        self._label_rest()

    def _label_adescvdd(self) -> None:
        g = self.tc
        m = g.container
        g.adesc = Set(
            m,
            name="ADESC",
            description="Attribute Descriptions",
            records=[
                # * variables (and their marginals)
                ("VAR_act", "Process Activity"),
                ("VAR_actM", "Process Activity - Marginals"),
                ("VAR_cap", "Technology Capacity"),
                ("VAR_capM", "Technology Capacity - Marginals"),
                ("VAR_ncap", "Technology Investment - New capacity"),
                ("VAR_ncapM", "Technology Investment - Marginals"),
                ("VAR_ncapR", "Technology Investment - BenCost + ObjRange"),
                ("VAR_fin", "Commodity Consumption by Process"),
                ("VAR_fout", "Commodity Production by Process"),
                ("VAR_Pout", "Commodity Output Level by Process"),
                ("VAR_comprd", "Commodity Total Production"),
                ("VAR_comprdM", "Commodity Total Production - Marginal"),
                ("VAR_comnet", "Commodity Net"),
                ("VAR_comnetM", "Commodity Net - Marginal"),
                ("VAR_eout", "Electricity supply by technology and energy source"),
                ("VAR_CumCst", "Cumulative costs by type (if constrained)"),
                # * equations (and their marginals)
                ("EQ_combal", "Commodity Slack/Levels"),
                ("EQ_combalM", "Commodity Slack/Levels - Marginals"),
                ("EQ_peak", "Peaking Constraint Slack"),
                ("EQ_peakM", "Peaking Constraint Slack - Marginals"),
                ("EQ_Cumflo", "Cumulative flow constraint - Levels"),
                ("EQ_CumfloM", "Cumulative flow constraint - Marginals"),
                ("EQ_IreM", "Inter-regional trade equations - Marginals"),
                # * calculated parameters
                ("PAR_capLO", "Capacity Lower Limit"),
                ("PAR_capUP", "Capacity Upper Limit"),
                (
                    "PAR_CapRet",
                    "Cumulative Retirements of Technology Capacity by Vintage",
                ),
                (
                    "PAR_Top",
                    "Process topology (Opted out - SET RPT_TOP YES to activate)",
                ),
                (
                    "Cap_New",
                    "Newly installed capacity and lumpsum investment by vintage and commissioning period",
                ),
                # * calculated costs
                ("COST_inv", "Annual investment costs"),
                ("COST_dec", "Annual decommissioning costs"),
                ("COST_salv", "Salvage values of capacities at EOH+1"),
                ("COST_late", "Annual late costs"),
                ("COST_fom", "Annual fixed operating and maintenance costs"),
                ("COST_act", "Annual activity costs"),
                ("COST_flo", "Annual flow costs (including import/export prices)"),
                ("COST_com", "Annual commodity costs"),
                ("COST_els", "Annual elastic demand cost term"),
                ("COST_dam", "Annual damage cost term"),
                ("COST_invx", "Annual investment taxes/subsidies"),
                ("COST_fixx", "Annual fixed taxes/subsidies"),
                ("COST_flox", "Annual flow taxes/subsidies"),
                ("COST_comx", "Annual commodity taxes/subsidies"),
                ("COST_ire", "Annual implied costs of endogenous trade"),
                ("COST_NPV", "Total discounted costs by process/commodity (optional)"),
                ("Time_NPV", "Discounted value of time by period"),
                ("VAL_Flo", "Annual commodity flow values"),
                ("ObjZ", "Total discounted system cost"),
                ("Reg_wobj", "Regional total expected discounted system cost"),
                ("Reg_obj", "Regional total discounted system cost"),
                ("Reg_irec", "Regional total discounted implied trade cost"),
                ("Reg_ACost", "Regional total annualized costs by period"),
                ("User_Con", "Level of user constraint"),
                (
                    "User_ConFXM",
                    "Marginal cost of user constraint (or group-wise market share)",
                ),
                ("User_ConLOM", "Marginal cost of lower bound user constraint"),
                ("User_ConUPM", "Marginal cost of upper bound user constraint"),
                ("User_DynbM", "Marginal cost of dynamic process bound constraint"),
                # * Climate module and MACRO
                ("User_Maxbet", "Level of MaxBet constraint"),
                ("VAR_climate", "Climate result variables"),
                ("Dual_Clic", "Shadow price of climate constraint"),
                ("VAR_Macro", "MACRO result variables"),
            ],
        )

    def _label_rest(self) -> None:
        if "IRE" in self.tc.container.listSymbols():
            raise ValueError(
                "Illegal Declaration of Internal TIMES Identifier: IRE - Run Aborted"
            )
        g = self.tc
        m = g.container
        r, p, c, Reg, Com, allr, allts = g.r, g.p, g.c, g.Reg, g.Com, g.allr, g.allts
        ire = g.ire = Set(
            m, name="IRE", description="Inter-regional Exchange (Exports & Imports)"
        )
        g.Irelx = Set(
            m, name="IRELX", domain=[ire], description="Electricity Exchange Processes"
        )
        g.Irenx = Set(
            m, name="IRENX", domain=[ire], description="Enodogenous Trade Exchange"
        )
        g.Stg = Set(
            m, name="STG", domain=[ire], description="Storage Processes (genuine)"
        )
        g.Sts = Set(
            m, name="STS", domain=[ire], description="General Multilevel Storage"
        )
        g.Rcap = Set(
            m, name="RCAP", domain=[ire], description="Processes with Retirements"
        )
        g.Nst = Set(m, name="NST", domain=[ire], description="Night Storage")
        g.Dmd = Set(m, name="DMD", domain=[r, p], description="Demand Devices")
        g.Pre = Set(m, name="PRE", domain=[r, p], description="Energy Processes")
        g.Prw = Set(
            m, name="PRW", domain=[r, p], description="Material Processes - Weight"
        )
        g.Prv = Set(
            m, name="PRV", domain=[r, p], description="Material Processes - Volume"
        )
        g.Ref = Set(m, name="REF", domain=[r, g.prc], description="Refineries")
        g.Ele = Set(m, name="ELE", domain=[r, p], description="Electric Power Plants")
        g.Chp = Set(
            m, name="CHP", domain=[r, p], description="Coupled Heat+Power Plants"
        )
        g.Hpl = Set(m, name="HPL", domain=[r, p], description="Heating Plants")
        g.Distr = Set(
            m, name="DISTR", domain=[r, p], description="Distribution Technologies"
        )
        g.Renew = Set(
            m, name="RENEW", domain=[r, p], description="Renewables Processes"
        )
        g.Xtract = Set(
            m, name="XTRACT", domain=[r, p], description="Extraction Processes"
        )

        self.tc.enqueue(self.exec2)

        g.Res = Set(
            m, name="RES", domain=[r, Com], description="Residential Sector Demands"
        )
        g.Comm = Set(
            m, name="COMM", domain=[r, Com], description="Commercial Sector Demands"
        )
        g.Trn = Set(
            m, name="TRN", domain=[r, Com], description="Transporation Sector Demands"
        )
        g.Agr = Set(
            m, name="AGR", domain=[Reg, Com], description="Agriculature Sector Demands"
        )
        g.Othd = Set(m, name="OTHD", domain=[r, Com], description="Other Demands")
        g.Ind = Set(m, name="IND", domain=[Reg, Com], description="Industrial Demands")
        g.Nrgfos = Set(m, name="NRGFOS", domain=[r, c], description="Fossil")
        g.Nrgren = Set(m, name="NRGREN", domain=[r, c], description="Renewable")
        g.Nrgsyn = Set(m, name="NRGSYN", domain=[r, c], description="Synthetic")
        g.Nrgelc = Set(m, name="NRGELC", domain=[allr, c], description="Electricity")
        g.Nrghet = Set(m, name="NRGHET", domain=[allr, c], description="Heat")

        self.tc.enqueue(self.exec3)

        # * timeslices
        g.Rs = Set(m, name="RS", domain=[r, allts])

        self.tc.enqueue(self.exec4)

        # * UCs and completion of missing labels
        g.nonset = Set(m, name="NONSET", records=["NONE"])
        g.pluset = Set(m, name="PLUSET", records=["+"])
        g.Othcom = Set(m, name="OTHCOM", domain=[g.item])
        g.RegAct = Set(m, name="REG_ACT", domain=[g.item, c])
        g.UcConst = Set(
            m,
            name="UC_CONST",
            domain=["*", g.ucn],
            description="Genuine TIMES UC constraints",
        )
        g.UcMarks = Set(
            m,
            name="UC_MARKS",
            domain=[r, g.item],
            description="PRC_MARK Share UC constraints",
        )
        g.UcDynbd = Set(
            m,
            name="UC_DYNBD",
            domain=[r, g.ucn],
            description="Dynamic UC bound constraints",
        )
        self.tc.enqueue(
            self.exec5,
            pgprim=self.env.pgprim,
        )

        if self.env.punits.upper() == "YES":
            g.PrcUnits = Set(m, name="PRC_UNITS", domain=[r, p, g.ucgrptype, g.units])

            self.tc.enqueue(self.exec6)

    def _label_finishup(self) -> None:
        self.tc.enqueue(self.exec7)
        self.include(
            SolsysdV3(
                self.tc,
                self.env,
                mode="SYMBOL",
                base_name="REG_ACOST",
                index_block="SOW,R",
                extra_index=",T,",
                suffix="",
                symbol_prefixes=["S", "R"],
                map=False,
            )
        )
        self.include(
            SolsysdV3(
                self.tc,
                self.env,
                mode="SYMBOL",
                base_name="REG_WOBJ",
                index_block="SOW,R",
                extra_index=",",
                suffix=",CUR",
                symbol_prefixes=["S", "R"],
                map=False,
            )
        )
        self.tc.enqueue(self.exec8)

        g = self.tc
        m = g.container

        if self.env.rpt_top.upper() == "YES":
            g.adesc = Set(
                m, name="ADESC", records=[("PAR_Top", "Process topology indicator")]
            )
            self.tc.enqueue(self.exec9)

        self.tc.enqueue(self.exec10)

    def exec1(self: SolsetvV3) -> None:
        self.tc.Sow["1"] = True

    def exec2(self: SolsetvV3) -> None:
        g = self.tc
        r, p = g.r, g.p
        # * set the regional memebers of the reporting sets
        g.Dmd[g.Rp[r, p]] = sparse(g.PrcMap[r, "DMD", p])
        g.Pre[g.Rp[r, p]] = sparse(g.PrcMap[r, "PRE", p])
        g.Prw[g.Rp[r, p]] = sparse(g.PrcMap[r, "PRW", p])
        g.Prv[g.Rp[r, p]] = sparse(g.PrcMap[r, "PRV", p])
        g.Ref[g.Rp[r, p]] = sparse(g.PrcMap[r, "REF", p])
        g.Ele[g.Rp[r, p]] = sparse(g.PrcMap[r, "ELE", p])
        g.Chp[g.Rp[r, p]] = sparse(g.PrcMap[r, "CHP", p])
        g.Hpl[g.Rp[r, p]] = sparse(g.PrcMap[r, "HPL", p])
        g.Distr[g.Rp[r, p]] = sparse(g.PrcMap[r, "DISTR", p])
        g.Renew[g.Rp[r, p]] = sparse(g.PrcMap[r, "RENEW", p])
        g.Xtract[g.Rp[r, p]] = sparse(g.PrcMap[r, "XTRACT", p])

    def exec3(self: SolsetvV3) -> None:
        g = self.tc
        r, c, p = g.r, g.c, g.p
        # * set the regional memebers of the reporting sets
        g.Res[g.Rc[r, c]] = sparse(g.DemSmap[r, "RES", c])
        g.Comm[g.Rc[r, c]] = sparse(g.DemSmap[r, "COM", c])
        g.Trn[g.Rc[r, c]] = sparse(g.DemSmap[r, "TRN", c])
        g.Agr[g.Rc[r, c]] = sparse(g.DemSmap[r, "AGR", c])
        g.Ind[g.Rc[r, c]] = sparse(g.DemSmap[r, "IND", c])
        g.Othd[g.Rc[r, c]] = sparse(g.DemSmap[r, "OTH", c])
        g.Ne[g.Rc[r, c]] = sparse(g.DemSmap[r, "NE", c])
        g.Nrgelc[g.Nrg[r, c]] = sparse(g.NrgTmap[r, "ELC", c])
        g.Nrghet[g.Nrg[r, c]] = sparse(g.NrgTmap[r, "LTHEAT", c])
        g.Nrghet[g.Nrg[r, c]] = sparse(g.NrgTmap[r, "HTHEAT", c])
        g.Nrgfos[g.Nrg[r, c]] = sparse(g.NrgTmap[r, "FOSSIL", c])
        g.Nrgren[g.Nrg[r, c]] = sparse(g.NrgTmap[r, "RENEN", c])
        g.Nrgren[g.Nrg[r, c]] = sparse(g.NrgTmap[r, "FRERENEW", c])
        g.Nrgren[g.Nrg[r, c]] = sparse(g.NrgTmap[r, "LIMRENEW", c])
        g.Nrgsyn[g.Nrg[r, c]] = sparse(g.NrgTmap[r, "SYNTH", c])
        # *GG* set the REGional descriptions if not provided
        # * Use the RC / RP masks
        g.ComDesc[g.Rc[r, c]].where[~(g.ComDesc[r, c])] = g.comgrp[c]
        g.PrcDesc[g.Rp[r, p]].where[~(g.PrcDesc[r, p])] = g.prc[p]

    def exec4(self: SolsetvV3) -> None:
        project(source=self.tc.rs_tslvl, target=self.tc.Rs)

    def exec5(self: SolsetvV3, pgprim: str) -> None:
        g = self.tc
        r, c = g.r, g.c
        with Loop(r):
            g.UcConst["NONE", g.ucn].where[g.UcRSum[r, g.ucn]] = True
        with Loop(g.Rmkc[r, g.item, c].where[g.rpt_opt["COMPRD", "4"]]):
            g.UcMarks[r, g.item] = True
        g.RegAct[g.allr, pgprim] = g.allreg[g.allr]
        g.RegAct[g.nonset, pgprim] = True
        g.Othcom[g.cg] = sparse(Sum(g.ComPeak[r, g.cg], 1))
        g.Othcom[g.cur] = sparse(Sum(g.Rdcur[r, g.cur], 1))

    def exec6(self: SolsetvV3) -> None:
        # * Add default capacity unit and conversion if missing
        g = self.tc
        g.g_unca[g.UnitsAct, g.UnitsAct].where[
            ~(Sum(g.units.where[(g.g_unca[g.units, g.UnitsAct] == 1)], 1))
        ] = 1.0
        g.PrcUnits[g.Rp, "ACT", g.UnitsAct].where[
            Sum(g.PrcActunt[g.Rp, g.cg, g.UnitsAct], 1)
        ] = True
        with Loop(g.UnitsAct):
            g.PrcUnits[g.PrcCap[g.Rp], "CAP", g.units].where[
                (
                    (
                        abs(g.g_unca[g.units, g.UnitsAct] - g.prc_capact[g.Rp])
                        < g.prc_capact[g.Rp] / 1280.0
                    ).where[
                        g.g_unca[g.units, g.UnitsAct]
                        & g.PrcUnits[g.Rp, "ACT", g.UnitsAct]
                    ]
                )
            ] = True
        g.Trackp[g.PrcCap[g.Rp]].where[
            Product(
                g.PrcUnits[g.Rp, "CAP", g.units],
                Sum(g.PrcCapunt[g.Rp, g.cg, g.UnitsCap], 1).where[  # type: ignore[arg-type]
                    g.PrcUnits[g.Rp, "ACT", g.units]
                ],
            )
        ] = True
        g.PrcUnits[g.Trackp[g.Rp], "CAP", g.units] = Sum(
            g.PrcCapunt[g.Rp, g.cg, g.UnitsCap[g.units]], 1
        )
        g.Trackp.setRecords(None)

    def exec7(self: SolsetvV3) -> None:
        # * Finally, do some cleanup and set optional TOP indicators
        g = self.tc
        r, p, c, ie = g.r, g.p, g.c, g.ie
        g.RpUx.setRecords(None)
        project(source=g.prc_dynuc, target=g.UcDynbd)
        g.RpSgs[r, p] = sparse(g.PrcMap[r, "NST", p])
        g.IreDist[g.RpIre[r, p]] = sparse(Sum(g.RpcIreio[r, p, c, ie, "IN"], 1))
        g.RpUx[g.RpIre[r, p]] = sparse(Sum(g.RpcIre[r, p, c, ie], g.Nrgelc[r, c]))

    def exec8(self: SolsetvV3) -> None:
        g = self.tc
        g.Afs.setRecords(None)
        g.par_objsal.setRecords(None)
        g.Rtpc.setRecords(None)
        g.Rttc.setRecords(None)
        g.coef_vnt.setRecords(None)
        g.RvpKmap.setRecords(None)
        g.RtpVntbyr.setRecords(None)
        g.par_top.setRecords(None)

    def exec9(self: SolsetvV3) -> None:
        self.tc.rpt_opt["FLO", "7"] = 1.0

    def exec10(self: SolsetvV3) -> None:
        g = self.tc
        r, t, p, c, io = g.r, g.t, g.p, g.c, g.io

        # IF(RPT_OPT('FLO','7'), -> is rpt_opt of 'FLO' and '7' != 0
        if g.rpt_opt["FLO", "7"].toDense():
            g.par_top[r, t[g.Miyr1], p, c, io].where[g.Top[r, p, c, io]] = (
                SpecialValues.EPS
            )
            g.par_top[r, t[g.Miyr1], p, c, "OUT"].where[g.RpcIre[r, p, c, "IMP"]] = (
                SpecialValues.EPS
            )
            g.par_top[r, t[g.Miyr1], p, c, "IN"].where[g.RpcIre[r, p, c, "EXP"]] = (
                SpecialValues.EPS
            )
            g.par_top[r, t - (Ord(t) - 1), p, c, io].where[
                g.ncap_com[r, t, p, c, io]
            ] = SpecialValues.EPS
