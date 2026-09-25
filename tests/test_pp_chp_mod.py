from types import SimpleNamespace
from typing import cast

from gamspy import Alias, Container, Set

from core.pp_chp_mod import chp_unusual_operation_violations
from utils.times_model_class import TimesModelClass


def test_chp_unusual_operation_violations() -> None:
    m = Container()
    reg = Set(m, name="Reg", records=["REG1"])
    r = Alias(m, name="R", alias_with=reg)

    # Mirror the real model: ALLYEAR is the common base domain, MILESTONYR is
    # loaded directly as data, and MODLYEAR is populated via a GAMS
    # assignment statement (making it an "assigned set" per GAMS terms). RVP
    # is declared over ALLYEAR, not V/MODLYEAR - this is what
    # chp_unusual_operation_violations must respect to avoid GAMS error 187
    # ("Assigned set used as domain").
    allyear = Set(m, name="ALLYEAR", records=["2010", "2020", "2025"])
    milestonyr = Set(m, name="MILESTONYR", domain=[allyear], records=["2020", "2025"])
    t = Alias(m, name="T", alias_with=milestonyr)
    pastyear = Set(m, name="PASTYEAR", domain=[allyear], records=["2010"])
    modlyear = Set(m, name="MODLYEAR", domain=[allyear])
    modlyear[allyear] = milestonyr[allyear] + pastyear[allyear]
    v = Alias(m, name="V", alias_with=modlyear)

    prc = Set(
        m,
        name="Prc",
        records=["P_VIOL_T", "P_VIOL_VINT", "P_NOT_RVP", "P_NEITHER"],
    )
    p = Alias(m, name="P", alias_with=prc)

    rvp = Set(m, name="RVP", domain=[r, allyear, p])
    prc_vint = Set(m, name="PRC_VINT", domain=[reg, prc])

    # P_VIOL_T: in RVP, V is itself a current milestone year (T(V) holds) ->
    # violation regardless of PRC_VINT.
    rvp[r, "2020", "P_VIOL_T"] = True

    # P_VIOL_VINT: in RVP, V is a historical vintage (not in T), but the
    # process is vintaged (PRC_VINT holds) -> violation via the OR branch.
    rvp[r, "2010", "P_VIOL_VINT"] = True
    prc_vint[r, "P_VIOL_VINT"] = True

    # P_NOT_RVP: PRC_VINT holds, but the process was never in RVP -> excluded
    # by the outer RVP(R,V,P) filter. (deliberately absent from RVP)
    prc_vint[r, "P_NOT_RVP"] = True

    # P_NEITHER: in RVP at a historical vintage, but neither T(V) nor
    # PRC_VINT holds -> excluded.
    rvp[r, "2010", "P_NEITHER"] = True

    g = cast(
        TimesModelClass,
        SimpleNamespace(
            container=m, r=r, v=v, p=p, t=t, allyear=allyear, Rvp=rvp, PrcVint=prc_vint
        ),
    )

    violations = chp_unusual_operation_violations(g)
    records = violations.records

    assert records is not None
    assert set(records["P"]) == {"P_VIOL_T", "P_VIOL_VINT"}
