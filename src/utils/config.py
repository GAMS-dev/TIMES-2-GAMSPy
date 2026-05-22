# config.py
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RunConfig(BaseModel):
    # Allow to accept un-validated custom Python classes (DataModules)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_name: str
    milestone_years: list[str]
    env_vars: dict[str, str]
    data_modules: list[Path]

    time_slices: Path
    botime: str = Field(default="1960")
    lp_solver: str = Field(default="CBC")
