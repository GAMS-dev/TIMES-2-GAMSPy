from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class TimesConfig:
    # TODO: check capitalization of options
    """Holds default config data."""

    run_name: str = "default"
    botime: int = 1850
    eotime: int = 2200

    # Flags
    reduce: bool = True
    dsc_auto: bool = True
    cli: bool = False
    vda: bool = True
    dsc: bool = True
    stages: bool = False
    macro: str = "N"
    etl: bool = False
    abs: bool = False
    ier: bool = False
    pgprim: str = "ACT"
    debug: bool = False
    dumpsol: bool = False
    solve_now: bool = True
    xtqa: bool = True
    var_uc: bool = True
    obj: str = "MOD"
    solveda: bool = True
    datagdx: bool = True
    vedavdd: bool = True
    MAXSOW = None  # non user
    DFLBL = 0  # non user

    # Derived low-level flags from setglobs.gms:
    setglobals: Dict[str, Any] = field(default_factory=dict)
