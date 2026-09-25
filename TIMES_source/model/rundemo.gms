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
$ IFI %system.filesys%==MSNT $set GORUN cd /d %SYSTEM.FP% &&
*------------------------------------------------------------------------------
* Call GAMS with the RUN file, producing GDX with the same name
$ hiddencall %GORUN% gams %SYSTEM.FP%%RUNNAME%.run idir1=%SYSTEM.FP% idir2=%SYSTEM.FP%%SRC% ps=0 gdx=%SYSTEM.FP%%RUNNAME% O=%SYSTEM.FP%%RUNNAME%.lst filecase=%CAS% r=%SRC%/_times.g00
* Call the GDX2VEDA utility for producing results files
$ hiddencall %GORUN% gdx2veda %SYSTEM.FP%%RUNNAME% %SYSTEM.FP%%SRC%/times2veda.vdd %SYSTEM.FP%%RUNNAME%
$ onlisting
$ Remark ********************************************************************************************
$ Remark  The GAMS run for the TIMES model %RUNNAME% has been executed to completion.
$ Remark  Please see the folder %SYSTEM.FP% for the output files from the %RUNNAME% run:
$ Remark   -- see %RUNNAME%.lst for the listing file from the %RUNNAME% model run
$ Remark   -- see %RUNNAME%.gdx for the composite GDX file from the %RUNNAME% run
$ Remark   -- see %RUNNAME%.vd* for the results files generated from the solution.
$ Remark  See also %SYSTEM.FP%QA_CHECK.LOG for the TIMES QA check log for the model run.
$ Remark ********************************************************************************************
$ offlisting offlog
$ log -------------------------------------------------------------------------------
$ log --- The GAMS run for the TIMES model %RUNNAME% has been completed.
$ log --- See folder %SYSTEM.FP% for output files from the run:
$ log %system.tab% - %RUNNAME%.lst for the GAMS listing file
$ log %system.tab% - %RUNNAME%.gdx for the composite GDX file
$ log %system.tab% - %RUNNAME%.vd* for the results files
$ log --- See also %SYSTEM.FP%QA_CHECK.LOG for the TIMES QA log.
$ log -------------------------------------------------------------------------------
$ IFI %system.filesys%==MSNT
$ hiddencall ask T=Listbox  D="%RUNNAME%.lst -- GAMS Listing file|%RUNNAME%.gdx -- Composite GDX file|%RUNNAME%~Data_yymmdd_hhmmss.gdx -- Data-only GDX|%RUNNAME%.vd* -- Results files|QA_Check.log -- TIMES QA Log|" M="See the output files in Folder: %SYSTEM.FP%" C="GAMS Run for %RUNNAME% has been completed" o=nul
$ terminate
