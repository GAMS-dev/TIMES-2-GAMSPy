from types import SimpleNamespace
from typing import cast

from gamspy import Alias, Container, Set

from core.pp_qack_mod import empty_group_violations, rpc_in_top_violations
from utils.times_model_class import TimesModelClass


def _rpc_in_top_symbols() -> TimesModelClass:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    prc = Set(m, name="Prc", records=["P1", "P2", "P3"])
    p = Alias(m, name="P", alias_with=prc)
    com = Set(m, name="Com", records=["C1"])
    c = Alias(m, name="C", alias_with=com)
    inout = Set(m, name="INOUT", records=["IN", "OUT"])
    io = Alias(m, name="IO", alias_with=inout)

    top = Set(m, name="TOP", domain=[r, p, c, io])
    rpc = Set(m, name="RPC", domain=[r, p, c])
    trackp = Set(m, name="TRACKP", domain=[r, p])
    trackpc = Set(m, name="TRACKPC", domain=[r, p, c])

    return cast(
        TimesModelClass,
        SimpleNamespace(
            container=m,
            r=r,
            p=p,
            c=c,
            io=io,
            Top=top,
            Rpc=rpc,
            Trackp=trackp,
            Trackpc=trackpc,
        ),
    )


def test_rpc_in_top_violations_flags_untracked_commodity() -> None:
    g = _rpc_in_top_symbols()
    r, c = g.r, g.c

    # P1: tracked process, C1 in RPC, appears in TOP, but never made it into
    # TRACKPC (no ACTFLO/FLO_SHAR/FLO_FUNC/FLO_SUM claimed it) -> violation.
    g.Trackp[r, "P1"] = True
    g.Rpc[r, "P1", c] = True
    g.Top[r, "P1", c, "IN"] = True

    # P2: same setup, but TRACKPC is set -> no violation.
    g.Trackp[r, "P2"] = True
    g.Rpc[r, "P2", c] = True
    g.Top[r, "P2", c, "IN"] = True
    g.Trackpc[r, "P2", c] = True

    # P3: appears in TOP/RPC but was never tracked at all (TRACKP not set) ->
    # excluded by the domain restriction itself, not just the $condition.
    g.Rpc[r, "P3", c] = True
    g.Top[r, "P3", c, "IN"] = True

    violations = rpc_in_top_violations(g)
    records = violations.records

    assert records is not None
    assert set(records["P"]) == {"P1"}


def _empty_group_symbols() -> TimesModelClass:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    prc = Set(m, name="Prc", records=["P1", "P2", "P3"])
    p = Alias(m, name="P", alias_with=prc)
    comgrp = Set(m, name="COMGRP", records=["CG1"])
    cg = Alias(m, name="CG", alias_with=comgrp)
    com = Set(m, name="Com", records=["C1", "C2"])
    c = Alias(m, name="C", alias_with=com)

    rp_grp = Set(m, name="RP_GRP", domain=[r, p, cg])
    rp = Set(m, name="RP", domain=[r, p])
    rpc = Set(m, name="RPC", domain=[r, p, c])
    com_gmap = Set(m, name="COM_GMAP", domain=[r, cg, c])

    return cast(
        TimesModelClass,
        SimpleNamespace(
            container=m,
            r=r,
            p=p,
            c=c,
            cg=cg,
            RpGrp=rp_grp,
            Rp=rp,
            Rpc=rpc,
            ComGmap=com_gmap,
        ),
    )


def test_empty_group_violations_flags_group_with_no_members() -> None:
    g = _empty_group_symbols()
    r, cg = g.r, g.cg

    # P1: pre-flagged empty by the caller's RP_PG/RPC_PG check (RP_GRP set),
    # and RPC+COM_GMAP together don't map any commodity into the group
    # either -> genuinely empty -> violation.
    g.RpGrp[r, "P1", cg] = True
    g.Rp[r, "P1"] = True
    g.Rpc[r, "P1", "C1"] = True

    # P2: also pre-flagged in RP_GRP, but RPC+COM_GMAP do map a commodity
    # (C2) into the group -> not empty via the fallback check -> no
    # violation.
    g.RpGrp[r, "P2", cg] = True
    g.Rp[r, "P2"] = True
    g.Rpc[r, "P2", "C2"] = True
    g.ComGmap[r, cg, "C2"] = True

    # P3: pre-flagged in RP_GRP, but the process isn't in RP at all ->
    # excluded by the RP(R,P) guard.
    g.RpGrp[r, "P3", cg] = True

    violations = empty_group_violations(g)
    records = violations.records

    assert records is not None
    assert set(records["P"]) == {"P1"}
