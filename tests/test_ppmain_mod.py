from types import SimpleNamespace
from typing import cast

from gamspy import Alias, Container, Parameter, Set

from core.ppmain_mod import (
    cap_bnd_lo_up_violations,
    cap_bnd_violations,
    com_fr_normalization_violations,
    diverging_trade_topology_violations,
    flow_off_ts_violations,
    mi_dmas_topology_violations,
    ncap_pasti_violations,
    ncap_tlife_violations,
    tslvl_reset_violations_df,
)
from utils.times_model_class import TimesModelClass


def test_tslvl_reset_violations_df_none_when_nothing_reset() -> None:
    assert tslvl_reset_violations_df(0.0, 0.0) is None


def test_tslvl_reset_violations_df_reports_counts_when_reset() -> None:
    violations_df = tslvl_reset_violations_df(3.0, 2.0)

    assert violations_df is not None
    assert violations_df.to_dict("records") == [{"F": 3, "Z": 2}]


def _cap_bnd_symbols() -> TimesModelClass:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    allyear = Set(m, name="ALLYEAR", records=["2020"])
    t = Alias(m, name="T", alias_with=allyear)
    prc = Set(
        m,
        name="Prc",
        records=[
            "PROC_VIOL",
            "PROC_OK",
            "PROC_RCAP",
            "PROC_ZERO_RESID",
            "PROC_ZERO_CAPBND",
            "PROC_EQUAL",
            "PROC_OVERRIDE",
        ],
    )
    p = Alias(m, name="P", alias_with=prc)

    rtp = Set(m, name="RTP", domain=[r, t, p])
    rtp[r, t, p] = True  # every (REG1,2020,*) tuple is a valid RTP entry

    lim = Set(m, name="LIM", records=["LO", "FX", "UP", "N"])
    bnd_type = Set(m, name="BND_TYPE", domain=[lim], records=["LO", "FX", "UP"])
    lA = Alias(m, name="L", alias_with=lim)

    cap_bnd = Parameter(m, name="CAP_BND", domain=[reg, allyear, prc, bnd_type])
    rcap_bnd = Parameter(m, name="RCAP_BND", domain=[reg, allyear, prc, lim])
    prc_resid = Parameter(m, name="PRC_RESID", domain=[reg, allyear, prc])
    prc_rcap = Set(m, name="PRC_RCAP", domain=[reg, prc])
    rp_flo = Set(m, name="RP_FLO", domain=[r, p])
    f = Parameter(m, name="F", records=0)
    z = Parameter(m, name="Z", records=0)
    ifq = Parameter(m, name="IFQ", records=1)

    return cast(
        TimesModelClass,
        SimpleNamespace(
            container=m,
            r=r,
            t=t,
            p=p,
            lA=lA,
            Rtp=rtp,
            PrcRcap=prc_rcap,
            RpFlo=rp_flo,
            f=f,
            z=z,
            ifq=ifq,
            cap_bnd=cap_bnd,
            rcap_bnd=rcap_bnd,
            prc_resid=prc_resid,
        ),
    )


def test_cap_bnd_violations() -> None:
    g = _cap_bnd_symbols()
    r, t = g.r, g.t

    # F < Z, not early-retirement-capable -> a genuine violation.
    g.cap_bnd[r, t, "PROC_VIOL", "UP"] = 100
    g.prc_resid[r, t, "PROC_VIOL"] = 150

    # F > Z -> the bound is not tighter than the residual, no violation.
    g.cap_bnd[r, t, "PROC_OK", "UP"] = 200
    g.prc_resid[r, t, "PROC_OK"] = 150

    # F < Z, but PRC_RCAP holds -> GAMS sets Z=0 in this branch, so the
    # IF(Z,...) truthy test fails and no violation is raised.
    g.cap_bnd[r, t, "PROC_RCAP", "UP"] = 50
    g.prc_resid[r, t, "PROC_RCAP"] = 150
    g.PrcRcap[r, "PROC_RCAP"] = True

    # PRC_RESID is 0 -> IF(Z,...) is false regardless of the bound.
    g.cap_bnd[r, t, "PROC_ZERO_RESID", "UP"] = 10
    g.prc_resid[r, t, "PROC_ZERO_RESID"] = 0

    # CAP_BND(RTP,'UP') is 0 -> excluded by the outer $CAP_BND(RTP,L) filter.
    g.cap_bnd[r, t, "PROC_ZERO_CAPBND", "UP"] = 0
    g.prc_resid[r, t, "PROC_ZERO_CAPBND"] = 150

    # F == Z exactly -> not strictly less -> no violation.
    g.cap_bnd[r, t, "PROC_EQUAL", "UP"] = 150
    g.prc_resid[r, t, "PROC_EQUAL"] = 150

    # F == -IFQ (with IFQ=1, RP_FLO unset) -> the GAMS 0**(IFQ+F+...)
    # override fires, forcing F to Z, which makes F<Z false even though a
    # naive check of the original F=-1 < Z=150 would look like a violation.
    g.cap_bnd[r, t, "PROC_OVERRIDE", "UP"] = -1
    g.prc_resid[r, t, "PROC_OVERRIDE"] = 150

    violations = cap_bnd_violations(g)
    records = violations.records

    assert records is not None
    assert set(records["P"]) == {"PROC_VIOL"}


