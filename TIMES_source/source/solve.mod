*++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
* Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
* This file is part of the IEA-ETSAP TIMES model generator, licensed
* under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
*=============================================================================*
* SOLVE.MOD solver and solve controls
*=============================================================================*
*GaG Questions/Comments:
*-----------------------------------------------------------------------------
*$ONLISTING
* Release some memory
$  BATINCLUDE pp_clean.mod
*  get the optimizer directive file
%MODEL_NAME%.OPTFILE = OPTFILEID;
%MODEL_NAME%.PRIOROPT=(OPTFILEID=2);
* set the model solver status
%MODEL_NAME%.MODELSTAT = 0;
%MODEL_NAME%.TOLPROJ= 1e-8;

* MACRO: Loading solution from GDX file replaced by activating the SPOINT utility

$  IF '%SOLVE_NOW%'==NO  $GOTO NO_SOLVE
* solve TIMES with appropriate METHOD
$  IF NOT SET MIXLP $SETLOCAL MIXLP ''
$  IF NOT SET NONLP $SETLOCAL NONLP ''
$  IF NOT SET DUMP_SAVEPOINT $SETLOCAL DUMP_SAVEPOINT NO
* LP/MIP solver for the real solve, selectable via --LPSOLVER=<name>
$  IF NOT SET LPSOLVER $SETLOCAL LPSOLVER default
* NLP solver for the real solve, selectable via --NLPSOLVER=<name>
$  IF NOT SET NLPSOLVER $SETLOCAL NLPSOLVER default
* if ETL or DSC with binary variables use MIP
$  IF    '%DAMAGE%'==NLP    $SETLOCAL NONLP NL
$  IF    '%MICRO%'==YES     $SETLOCAL NONLP NL
$  IF    '%MACRO%'==YES     $SETLOCAL NONLP NL
$  IF    '%ETL%' == YES     $SETLOCAL MIXLP MI
$  IF    '%SOLMIP%'==YES    $SETLOCAL MIXLP MI
$  SETLOCAL METHOD '%MIXLP%%NONLP%P'
$  IF     %METHOD% == P     $SETLOCAL METHOD LP
$  IFI NOT '%MACRO%'==YES   $GOTO NOT_MACRO
$onEcho > %gams.optDir%%system.dirSep%convert.opt
DumpGDX %CONVERT_GDX%
$offEcho

%MODEL_NAME%.optfile = 1;
option lp=convert, nlp=convert;
SOLVE %MODEL_NAME% MAXIMIZING VAR_UTIL USING %METHOD%;

option lp=%LPSOLVER%, nlp=%NLPSOLVER%;
SOLVE %MODEL_NAME% MAXIMIZING VAR_UTIL USING %METHOD%;
$GOTO CHECK
$LABEL NOT_MACRO
* solve TIMES as an LP/MIP

$onEcho > %gams.optDir%%system.dirSep%convert.opt
DumpGDX %CONVERT_GDX%
!dict %MODEL_NAME%_dict.txt
$offEcho

%MODEL_NAME%.optfile = 1;
*%MODEL_NAME%.dictfile = 1;
option lp=convert, mip=convert;
SOLVE %MODEL_NAME% MINIMIZING objZ USING %METHOD%;

option lp=%LPSOLVER%, mip=%LPSOLVER%;
$ifThenI.solvemode %SOLVEMODE%==SOLVE
$  ifThenI.dumpsp %DUMP_SAVEPOINT%==YES
* use GAMS's native savepoint mechanism (see GAMSAOsavepoint) to dump this
* solve's solver point
    OPTION SAVEPOINT=2;
$  endIf.dumpsp
  SOLVE %MODEL_NAME% MINIMIZING objZ USING %METHOD%;
$  ifThenI.dumpsp %DUMP_SAVEPOINT%==YES
* this is the 2nd SOLVE this job (the CONVERT solve above is the 1st)
    execute 'mv -f %MODEL_NAME%_p2.gdx %SAVEPOINT_GDX%';
     savepointModelstat = %MODEL_NAME%.modelstat;
     execute_unload '%SAVEPOINT_MODELSTAT%', savepointModelstat;
$  endIf.dumpsp
$elseifi.solvemode %SOLVEMODE%==LOADSOLUTION
* generate model but do not pass it to the solver
  %MODEL_NAME%.JustScrDir=1;
  SOLVE %MODEL_NAME% MINIMIZING objZ USING %METHOD%;
* load solution point and fake modelstatus from "real" solve
  execute_loadpoint '%SAVEPOINT_GDX%';
   execute_load '%SAVEPOINT_MODELSTAT%', savepointModelstat;
   %MODEL_NAME%.modelstat = savepointModelstat;
$endif.solvemode

$LABEL CHECK
* do an check on solution errors
$  BATINCLUDE err_stat.mod SOLVE '*** ERRORS DURING SOLUTION ***'

* hook for GAMS-CGI WWW output
$  IF %GAMS_CGI% == WWW  $BATINCLUDE www_out.cgi

$LABEL NO_SOLVE
*$OFFLISTING
