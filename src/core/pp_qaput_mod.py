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


def pp_qaput(
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
) -> str:
    condition = not (arg3 == "*")

    return rf"""
IF(NOT {arg1}, {arg1}=1; PUT QLOG @15;
    WHILE(QLOG.CC<67,PUT '*****'); PUT @21,'%SYSTEM.TITLE%':<>43 / @15;
    WHILE(QLOG.CC<67,PUT '*****'); PUT @29,'QUALITY ASSURANCE LOG':<>27;
);
PUT$(NOT {arg2}) QLOG // ' *** {arg4} ';
* hold highest errorlevel for shutdown or not
{f"{arg2}=1+1$(ROUND({arg3})>9); PUT QLOG / ' *00'@(5-{arg2}) MIN(99,{arg3}):{arg2}:0; ERRLEV$({arg3}>ERRLEV)={arg3};" if condition else ""}
"""