def test_cap_bnd_lo_up_violations() -> None:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    allyear = Set(m, name="ALLYEAR", records=["2020"])
    t = Alias(m, name="T", alias_with=allyear)
    prc = Set(
        m,
        name="Prc",
        records=["PROC_VIOL", "PROC_OK", "PROC_NOT_VARP", "PROC_ZERO_UP"],
    )
    p = Alias(m, name="P", alias_with=prc)

    rtp = Set(m, name="RTP", domain=[r, t, p])
    rtp[r, t, p] = True

    rtp_varp = Set(m, name="RTP_VARP", domain=[r, t, p])
    rtp_varp[r, t, "PROC_VIOL"] = True
    rtp_varp[r, t, "PROC_OK"] = True
    rtp_varp[r, t, "PROC_ZERO_UP"] = True
    # PROC_NOT_VARP deliberately not in RTP_VARP

    bd = Set(m, name="BD", records=["LO", "FX", "UP"])
    cap_bnd = Parameter(m, name="CAP_BND", domain=[reg, allyear, prc, bd])

    cap_bnd[r, t, "PROC_VIOL", "LO"] = 100
    cap_bnd[r, t, "PROC_VIOL", "UP"] = 50  # LO > UP, UP nonzero -> violation

    cap_bnd[r, t, "PROC_OK", "LO"] = 50
    cap_bnd[r, t, "PROC_OK", "UP"] = 100  # LO < UP -> no violation

    cap_bnd[r, t, "PROC_NOT_VARP", "LO"] = 100
    cap_bnd[r, t, "PROC_NOT_VARP", "UP"] = 50  # LO>UP but not RTP_VARP -> excluded

    cap_bnd[r, t, "PROC_ZERO_UP", "LO"] = 100
    cap_bnd[r, t, "PROC_ZERO_UP", "UP"] = 0  # UP is zero -> excluded

    g = cast(
        TimesModelClass,
        SimpleNamespace(
            container=m, r=r, t=t, p=p, Rtp=rtp, RtpVarp=rtp_varp, cap_bnd=cap_bnd
        ),
    )

    violations = cap_bnd_lo_up_violations(g)
    records = violations.records

    assert records is not None
    assert set(records["P"]) == {"PROC_VIOL"}


def test_mi_dmas_topology_violations() -> None:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    com_base = Set(m, name="COM", records=["CG1", "CG2", "M1", "M2"])
    c = Alias(m, name="C", alias_with=com_base)

    dem = Set(m, name="DEM", domain=[r, c])
    mi_dmas = Set(m, name="MI_DMAS", domain=[r, c, com_base])

    # CG1 is a demand commodity group with two members flagged in MI_DMAS ->
    # both should show up, one row per member.
    dem[r, "CG1"] = True
    mi_dmas[r, "CG1", "M1"] = True
    mi_dmas[r, "CG1", "M2"] = True

    # CG2 also has an MI_DMAS entry, but is NOT a demand commodity -> excluded.
    mi_dmas[r, "CG2", "M1"] = True

    g = cast(
        TimesModelClass,
        SimpleNamespace(container=m, r=r, c=c, Com=com_base, Dem=dem, MiDmas=mi_dmas),
    )

    violations = mi_dmas_topology_violations(g)
    records = violations.records

    assert records is not None
    assert set(zip(records["C"], records["COM"], strict=True)) == {
        ("CG1", "M1"),
        ("CG1", "M2"),
    }


