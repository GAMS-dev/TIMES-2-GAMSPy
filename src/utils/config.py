# config.py
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserConfig(BaseModel):
    validate_: Literal["NO", "%validate%"] = Field(
        default="%validate%", alias="validate"
    )
    reduce: Literal["YES", "%reduce%"] = "%reduce%"
    vda: Literal["YES", "%vda%"] = "%vda%"
    debug: Literal["YES", "NO"] = "NO"
    dumpsol: Literal["YES", "NO"] = "NO"
    solans: Literal["YES", "NO"] = "NO"
    err_abort: Literal["YES", "NO"] = "YES"
    gams_cgi: Literal["NO", "WWW"] = "NO"
    solve_now: Literal["YES", "NO"] = "YES"
    model_name: str = "TIMES"
    xtqa: Literal["YES", "%xtqa%"] = "%xtqa%"
    var_uc: Literal["YES", "%var_uc%"] = "%var_uc%"
    obj: Literal["ALT", "MOD", "LIN", "STD", "AUTO"] = "AUTO"
    mid_year: Literal["YES", "%mid_year%"] = "%mid_year%"
    oblong: Literal["YES", "NO", "%oblong%"] = "%oblong%"
    damage: Literal["LP", "NLP", "NO"] = "LP"
    stages: Literal["YES", "NO", "%stages%"] = "%stages%"
    solveda: Literal["YES", "%solveda%"] = "%solveda%"
    varcost: Literal["LIN", "%varcost%"] = "%varcost%"
    dscauto: Literal["YES", "%dscauto%"] = "%dscauto%"
    datagdx: Literal["YES", "%datagdx%"] = "%datagdx%"
    botime: int = 1980
    eotime: int = 2200
    vedavdd: Literal["YES", "%vedavdd%"] = "%vedavdd%"
    timesed: Literal["YES", "NO", "%timesed%"] = "%timesed%"
    anncost: Literal["LEV", "%anncost%"] = "%anncost%"
    macro: Literal["YES", "MLF", "MSA", "CSA", "%macro%"] = "%macro%"
    cli: Literal["YES", "%cli%"] = "%cli%"
    fixboh: int | Literal["%fixboh%"] = "%fixboh%"
    lpoint: str = "%lpoint%"


class RunConfig(BaseModel):
    # Allow to accept un-validated custom Python classes (DataModules)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_name: str = "TEST"
    milestone_years: list[str]
    env_vars: UserConfig
    data_modules: list[Path]

    time_slices: Path
    lp_solver: str = Field(default="CBC")
