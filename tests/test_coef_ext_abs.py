from types import SimpleNamespace
from typing import cast

from gamspy import Alias, Container, Parameter, Set

from core.coef_ext_abs import ncap_afac_reset_violations
from utils.times_model_class import TimesModelClass


def _ncap_afac_symbols() -> TimesModelClass:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)
    allyear = Set(m, name="ALLYEAR", records=["2010", "2020"])
    prc = Set(m, name="Prc", records=["P1", "P2"])
    p = Alias(m, name="P", alias_with=prc)
    com = Set(m, name="Com", records=["C1", "C2"])
    c = Alias(m, name="C", alias_with=com)

    rtp = Set(m, name="RTP", domain=[r, allyear, p])
    ncap_afac = Parameter(m, name="NCAP_AFAC", domain=[reg, allyear, prc, com])

    return cast(
        TimesModelClass,
        SimpleNamespace(
            container=m, r=r, allyear=allyear, p=p, c=c, Rtp=rtp, ncap_afac=ncap_afac
        ),
    )


def test_ncap_afac_reset_violations_flags_populated_entries() -> None:
    g = _ncap_afac_symbols()
    r = g.r

    # P1/2020/C1: RTP holds and NCAP_AFAC was reset (nonzero) -> violation.
    g.Rtp[r, "2020", "P1"] = True
    g.ncap_afac[r, "2020", "P1", "C1"] = 0.5

    # P1/2020/C2: RTP holds, but NCAP_AFAC has no record for C2 -> no violation.

    # P2/2010/C1: NCAP_AFAC has a record, but P2 was never in RTP -> excluded
    # by the RTP(R,V,P) domain restriction.
    g.ncap_afac[r, "2010", "P2", "C1"] = 1.0

    violations = ncap_afac_reset_violations(g)
    records = violations.records

    assert records is not None
    assert list(zip(records["ALLYEAR"], records["P"], records["C"], strict=False)) == [
        ("2020", "P1", "C1")
    ]


def test_ncap_afac_reset_violations_empty_when_ncap_afac_unset() -> None:
    g = _ncap_afac_symbols()
    g.Rtp[g.r, "2020", "P1"] = True

    violations = ncap_afac_reset_violations(g)
    records = violations.records

    assert records is None or records.empty