def test_ncap_tlife_violations() -> None:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    allyear = Set(m, name="ALLYEAR", records=["2020"])
    t = Alias(m, name="T", alias_with=allyear)
    prc = Set(
        m,
        name="Prc",
        records=["P_TOO_SHORT", "P_TOO_LONG", "P_OK", "P_ZERO", "P_NOT_RTP"],
    )
    p = Alias(m, name="P", alias_with=prc)

    rtp = Set(m, name="RTP", domain=[r, t, p])
    rtp[r, t, "P_TOO_SHORT"] = True
    rtp[r, t, "P_TOO_LONG"] = True
    rtp[r, t, "P_OK"] = True
    rtp[r, t, "P_ZERO"] = True
    # P_NOT_RTP deliberately excluded from RTP

    ncap_tlife = Parameter(m, name="NCAP_TLIFE", domain=[reg, allyear, prc])
    # NCAP_TLIFE is nominally integer, and the GAMS check's "-.999" is an
    # epsilon-guard against float noise on integer values, not a general
    # fractional threshold - a non-integer value near 1 (e.g. 0.5) rounds
    # back into the valid AGE range and wouldn't be flagged, so use values
    # unambiguously outside [1,200] to exercise the "too short"/"too long"
    # branches.
    ncap_tlife[r, t, "P_TOO_SHORT"] = -5  # < 1 -> too short
    ncap_tlife[r, t, "P_TOO_LONG"] = 250  # > 200 -> too long
    ncap_tlife[r, t, "P_OK"] = 25  # within [1,200] -> no violation
    ncap_tlife[r, t, "P_ZERO"] = 0  # falsy -> excluded regardless of value
    ncap_tlife[r, t, "P_NOT_RTP"] = 0.1  # would be "too short" but not in RTP

    age = Set(m, name="AGE", records=[str(i) for i in range(1, 201)])
    life = Alias(m, name="LIFE", alias_with=age)
    rxx = Set(m, name="RXX", domain=[reg, "*", "*"])
    putgrp = Parameter(m, name="PUTGRP", records=0)

    g = cast(
        TimesModelClass,
        SimpleNamespace(
            container=m,
            r=r,
            t=t,
            p=p,
            age=age,
            Rtp=rtp,
            Rxx=rxx,
            ncap_tlife=ncap_tlife,
            life=life,
            putgrp=putgrp,
        ),
    )

    too_short, too_long = ncap_tlife_violations(g)

    too_short_records = too_short.records
    too_long_records = too_long.records
    assert too_short_records is not None
    assert too_long_records is not None
    assert set(too_short_records["P"]) == {"P_TOO_SHORT"}
    assert set(too_long_records["P"]) == {"P_TOO_LONG"}


def test_flow_off_ts_violations() -> None:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    prc = Set(m, name="Prc", records=["P1", "P2"])
    p = Alias(m, name="P", alias_with=prc)
    com = Set(m, name="Com", records=["C1"])
    c = Alias(m, name="C", alias_with=com)
    allts = Set(m, name="ALL_TS", records=["ANNUAL", "WINTER", "SUMMER"])
    ts = Alias(m, name="TS", alias_with=allts)
    s = Alias(m, name="S", alias_with=allts)
    bohyear = Set(m, name="BOHYEAR", records=["2020"])
    eohyear = Set(m, name="EOHYEAR", records=["2030"])

    prc_foff = Set(m, name="PRC_FOFF", domain=[reg, prc, com, allts, bohyear, eohyear])
    rpc = Set(m, name="RPC", domain=[r, p, c])
    rpcs_var = Set(m, name="RPCS_VAR", domain=[r, p, c, allts])
    rs_below = Set(m, name="RS_BELOW", domain=[reg, allts, allts])

    # P1: flow OFF at ANNUAL, but a VAR_FLO exists at WINTER, which is
    # strictly below ANNUAL -> the OFF is ignored -> violation.
    rpc[r, "P1", c] = True
    prc_foff[r, "P1", c, "ANNUAL", "2020", "2030"] = True
    rpcs_var[r, "P1", c, "WINTER"] = True
    rs_below[r, "WINTER", "ANNUAL"] = True

    # P2: same PRC_FOFF entry, but its VAR_FLO timeslice (SUMMER) has no
    # RS_BELOW relation to ANNUAL registered -> no violation.
    rpc[r, "P2", c] = True
    prc_foff[r, "P2", c, "ANNUAL", "2020", "2030"] = True
    rpcs_var[r, "P2", c, "SUMMER"] = True

    g = cast(
        TimesModelClass,
        SimpleNamespace(
            container=m,
            r=r,
            p=p,
            c=c,
            ts=ts,
            s=s,
            bohyear=bohyear,
            eohyear=eohyear,
            PrcFoff=prc_foff,
            Rpc=rpc,
            RpcsVar=rpcs_var,
            RsBelow=rs_below,
        ),
    )

    violations = flow_off_ts_violations(g)
    records = violations.records

    assert records is not None
    assert set(records["P"]) == {"P1"}


