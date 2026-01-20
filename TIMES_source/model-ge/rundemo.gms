$ offlisting
*------------------------------------------------------------------------------
* TIMES Demo model helper run launching utility
*  -- Assumption is that GAMS is found under system PATH
*------------------------------------------------------------------------------
$ if NOT set runname $SET runname demo12
$ SET SRC ../source
$ SET CAS 2
$ IF gamsversion 341 $SET CAS 4
$ SET GORUN ''
$ SET SOLVER LP=CPLEX NLP=CONOPT
$ IFI %GAMS.LP%==CBC $SET SOLVER LP=CBC NLP=CONOPT
$ IFI %system.filesys%==MSNT $set GORUN cd /d %SYSTEM.FP% &&
*------------------------------------------------------------------------------
* Call GAMS with the RUN file, producing GDX with the same name
$ hiddencall =gams %SYSTEM.FP%%RUNNAME%Base.run idir1=%SYSTEM.FP% idir2=%SYSTEM.FP%%SRC% ps=0 gdx=%SYSTEM.FP%%RUNNAME%Base O=%SYSTEM.FP%%RUNNAME%Base.lst filecase=%CAS% r=%SRC%/_times.g00 %SOLVER%
$ eval ERRLEV errorLevel
$ IF errorLevel 1 $GOTO ERRBASE
* Call the GDX2VEDA utility for producing results files
$ hiddencall %GORUN% gdx2veda %SYSTEM.FP%%RUNNAME%Base %SYSTEM.FP%%SRC%/times2veda.vdd %SYSTEM.FP%%RUNNAME%Base
$ onlisting
$ Remark ********************************************************************************************
$ Remark  The Baseline run for the TIMES demo model %RUNNAME% has been executed to completion.
$ Remark ********************************************************************************************
$ offlisting offlog
$ log -------------------------------------------------------------------------------
$ log --- The Baseline run for the TIMES model %RUNNAME% has been completed.
$ log -------------------------------------------------------------------------------
$ IFI %system.filesys%==MSNT
$ hiddencall ask T=Listbox  D="%RUNNAME%Base.lst -- GAMS Listing file|%RUNNAME%Base.gdx -- Composite GDX file|%RUNNAME%Base.vd* -- Results files|" M="See the output files in Folder: %SYSTEM.FP%" C="Run for %RUNNAME%Base has been completed" o=nul
*------------------------------------------------------------------------------
* Call GAMS with the RUN file, producing GDX with the same name
$ hiddencall =gams %SYSTEM.FP%%RUNNAME%MLF-BaseRep.run idir1=%SYSTEM.FP% idir2=%SYSTEM.FP%%SRC% ps=0 gdx=%SYSTEM.FP%%RUNNAME%MLF-BaseRep O=%SYSTEM.FP%%RUNNAME%MLF-BaseRep.lst filecase=%CAS% r=%SRC%/_times.g00 %SOLVER%
* Call the GDX2VEDA utility for producing results files
$ hiddencall %GORUN% gdx2veda %SYSTEM.FP%%RUNNAME%MLF-BaseRep %SYSTEM.FP%%SRC%/times2veda.vdd %SYSTEM.FP%%RUNNAME%MLF-BaseRep
$ onlisting
$ Remark ********************************************************************************************
$ Remark  The Baseline Replication run for the model %RUNNAME% has been executed to completion.
$ Remark ********************************************************************************************
$ offlisting offlog
$ log -------------------------------------------------------------------------------
$ log --- The Baseline Replication run for the model %RUNNAME% has been completed.
$ log -------------------------------------------------------------------------------
$ IFI %system.filesys%==MSNT
$ hiddencall ask T=Listbox  D="%RUNNAME%MLF-BaseRep.lst -- GAMS Listing file|%RUNNAME%MLF-BaseRep.gdx -- Composite GDX file|%RUNNAME%MLF-BaseRep.vd* -- Results files|" M="See the output files in Folder: %SYSTEM.FP%" C="Run for %RUNNAME%MLF-BaseRep has been completed" o=nul
*------------------------------------------------------------------------------
* Call GAMS with the RUN file, producing GDX with the same name
$ hiddencall =gams %SYSTEM.FP%%RUNNAME%MLF-PolicyEx.run idir1=%SYSTEM.FP% idir2=%SYSTEM.FP%%SRC% ps=0 gdx=%SYSTEM.FP%%RUNNAME%MLF-PolicyEx O=%SYSTEM.FP%%RUNNAME%MLF-PolicyEx.lst filecase=%CAS% r=%SRC%/_times.g00 %SOLVER%
* Call the GDX2VEDA utility for producing results files
$ hiddencall %GORUN% gdx2veda %SYSTEM.FP%%RUNNAME%MLF-PolicyEx %SYSTEM.FP%%SRC%/times2veda.vdd %SYSTEM.FP%%RUNNAME%MLF-PolicyEx
$ onlisting
$ Remark ********************************************************************************************
$ Remark  The Policy Example LP run for the model %RUNNAME% has been executed to completion.
$ Remark ********************************************************************************************
$ offlisting offlog
$ log -------------------------------------------------------------------------------
$ log --- The Policy Example run for the model %RUNNAME% has been completed.
$ log -------------------------------------------------------------------------------
$ IFI %system.filesys%==MSNT
$ hiddencall ask T=Listbox  D="%RUNNAME%MLF-PolicyEx.lst -- GAMS Listing file|%RUNNAME%MLF-PolicyEx.gdx -- Composite GDX file|%RUNNAME%MLF-PolicyEx.vd* -- Results files|" M="See the output files in Folder: %SYSTEM.FP%" C="Run for %RUNNAME%MLF-PolicyEx has been completed" o=nul
*------------------------------------------------------------------------------
* Call GAMS with the RUN file, producing GDX with the same name
$ hiddencall =gams %SYSTEM.FP%%RUNNAME%MLF-PolicyEx.run idir1=%SYSTEM.FP% idir2=%SYSTEM.FP%%SRC% ps=0 gdx=%SYSTEM.FP%%RUNNAME%NLF-PolicyEx O=%SYSTEM.FP%%RUNNAME%NLF-PolicyEx.lst filecase=%CAS% --NONLP=NL r=%SRC%/_times.g00 %SOLVER%
$ eval ERRLEV errorLevel
$ IF errorLevel 1 $GOTO ERRNLP
$ LABEL FINLP
* Call the GDX2VEDA utility for producing results files
$ hiddencall %GORUN% gdx2veda %SYSTEM.FP%%RUNNAME%NLF-PolicyEx %SYSTEM.FP%%SRC%/times2veda.vdd %SYSTEM.FP%%RUNNAME%NLF-PolicyEx
$ onlisting
$ Remark ********************************************************************************************
$ Remark  The Policy Example NLP run for the model %RUNNAME% has been executed to completion.
$ Remark ********************************************************************************************
$ offlisting offlog
$ log -------------------------------------------------------------------------------
$ log --- The Policy Example NLP run for the model %RUNNAME% has been completed.
$ log -------------------------------------------------------------------------------
$ IFI %system.filesys%==MSNT
$ hiddencall ask T=Listbox  D="%RUNNAME%NLF-PolicyEx.lst -- GAMS Listing file|%RUNNAME%NLF-PolicyEx.gdx -- Composite GDX file|%RUNNAME%NLF-PolicyEx.vd* -- Results files|" M="See the output files in Folder: %SYSTEM.FP%" C="Run for %RUNNAME%MLF-PolicyEx has been completed" o=nul
$ terminate
*------------------------------------------------------------------------------
$ label ERRBASE
$ IFI %system.filesys%==MSNT
$ hiddencall ask T=Listbox  D="Error in Demo12 Base run|GAMS Error code = %ERRLEV%|Probably CPLEX License Missing|" M="ERROR! See the Listing file in Folder: %SYSTEM.FP%" C="ERROR in Run for %RUNNAME%Base" o=nul
$ stop
$ label ERRNLP
$ log --- Error - Probably Missing NLP Licence -- Trying Kestrel instead.
$ IFI %system.filesys%==MSNT
$ hiddencall ask T=Listbox  D="Error in Demo12 PolicyExample NLP Benchmark run|GAMS Error code = %ERRLEV%|Probably CONOPT License Missing|Trying Kestrel now instead|" M="ERROR solving NLP Benchmark -- Trying Kestrel instead." C="ERROR in Run for %RUNNAME%NLF-PolicyEx" o=nul
$ hiddencall =gams %SYSTEM.FP%%RUNNAME%MLF-PolicyEx.run idir1=%SYSTEM.FP% idir2=%SYSTEM.FP%%SRC% ps=0 gdx=%SYSTEM.FP%%RUNNAME%NLF-PolicyEx O=%SYSTEM.FP%%RUNNAME%NLF-PolicyEx.lst filecase=%CAS% --NONLP=NL r=%SRC%/_times.g00 %SOLVER% --KESTREL=NLP
$ eval ERRLEV errorLevel
$ IF %ERRLEV%==0 $GOTO FINLP
$ IFI %system.filesys%==MSNT
$ hiddencall ask T=Listbox  D="Error in Demo12 PolicyExample NLP Benchmark run|GAMS Error code = %ERRLEV%|Both Local and Kestrel run failed|" M="ERROR! See the Listing file in Folder: %SYSTEM.FP%" C="ERROR in Run for %RUNNAME%NLF-PolicyEx" o=nul
$ log --- Error - NLP Benchmark run failed, both local and Kestrel attempt.
