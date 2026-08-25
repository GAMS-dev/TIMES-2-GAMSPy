# bnd_act_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_ACT.MOD set the actual bounds for non-vintage VAR_ACTs
# =============================================================================*
# GaG Questions/Comments:
#   - FX take precedence as is set last!!!
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def bnd_act_mod(
    *,
    var: str,
    swd: str,
    swt: str,
    r_t: str,
) -> str:
    return rf"""
* reset any existing bounds
  {var}_ACT.LO(R,V,T,P,S{swd}) = 0;
  {var}_ACT.UP(R,V,T,P,S{swd}) = INF;

  {var}_ACT.LO(RTP_VINTYR(R,T,T,P),S{swd})$({swt} PRC_TS(R,P,S) * (NOT PRC_VINT(R,P))) $= ACT_BND(R,T,P,S,'LO');
  {var}_ACT.UP(RTP_VINTYR(R,T,T,P),S{swd})$({swt} PRC_TS(R,P,S) * (NOT PRC_VINT(R,P))) $= ACT_BND(R,T,P,S,'UP');
  {var}_ACT.FX(RTP_VINTYR({r_t},T,P),S{swd})$({swt}PRC_TS(R,P,S)* (NOT PRC_VINT(R,P))) $= ACT_BND(R,T,P,S,'FX');
* for upper bounds of zero, activity variables of all vintages can be bounded to zero
  {var}_ACT.UP(RTP_VINTYR(R,V,T,P),S{swd})$({swt} PRC_TS(R,P,S) * PRC_VINT(R,P)$RTPS_OFF(R,T,P,S)) = EPS;
"""