def test_diverging_trade_topology_violations() -> None:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    prc = Set(m, name="Prc", records=["P_VIOL", "P_OK", "P_NOT_DIST", "P_HAS_TOP_IRE"])
    p = Alias(m, name="P", alias_with=prc)
    com = Set(m, name="Com", records=["C1", "M1", "M2"])
    c = Alias(m, name="C", alias_with=com)
    impexp = Set(m, name="IMPEXP", records=["IMP", "EXP"])
    ie = Alias(m, name="IE", alias_with=impexp)

    rpc_market = Set(m, name="RPC_MARKET", domain=[r, p, c, ie])
    top_ire = Set(m, name="TOP_IRE", domain=[r, com, r, com, p])
    rpc_ire = Set(m, name="RPC_IRE", domain=[r, p, com, ie])
    ire_dist = Set(m, name="IRE_DIST", domain=[r, p])
    cg_grp = Set(m, name="CG_GRP", domain=[r, p, c, com])
    z = Parameter(m, name="Z", records=0)

    # P_VIOL: no internal TOP_IRE link, IRE_DIST holds, two import
    # candidates (M1, M2) -> "too complex" violation.
    rpc_market[r, "P_VIOL", "C1", "EXP"] = True
    ire_dist[r, "P_VIOL"] = True
    rpc_ire[r, "P_VIOL", "M1", "IMP"] = True
    rpc_ire[r, "P_VIOL", "M2", "IMP"] = True

    # P_OK: same setup but only ONE import candidate -> not "too complex".
    rpc_market[r, "P_OK", "C1", "EXP"] = True
    ire_dist[r, "P_OK"] = True
    rpc_ire[r, "P_OK", "M1", "IMP"] = True

    # P_NOT_DIST: two import candidates, but IRE_DIST doesn't hold -> excluded.
    rpc_market[r, "P_NOT_DIST", "C1", "EXP"] = True
    rpc_ire[r, "P_NOT_DIST", "M1", "IMP"] = True
    rpc_ire[r, "P_NOT_DIST", "M2", "IMP"] = True

    # P_HAS_TOP_IRE: two import candidates, IRE_DIST holds, but an internal
    # TOP_IRE link already exists -> excluded by the outer filter.
    rpc_market[r, "P_HAS_TOP_IRE", "C1", "EXP"] = True
    ire_dist[r, "P_HAS_TOP_IRE"] = True
    rpc_ire[r, "P_HAS_TOP_IRE", "M1", "IMP"] = True
    rpc_ire[r, "P_HAS_TOP_IRE", "M2", "IMP"] = True
    top_ire[r, "C1", r, "M1", "P_HAS_TOP_IRE"] = True

    g = cast(
        TimesModelClass,
        SimpleNamespace(
            container=m,
            r=r,
            p=p,
            c=c,
            ie=ie,
            Com=com,
            RpcMarket=rpc_market,
            TopIre=top_ire,
            RpcIre=rpc_ire,
            IreDist=ire_dist,
            CgGrp=cg_grp,
            z=z,
        ),
    )

    violations = diverging_trade_topology_violations(g)
    records = violations.records

    assert records is not None
    assert set(records["P"]) == {"P_VIOL"}


