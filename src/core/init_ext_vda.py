# init_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * INIT_EXT.VDA has all the initial preprocessing for VEDA
# *=============================================================================*

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from gamspy import Domain, If, Loop, Ord, Parameter, Set, SpecialValues, Sum
from gamspy.math import Max, Min, Round, abs, mod, project  # noqa: F401

from core.base_class import GamsClass
from core.equcrtp_vda import EqucrtpVda, EqucrtpVdaConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitExtVda(GamsClass):
    """Translation unit for init_ext.vda."""

    # Instance attributes
    module_name: str = "init_ext_vda"
    gams_source: str = "init_ext.vda"

    def __init__(
        self: InitExtVda,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self: InitExtVda) -> None:
        g = self.tc
        m = g.container

        # Internal SETs
        g.RpUx = Set(m, name="RP_UX", domain=[g.r, g.p])
        g.RpPl = Set(m, name="RP_PL", domain=[g.r, g.p, g.lA])
        g.RtpPl = Set(m, name="RTP_PL", domain=[g.r, g.ll, g.p])
        g.RpsUps = Set(m, name="RPS_UPS", domain=[g.r, g.p, g.s])

        g.RpUpc = Set(m, name="RP_UPC", domain=[g.r, g.p, g.tsl, g.lA])
        g.Afups = Set(m, name="AFUPS", domain=[g.r, g.t, g.p, g.s])
        g.RpDp = Set(m, name="RP_DP", domain=[g.r, g.p])
        g.DpLosd = Set(m, name="DP_LOSD", domain=[g.r, g.ll, g.p])
        g.FsEmcb = Set(m, name="FS_EMCB", domain=[g.r, g.p, g.c, g.c])
        g.RpDcgg = Set(m, name="RP_DCGG", domain=[g.r, g.p, g.c, g.cg, g.cg, g.lA])
        g.RpCgc = Set(m, name="RP_CGC", domain=[g.Reg, g.prc, g.cg, g.Com])
        g.RpcIrein = Set(m, name="RPC_IREIN", domain=[g.r, g.p, g.c, g.ie, g.io])

        # Sets for commodity specific availabilities
        g.Rvps = Set(m, name="RVPS", domain=[g.Reg, g.allyear, g.prc, g.ts])
        g.RpsCaflac = Set(m, name="RPS_CAFLAC", domain=[g.r, g.p, g.s, g.bd])
        g.Rvpcsl = Set(m, name="RVPCSL", domain=[g.r, g.year, g.p, g.c, g.s, g.lA])

        # Sets for ACT_EFF processing
        g.RpgAce = Set(m, name="RPG_ACE", domain=[g.r, g.p, g.cg, g.io])
        g.RpgPace = Set(m, name="RPG_PACE", domain=[g.r, g.p, g.cg])
        g.Rpg1ace = Set(m, name="RPG_1ACE", domain=[g.r, g.p, g.cg, g.c])
        g.RpcAce = Set(m, name="RPC_ACE", domain=[g.Reg, g.prc, g.cg])
        g.RvpKmap = Set(m, name="RVP_KMAP", domain=[g.r, g.year, g.p, g.year])
        g.dumimp = Set(
            m,
            name="DUMIMP",
            records=["IMPNRGZ", "IMPMATZ", "IMPDEMZ"],
        )
        g.Nrgelc = Set(
            m, name="NRGELC", description="Electricity", domain=[g.allr, g.c]
        )

        # -----------------------------------------------------------------------------
        # Internal PARAMATERs
        g.miyr_boh = Parameter(m, records=0, name="MIYR_BOH")
        if g.reg_fixt is None:
            g.reg_fixt = Parameter(m, name="REG_FIXT")
        g.rtforc = Parameter(m, name="RTFORC", domain=[g.r, g.ll, g.ll, g.p])
        # For dynamic process bounds
        g.prc_dynuc = Parameter(
            m,
            name="PRC_DYNUC",
            domain=[g.ucn, g.side, g.r, g.allyear, g.p, g.ucgrptype, g.bd],
        )
        # For special handling of non-standard FLO_SHAR
        g.rpcg_ashar = Parameter(
            m, name="RPCG_ASHAR", domain=[g.r, g.p, g.cg, g.cg, g.s]
        )
        g.flo_ashar = Parameter(
            m, name="FLO_ASHAR", domain=[g.Reg, g.allyear, g.prc, g.cg, g.cg, g.s, g.bd]
        )
        # For internal IRE prices processing
        g.par_ipric = Parameter(
            m, name="PAR_IPRIC", domain=[g.r, g.allyear, g.p, g.c, g.ts, g.ie]
        )
        # For partial load efficiencies
        g.dp_psud = Parameter(m, name="DP_PSUD", domain=[g.r, g.ll, g.p, g.upt, g.bd])
        # For storage level UP availability
        g.coef_afups = Parameter(m, name="COEF_AFUPS", domain=[g.r, g.year, g.p, g.s])

        self.tc.enqueue(
            self.basic_years_stuff,
            dflbl=self.env.dflbl,
            waver=(self.env.waver.upper() == "YES"),
        )

        self.tc.enqueue(self.peaking_and_storage_stuff)

        if self.env.obmac != "YES":
            g.var_sift = Parameter(m, name="VAR_SIFT", domain=[g.ll, g.s, g.lA])

        self.add_records_to_universe_item(records=[""])

        self.tc.enqueue(self.clean_up_some_parameters)

        self.tc.enqueue(self.identify_and_initial_preprocessing)

        self.tc.enqueue(
            self.initial_preprocessing_of_com_agg, self.env.shell, self.env.dflbl
        )

        # * Handle Updatable OFF-ranges & REG_BDNCAP process-based bounds
        self.tc.enqueue(self.handle_updatetable_off_ranges, self.env.eotime)

        self.include(EqucrtpVda(self.tc, self.env, EqucrtpVdaConfig(arg1="INIT_EXT")))

        uc_actbet_defined = self.tc.defined("UC_ACTBET")
        if uc_actbet_defined:
            g.register_assignment(g.uc_flobet)
        self.tc.enqueue(
            self.prepare_uc_cli_uc_dynbnd_uc_actbet_cont,
            cli=self.env.cli == "YES",
            uc_actbet_defined=uc_actbet_defined,
            pgprim=self.env.pgprim,
        )

        if self.env.stages == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="$CLEAR GG_KGF",
            )

        if self.tc.defined("PRC_REACT"):
            self.env.set_global("powerflo", "YES")

        if g.gr_ptdf.number_records or g.gg_kgf.number_records:
            self.env.set_global("powerflo", "YES")

        # Load bounds/prices for exogenous trade from previous run if requested
        g.Premile = Set(m, name="PREMILE", domain=[g.allyear])
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="$KILL PAR_IRE PAR_IPRIC",
        )

        if not self.env.is_set("gdx_irebnd"):
            self.label_ifprice()
        else:
            if not os.path.exists(f"{self.env.gdxpath}{self.env.gdx_irebnd}.gdx"):
                self.label_ifprice()
            else:
                self.tc.add_gams_code(
                    module=self,
                    phase="init",
                    code=f"""
$GDXIN {self.env.gdxpath}{self.env.gdx_irebnd}
$LOAD RPC_IREIN=RPC_IREIO PREMILE=MILESTONYR PAR_IRE
""",
                )

                if self.env.gdx_irebnd.upper() == self.env.gdx_ipric.upper():
                    self.label_load2()

                else:
                    self.tc.add_gams_code(module=self, phase="init", code="$GDXIN")
                    self.label_ifprice()
        self.tc.enqueue(self.remove_originally_exogenous_trade_flows)

    def label_ifprice(self: InitExtVda) -> None:
        if not self.env.is_set("gdx_ipric"):
            return
        path = f"{self.env.gdxpath}{self.env.gdx_ipric}.gdx"
        if not Path(path).exists():
            return

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=f"$GDXIN {path}",
        )
        self.label_load2()

    def label_load2(self: InitExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
$LOAD RPC_IREIN=RPC_IREIO PREMILE=MILESTONYR PAR_IPRIC
$GDXIN
""",
        )

    def prepare_uc_cli_uc_dynbnd_uc_actbet_cont(
        self: InitExtVda,
        cli: bool,
        uc_actbet_defined: bool,
        pgprim: str,
    ) -> None:
        g = self.tc
        ucn, side, r, ll, cmvar, tsl = g.ucn, g.side, g.r, g.ll, g.CmVar, g.tsl
        allr, ucgrptype, year, p = g.allr, g.ucgrptype, g.year, g.p

        if cli:
            with Loop(
                Domain(ucn, side, r, ll, cmvar).where[g.uc_cli[ucn, side, r, ll, cmvar]]
            ):
                g.UcAttr[r, ucn, "RHS", "CLI", "YES"] = True

        with Loop(g.UcAttr[r, ucn, side, ucgrptype, g.ucname[tsl]]):
            g.UcTsl[r, ucn, side, tsl] = True

        if uc_actbet_defined:
            g.uc_flobet[ucn, allr, year, p, pgprim].where[
                g.uc_actbet[ucn, allr, year, p]
            ] = g.uc_actbet[ucn, allr, year, p]

            with Loop(Domain(ucn, r, year, p).where[g.uc_actbet[ucn, r, year, p]]):
                g.UcGmapP[r, ucn, "ACT", p] = True

    def basic_years_stuff(self: InitExtVda, dflbl: str, waver: bool) -> None:
        """Basic Years stuff:"""
        g = self.tc
        t, ll = g.t, g.ll

        if g.Datayear.number_records == 0:
            g.Datayear[t] = True
            g.Datayear[ll].where[mod(Max(1999, Min(2051, g.yearval[ll])), 5) == 0] = (
                True
            )

        g.Datayear[g.Pastyear] = True
        g.Datayear[dflbl] = False

        with Loop(t.where[Ord(t) == 1]):
            with If(abs(g.b[t] - g.yearval[t] + 5) > 5):
                g.b[t] = g.yearval[t]
            g.Miyr1[t] = True
            g.miyr_boh[...] = g.b[t] - 1

        g.PyrS[ll].where[g.yearval[ll] == g.miyr_boh[...]] = True

        if waver:
            g.intdefault["PASTI"] = True

    def peaking_and_storage_stuff(self: InitExtVda) -> None:
        g = self.tc
        R, P, c, cg, S, LL, TSL, CUR = g.r, g.p, g.c, g.cg, g.s, g.ll, g.tsl, g.cur
        UnitsAct = g.UnitsAct

        # Peaking and Storage stuff
        g.PrcPkno[R, P].where[
            (
                (g.ncap_pkcnt[R, "0", P, "ANNUAL"] >= 10).where[
                    g.ncap_pkcnt[R, "0", P, "ANNUAL"]
                ]
            )
        ] = True

        g.PrcPkaf[R, P].where[
            (
                (g.ncap_pkcnt[R, "0", P, "ANNUAL"] <= 0).where[
                    g.ncap_pkcnt[R, "0", P, "ANNUAL"]
                ]
            )
        ] = True

        g.PrcStgips[R, P, c].where[
            ~Sum(
                g.PrcActunt[R, P, cg, UnitsAct].where[
                    g.ComGmap[R, cg, c] + cg.sameAs(c)
                ],
                1,
            )
        ] = False

        # Set penalty cost for partial loads and excess storage cycling
        project(target=g.Trackp, source=g.stg_maxcyc)
        g.RpPl[g.Trackp, "UP"] = True

        with Loop(TSL[S[g.Annual]]):
            g.act_cstup[R, LL, P, TSL, CUR] = 0.0
            g.act_cstup[R, LL, P, TSL, CUR].where[g.act_cstpl[R, LL, P, CUR]] = (
                g.act_cstpl[R, LL, P, CUR]
            )
            g.act_cstup[R, LL, P, TSL, CUR].where[
                g.Trackp[R, P] & g.ncap_cost[R, LL, P, CUR]
            ] = g.ncap_cost[R, LL, P, CUR]
            g.act_ups[R, LL, P, S, "FX"].where[g.act_minld[R, LL, P]] = g.act_minld[
                R, LL, P
            ]

        g.Trackp.setRecords(None)
        project(target=g.RpUpr, source=g.act_time)
        project(target=g.RpUpt, source=g.act_cstsd)

    def clean_up_some_parameters(self: InitExtVda) -> None:
        g = self.tc
        year, ll, r, c, p, s, cur = g.year, g.ll, g.r, g.c, g.p, g.s, g.cur
        Com, Datayear = g.Com, g.Datayear

        with Loop(g.Lastll[year]):
            g.Uncd7.setRecords(None)
            g.Uncd7[r, ll.lag(Ord(ll), type="circular"), c, Com, "", "", ""].where[
                (g.vda_emcb[r, ll, c, Com] != 0)
            ] = g.vda_emcb[r, ll, c, Com] != 0

            g.vda_emcb[r, Datayear, c, Com].where[
                ~g.Uncd7[r, year, c, Com, "", "", ""]
            ] = 0

            g.Uncd7.setRecords(None)
            with Loop(g.ie):
                g.Uncd7[
                    r, ll.lag(Ord(ll), type="circular"), p, c, s, g.allr, cur
                ].where[(g.ire_price[r, ll, p, c, s, g.allr, g.ie, cur] != 0)] = (
                    g.ire_price[r, ll, p, c, s, g.allr, g.ie, cur] != 0
                )

            g.ire_price[r, Datayear, p, c, s, g.allr, g.ie, cur].where[
                ~g.Uncd7[r, year, p, c, s, g.allr, cur]
            ] = 0

            g.Uncd7.setRecords(None)
            g.Uncd7[r, ll.lag(Ord(ll), type="circular"), p, cur, "", "", ""].where[
                (g.act_cost[r, ll, p, cur] != 0)
            ] = g.act_cost[r, ll, p, cur] != 0

            g.act_cost[r, Datayear, p, cur].where[
                ~g.Uncd7[r, year, p, cur, "", "", ""]
            ] = 0

            g.Uncd7.setRecords(None)
            g.Uncd7[r, ll.lag(Ord(ll), type="circular"), p, c, s, cur, ""].where[
                (g.flo_deliv[r, ll, p, c, s, cur] != 0)
            ] = g.flo_deliv[r, ll, p, c, s, cur] != 0

            g.flo_deliv[r, Datayear, p, c, s, cur].where[
                ~g.Uncd7[r, year, p, c, s, cur, ""]
            ] = 0

            g.Uncd7.setRecords(None)
            g.Uncd7[r, ll.lag(Ord(ll), type="circular"), p, c, s, cur, ""].where[
                (g.flo_cost[r, ll, p, c, s, cur] != 0)
            ] = g.flo_cost[r, ll, p, c, s, cur] != 0

            g.flo_cost[r, Datayear, p, c, s, cur].where[
                ~g.Uncd7[r, year, p, c, s, cur, ""]
            ] = 0

        g.ncap_ceh[r, ll, p].where[g.vda_ceh[r, ll, p]] = g.vda_ceh[r, ll, p]

    def identify_and_initial_preprocessing(self: InitExtVda) -> None:
        g = self.tc
        r, p, c, s, ll, cg, ie = g.r, g.p, g.c, g.s, g.ll, g.cg, g.ie
        io, year = g.io, g.year
        Datayear, Com = g.Datayear, g.Com

        # -----------------------------------------------------------------------------
        #  Identify PRC_RESID processes and initialize NCAP_PASTI
        g.prc_resid[r, ll.lag(Ord(ll), type="circular"), p].where[
            (g.prc_resid[r, ll, p] > 0).where[g.prc_resid[r, ll, p]]
        ] = g.prc_resid[r, "0", p] + SpecialValues.EPS
        g.ncap_pasti[r, g.PyrS, p].where[g.prc_resid[r, "0", p]] = 1
        # -----------------------------------------------------------------------------

        # Initial Preprocessing of VDA_EMCB, FLO_EMIS and IRE_FLOSUM
        g.flo_emis[r, ll, p, cg, c, s].where[g.flo_eff[r, ll, p, cg, c, s]] = g.flo_eff[
            r, ll, p, cg, c, s
        ]
        g.Rxx.setRecords(None)
        g.flo_eff.setRecords(None)
        g.vda_emcb[r, year, c, Com].where[g.ComTmap[r, "ENV", c]] = 0

        with Loop(Domain(r, Datayear, c, Com).where[g.vda_emcb[r, Datayear, c, Com]]):
            g.Rxx[r, c, Com] = True

        g.Rxx[r, c, Com].where[~g.ComTmap[r, "ENV", Com]] = False

        with Loop(Domain(g.Top[r, p, c, "IN"], g.Rxx[r, c, Com])):
            g.FsEmcb[r, p, Com, c] = True

        g.FsEmcb[r, p, Com, c].where[g.Top[r, p, Com, "IN"]] = False
        project(target=g.Trackpc, source=g.FsEmcb, direction="left")
        g.Top[g.Trackpc, "OUT"] = True
        g.Rxx.setRecords(None)
        g.Trackpc.setRecords(None)

        with Loop(
            Domain(r, Datayear, p, cg, c, s).where[g.flo_emis[r, Datayear, p, cg, c, s]]
        ):
            g.RpcEmis[r, p, c] = True

        g.RpgRed[g.RpcEmis[r, p, c], "OUT"].where[~g.Top[r, p, c, "IN"]] = True

        with Loop(
            Domain(r, Datayear, p, c, s, ie, Com, io).where[
                (
                    g.PrcMap[r, "IRE", p].where[
                        g.ire_flosum[r, Datayear, p, c, s, ie, Com, io]
                    ]
                )
            ]
        ):
            g.RpgRed[r, p, Com, io] = True

    def initial_preprocessing_of_com_agg(
        self: InitExtVda, shell: str, dflbl: str
    ) -> None:
        """Initial Preprocessing of COM_AGG and VDA_FLOP"""
        g = self.tc
        r, ll, c, p, s, cg = g.r, g.ll, g.c, g.p, g.s, g.cg

        g.com_agg[r, ll, c, c].where[g.com_agg[r, ll, c, c]] = 0

        rhs = g.act_flo[r, ll, p, cg, s]
        g.vda_flop[r, ll, p, cg, s].where[rhs] = rhs

        g.KeepFlof[r, p, c].where[g.vda_flop[r, dflbl, p, c, "ANNUAL"]] = True

        if shell.upper() == "ANSWER":
            g.KeepFlof[r, p, c].where[g.prc_actflo[r, dflbl, p, c]] = True

        project(target=g.RpXred, source=g.act_flo)
        g.act_flo.setRecords(None)

    def handle_updatetable_off_ranges(self: InitExtVda, eotime: int) -> None:
        """Handle Updatable OFF-ranges & REG_BDNCAP process-based bounds"""

        g = self.tc
        r, p, ll, lll, Rvp = g.r, g.p, g.lA, g.ll, g.Rvp  # noqa: F841

        g.ncap_start[r, p].where[(g.ncap_start[r, p] <= g.miyr_boh)] = 0
        Rvp[r, lll, p].where[g.ncap_bnd[r, lll, p, "N"]] = g.ncap_bnd[r, lll, p, "N"]

        if Rvp.number_records:
            g.ncap_bnd[Rvp, "N"].where[(g.ncap_bnd[Rvp, "N"] > eotime)] = eotime
            g.ncap_start[r, p].where[
                (abs(g.ncap_bnd[r, "0", p, "N"]) > 999).where[Rvp[r, "0", p]]
            ] = abs(g.ncap_bnd[r, "0", p, "N"]) + 1
            g.PrcNoff[r, p, lll, g.eohyear].where[Rvp[r, lll, p]] = False
            g.PrcNoff[
                r,
                p,
                g.bohyear[lll],
                (Ord(lll) + (g.ncap_bnd[r, lll, p, "N"] - g.yearval[lll])),
            ].where[Rvp[r, lll, p]] = True

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  NCAP_BND(RVP(R,LL,P),L('N')) = MOD(MIN(2,ROUND(MAX(NCAP_BND(RVP,L),-1))),2)$LASTLL(LL)+(YEARVAL(LL)-1)$(ROUND(MOD(NCAP_BND(RVP,L)-YEARVAL(LL),MAX(1,YEARVAL(LL))))=-1);
""",
        )
        # TODO: waiting for GAMSPy fix
        # g.ncap_bnd[Rvp[r, lll, p], ll["N"]] = (
        #     mod(Min(2, Round(Max(g.ncap_bnd[Rvp, ll], -1))), 2).where[g.Lastll[lll]]
        #     + (g.yearval[lll] - 1).where[
        #         (
        #             Round(
        #                 mod(g.ncap_bnd[Rvp, ll] - g.yearval[lll], Max(1, g.yearval[lll]))
        #             )
        #             == -1
        #         )
        #     ]
        # )

        Rvp.setRecords(None)

    def remove_originally_exogenous_trade_flows(self: InitExtVda) -> None:
        g = self.tc
        r, t, p, c, s, ll, ie, ts = g.r, g.t, g.p, g.c, g.s, g.ll, g.ie, g.ts

        g.par_ire[r, ll, t, p, c, s, ie].where[g.RpcIrein[r, p, c, ie, "OUT"]] = 0
        g.par_ipric[r, t, p, c, ts, ie].where[g.RpcIrein[r, p, c, ie, "OUT"]] = 0
        g.RpcIrein[r, p, c, ie, "OUT"] = False
