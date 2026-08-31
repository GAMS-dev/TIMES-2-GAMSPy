# mod_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * MOD_EXT.EXT Extension equations
# * Called from MAINDRV.MOD
# *============================================================================*

from __future__ import annotations

import logging

from gamspy import Equation

from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def mod_ext_vda(
    tc: TimesModelClass,
    eq: str,
    obmac: str,
    duc: str,
    solmip: str,
    powerflo: str,
    ecb: str,
    def_uc_flobet: bool,
    def_com_cstbal: bool,
    def_gr_vargen: bool,
    def_rtc_ms: bool,
    def_gg_mm: bool,
) -> list[Equation]:
    """Translation unit for mod_ext.vda."""
    eq = eq.lower()
    equations = [
        tc.get_equation(f"{eq}e_acteff"),
        tc.get_equation(f"{eq}l_caflac"),
        tc.get_equation(f"{eq}e_caflac"),
        tc.get_equation(f"{eq}l_capflo"),
        tc.get_equation(f"{eq}_capload"),
        tc.get_equation(f"{eq}_actramp"),
        tc.get_equation(f"{eq}e_actups"),
        tc.get_equation(f"{eq}l_actups"),
        tc.get_equation(f"{eq}l_actupc"),
        tc.get_equation(f"{eq}_actpl"),
        tc.get_equation(f"{eq}_actrmpc"),
        tc.get_equation(f"{eq}_slsift"),
        tc.eql_stgccl,
        tc.get_equation(f"{eq}e_ucrtp"),
        tc.get_equation(f"{eq}n_ucrtp"),
        tc.get_equation(f"{eq}n_ucrtc"),
        tc.get_equation(f"{eq}e_ashar"),
        tc.get_equation(f"{eq}l_ashar"),
        tc.get_equation(f"{eq}g_ashar"),
    ]

    if obmac == "YES":
        equations.extend(
            [
                tc.eq_sdlogic,
                tc.eq_sudupt,
                tc.eq_sdslant,
                tc.eq_sdminon,
                tc.eq_sudload,
                tc.eq_sudtime,
                tc.eq_sudpll,
            ]
        )

    if f"{duc}{solmip}".upper() == "YESYES":
        equations.extend([tc.eq_sdind_1, tc.eq_sdind_0])

    if def_uc_flobet:
        equations.extend(
            [tc.get_equation(f"{eq}g_ucmax"), tc.get_equation(f"{eq}g_ucsumax")]
        )

    if def_com_cstbal:
        equations.append(tc.eq_objbal)

    if powerflo.upper() == "YES":
        equations.extend(
            [
                tc.get_equation(f"{eq}_gr_powflo"),
                tc.get_equation(f"{eq}_gr_ptdflo"),
                tc.get_equation(f"{eq}_gr_genall"),
                tc.get_equation(f"{eq}_gr_demall"),
                tc.get_equation(f"{eq}_gr_xbnd"),
                tc.get_equation(f"{eq}_gr_virtcap"),
                tc.get_equation(f"{eq}_gr_virtbnd"),
            ]
        )

    if def_gr_vargen:
        equations.extend(
            [
                tc.get_equation(f"{eq}_rl_load"),
                tc.get_equation(f"{eq}_rl_ndis"),
                tc.get_equation(f"{eq}_rl_stcap"),
                tc.get_equation(f"{eq}_rl_pkcap"),
                tc.get_equation(f"{eq}_rl_thmin"),
            ]
        )

    if def_rtc_ms and ecb == "YES":
        equations.extend(
            [tc.get_equation(f"{eq}_msncap"), tc.get_equation(f"{eq}_msncapb")]
        )

    if def_gg_mm:
        equations.extend(
            [
                tc.eq_gg_mflo,
                tc.eq_gg_gama,
                tc.eq_gg_hlip,
                tc.eq_gg_hlev,
                tc.eq_gg_step,
                tc.eq_gg_prio,
                tc.eq_gg_mbnd,
                tc.eq_gg_pdif1,
                tc.eq_gg_pdif2,
                tc.eq_gg_weymst,
                tc.eq_gg_weymtx,
            ]
        )

    return equations