def test_ncap_pasti_violations() -> None:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    prc = Set(
        m,
        name="Prc",
        records=["P_VIOL", "P_NOT_TRACKED", "P_NO_PASTI", "P_ZERO_YMAX"],
    )
    p = Alias(m, name="P", alias_with=prc)
    allyear = Set(m, name="ALLYEAR", records=["2020"])
    pyr = Alias(m, name="PYR", alias_with=allyear)

    trackp = Set(m, name="TRACKP", domain=[r, p])
    ncap_pasti = Parameter(m, name="NCAP_PASTI", domain=[reg, allyear, prc])
    prc_ymax = Parameter(m, name="PRC_YMAX", domain=[reg, prc])

    # P_VIOL: tracked, has a PASTI entry, and PRC_YMAX still positive (i.e.
    # the delay wasn't cleared by an earlier pass) -> violation.
    trackp[r, "P_VIOL"] = True
    ncap_pasti[r, "2020", "P_VIOL"] = 5
    prc_ymax[r, "P_VIOL"] = 10

    # P_NOT_TRACKED: same PASTI/PRC_YMAX setup, but never tracked -> excluded.
    ncap_pasti[r, "2020", "P_NOT_TRACKED"] = 5
    prc_ymax[r, "P_NOT_TRACKED"] = 10

    # P_NO_PASTI: tracked and PRC_YMAX positive, but no NCAP_PASTI entry for
    # any PYR -> the SUM is zero -> excluded.
    trackp[r, "P_NO_PASTI"] = True
    prc_ymax[r, "P_NO_PASTI"] = 10

    # P_ZERO_YMAX: tracked, has a PASTI entry, but PRC_YMAX is zero -> excluded.
    trackp[r, "P_ZERO_YMAX"] = True
    ncap_pasti[r, "2020", "P_ZERO_YMAX"] = 5

    g = cast(
        TimesModelClass,
        SimpleNamespace(
            container=m,
            r=r,
            p=p,
            pyr=pyr,
            Trackp=trackp,
            ncap_pasti=ncap_pasti,
            prc_ymax=prc_ymax,
        ),
    )

    violations = ncap_pasti_violations(g)
    records = violations.records

    assert records is not None
    assert set(records["P"]) == {"P_VIOL"}


def test_com_fr_normalization_violations() -> None:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    allyear = Set(m, name="ALLYEAR", records=["T1", "T2"])
    t = Alias(m, name="T", alias_with=allyear)
    com = Set(m, name="Com", records=["C_VIOL", "C_OK", "C_NOT_TRACKED", "C_EPS"])
    c = Alias(m, name="C", alias_with=com)

    trackc = Set(m, name="TRACKC", domain=[r, c])
    rtc = Set(m, name="RTC", domain=[r, t, c])
    com_fr = Parameter(m, name="COM_FR", domain=[reg, allyear, com, "*"])

    # C_VIOL: tracked, two years off from unity -> only the FIRST offending
    # year should be flagged; Z gates the second one off.
    trackc[r, "C_VIOL"] = True
    rtc[r, "T1", "C_VIOL"] = True
    rtc[r, "T2", "C_VIOL"] = True
    com_fr[r, "T1", "C_VIOL", "ANNUAL"] = 1.2
    com_fr[r, "T2", "C_VIOL", "ANNUAL"] = 1.3

    # C_OK: tracked, sums to unity exactly -> no violation.
    trackc[r, "C_OK"] = True
    rtc[r, "T1", "C_OK"] = True
    com_fr[r, "T1", "C_OK", "ANNUAL"] = 1.0

    # C_NOT_TRACKED: off from unity, but TRACKC not set -> excluded by the
    # outer LOOP(TRACKC(R,C)) gate.
    rtc[r, "T1", "C_NOT_TRACKED"] = True
    com_fr[r, "T1", "C_NOT_TRACKED", "ANNUAL"] = 1.2

    # C_EPS: tracked and nominally "NE 1" due to float noise, but within the
    # 1E-5 tolerance -> the outer filter matches but IF(ABS(...)>1E-5) doesn't.
    trackc[r, "C_EPS"] = True
    rtc[r, "T1", "C_EPS"] = True
    com_fr[r, "T1", "C_EPS", "ANNUAL"] = 1.0 + 1e-7

    g = cast(
        TimesModelClass,
        SimpleNamespace(
            container=m,
            r=r,
            t=t,
            c=c,
            Trackc=trackc,
            Rtc=rtc,
            com_fr=com_fr,
            z=Parameter(m, name="Z", records=0),
        ),
    )

    violations = com_fr_normalization_violations(g)
    records = violations.records

    assert records is not None
    assert set(zip(records["T"], records["C"], strict=True)) == {("T1", "C_VIOL")}
