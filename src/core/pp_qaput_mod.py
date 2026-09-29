# pp_qaput_mod.py
# *============================================================================*
# * PP_QAPUT.MOD - puts out an error message
# *   arg1 - main header output flag
# *   arg2 - group header output flag
# *   arg3 - error level (e.g., WARNING, ERROR, FATAL)
# *   arg4 - group description
# * -- group header written on first error for group; ERRLEV holds highest errlevel
# *============================================================================*

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class QALogger:
    """
    Additive, partial Python-side echo of a subset of pp_qaput call sites.

    Only the call sites that already build a violations DataFrame use this;
    the raw-GAMS pp_qaput() code generation remains the source of truth for
    QLOG/ERRLEV for every call site, including these. This logger does not
    reproduce the one-time main "QUALITY ASSURANCE LOG" banner (only the
    per-group header). Remaining call sites are expected to move to this
    path incrementally.
    """

    def __init__(self) -> None:
        self.seen_groups: set[str] = set()
        self.max_err_level = 0

    def log_violations(
        self,
        violations_df: pd.DataFrame | None,
        err_level: int,
        group_desc: str,
        message_template: str,
    ) -> None:
        """
        Logs QA violations if any exist, tracking group headers and max error levels.
        """
        if violations_df is None or violations_df.empty:
            return

        # 1. Print the group header only if it's the first time seeing it
        if group_desc not in self.seen_groups:
            logger.warning(f"\n *** {group_desc} ")
            self.seen_groups.add(group_desc)

        # 2. Update the highest error level (for shutdown checks later)
        self.max_err_level = max(self.max_err_level, err_level)

        # 3. Log every violating record using the provided template
        for _, row in violations_df.iterrows():
            # .to_dict() allows us to use {R} and {P} in the message template
            row_values = {str(key): value for key, value in row.to_dict().items()}
            formatted_msg = message_template.format(**row_values)
            logger.warning(f" *{min(99, err_level):02d} {formatted_msg}")


def pp_qaput(
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
) -> str:
    condition = arg3 != "*"

    return rf"""
IF(NOT {arg1}, {arg1}=1; PUT QLOG @15;
    WHILE(QLOG.CC<67,PUT '*****'); PUT @21,'%SYSTEM.TITLE%':<>43 / @15;
    WHILE(QLOG.CC<67,PUT '*****'); PUT @29,'QUALITY ASSURANCE LOG':<>27;
);
PUT$(NOT {arg2}) QLOG // ' *** {arg4} ';
* hold highest errorlevel for shutdown or not
{f"{arg2}=1+1$(ROUND({arg3})>9); PUT QLOG / ' *00'@(5-{arg2}) MIN(99,{arg3}):{arg2}:0; ERRLEV$({arg3}>ERRLEV)={arg3};" if condition else ""}
"""
