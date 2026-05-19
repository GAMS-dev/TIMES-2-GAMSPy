# TIMES for GAMSPy (work-in-progress)

This repository contains an **ongoing translation of the ETSAP TIMES model** from **GAMS** to a **GAMSPy-based** workflow. The translation is based on [TIMES](https://github.com/etsap-TIMES/TIMES_model) version 4.9.2 from Oct 19, 2025.

---

## Project Overview

The translation is done **file-by-file**. This keeps a clear 1:1 mapping between the upstream GAMS codebase and the GAMSPy project. This ensures maintainability, simplifies auditing, and allows modelers familiar with the original TIMES model to navigate the Python version easily.

- Each original **GAMS file** has a **Python counterpart**.
- Naming Convention: Original files like `foo.gms` or `foo.mod` are translated to `foo_gms.py` or `foo_mod.py`.
- Encapsulation: Each GAMS file is represented as a Python Module Class.

---

## Information for Developers

If you are joining the parallel translation effort, **please read our [Contributor's Guide](CONTRIBUTING.md).** The `CONTRIBUTING.md` file contains everything you need to get started, including:
- Local environment setup.
- The "Fork, Capture, Enqueue" architectural workflow.
- Translation cheat sheets for GAMS macros (`$IF`, `$SET`, `$GOTO`).
- How to test your code using Checkpoints and GDX Diff.
- How to pick issues from our GitLab Issue Board.

---

## Project Layout

A typical layout looks like this:

- `src/`
  - `core/`
    - `times_model_class.py` (the orchestrator / model context, aka `tc`)
    - one Python module per upstream GAMS file (e.g. `initsys_mod.py`, `setglobs_gms.py`, …)
  - `main.py` (entrypoint: create config, build model, run phases)
  - `data/` (GDX or example datasets)
- `tests/` (Integration tests, GDX diffs, and compile-time state checks)

---

## How to Run

To run the current state of the translation, you need:
- A GAMSPy++ license that allows to run `addGamsCode()`
- `gamspy` and dependencies installed (see `project.toml`)

Example execution: `python src/main.py`

## Known gaps / limitations (current)

- Universe aliases / `ALIAS(*,ITEM)` patterns can require workarounds in GAMSPy, depending on the exact synchronization flow.
- Testing of individual files is not possible.

---

## Progress Status

| Issue   | File               |   Lines |
|:--------|:-------------------|--------:|
| #1      | atlearn.etl        |     140 |
| #2      | initmty.abs        |      56 |
| #3      | atlearn1.etl       |      57 |
| #4      | atlearn8.etl       |      44 |
| #5      | atlearn9.etl       |      77 |
| #6      | atsc.etl           |      68 |
| #7      | bndmain.mod        |      87 |
| #8      | bnd_act.mod        |      26 |
| #9      | bnd_cum.mod        |      48 |
| #10     | bnd_elas.mod       |      40 |
| #11     | bnd_flo.mod        |      39 |
| #12     | bnd_ire.vda        |      39 |
| #13     | bnd_macro.tm       |      38 |
| #14     | bnd_set.mod        |      34 |
| #15     | bnd_stg.mod        |      27 |
| #16     | bnd_ucv.mod        |      97 |
| #17     | bnd_ucw.mod        |      25 |
| #18     | calibase.mlf       |     119 |
| #19     | cal_cap.mod        |      28 |
| #20     | cal_caps.mod       |      29 |
| #21     | cal_fflo.mod       |      50 |
| #22     | cal_ire.mod        |      42 |
| #23     | cal_nored.red      |      30 |
| #24     | cal_red.red        |      59 |
| #25     | cal_stgn.mod       |      22 |
| #26     | clearsol.stc       |      41 |
| #27     | clearsol.stp       |      35 |
| #28     | coefmain.mod       |      29 |
| #29     | coef_alt.lin       |     161 |
| #30     | coef_cpt.mod       |      63 |
| #31     | coef_csv.mod       |      77 |
| #32     | coef_ext.abs       |     114 |
| #33     | coef_ext.cli       |     225 |
| #34     | coef_ext.etl       |      74 |
| #35     | coef_ext.vda       |      82 |
| #36     | coef_nio.mod       |      69 |
| #37     | coef_obj.mod       |     205 |
| #38     | coef_ptr.mod       |      54 |
| #39     | coef_shp.mod       |      94 |
| #40     | cost_ann.rpt       |     209 |
| #41     | curex.gms          |      81 |
| #42     | ddfupd.msa         |      46 |
| #43     | dumpsol.mod        |      28 |
| #44     | dumpsol1.mod       |     204 |
| #45     | dumpsolv.mod       |      92 |
| #46     | dynslite.vda       |     129 |
| #47     | eqactbnd.mod       |      29 |
| #48     | eqactflo.mod       |      31 |
| #49     | eqactups.vda       |     157 |
| #50     | eqashar.vda        |      78 |
| #51     | eqblnd.mod         |      71 |
| #52     | eqbndcom.mod       |      25 |
| #53     | eqbndcst.mod       |     213 |
| #54     | eqcaflac.vda       |      60 |
| #55     | eqcapact.mod       |      52 |
| #56     | eqcapvac.mod       |      28 |
| #57     | eqchpelc.ier       |      55 |
| #58     | eqcombal.mod       |     114 |
| #59     | eqcpt.mod          |      28 |
| #60     | eqcumcom.mod       |      34 |
| #61     | eqcumflo.mod       |      47 |
| #62     | eqdamage.mod       |     161 |
| #63     | eqdeclr.mod        |     195 |
| #64     | eqdeclr.tm         |      77 |
| #65     | eqflobnd.mod       |      45 |
| #66     | eqflofr.mod        |      27 |
| #67     | eqflomrk.mod       |     107 |
| #68     | eqfloshr.mod       |      42 |
| #69     | eqire.mod          |      54 |
| #70     | eqirebnd.mod       |      70 |
| #71     | eqlducs.vda        |     175 |
| #72     | eqmacro.tm         |     136 |
| #73     | eqmain.mod         |     262 |
| #74     | eqmrkcom.ier       |      94 |
| #75     | eqobj.mod          |     125 |
| #76     | eqobj.tm           |      64 |
| #77     | eqobjann.tm        |     100 |
| #78     | eqobjcst.tm        |      63 |
| #79     | eqobjels.mod       |      51 |
| #80     | eqobjels.rpt       |      37 |
| #81     | eqobjfix.mod       |     227 |
| #82     | eqobjfix.rpt       |      59 |
| #83     | eqobjinv.mod       |     324 |
| #84     | eqobjinv.rpt       |      69 |
| #85     | eqobjvar.mod       |     113 |
| #86     | eqobjvar.rpt       |     182 |
| #87     | eqobsalv.mod       |     142 |
| #88     | eqobsalv.rpt       |      74 |
| #89     | eqpeak.mod         |      88 |
| #90     | eqpk_ect.ier       |      11 |
| #91     | eqptrans.mod       |      41 |
| #92     | eqstgaux.lin       |      43 |
| #93     | eqstgaux.mod       |      44 |
| #94     | eqstgflo.mod       |      31 |
| #95     | eqstgips.lin       |      67 |
| #96     | eqstgips.mod       |      45 |
| #97     | eqstgtss.mod       |      95 |
| #98     | equcrtp.vda        |     123 |
| #99     | equcwrap.mod       |      42 |
| #100    | equserco.mod       |     122 |
| #101    | equ_ext.abs        |     208 |
| #102    | equ_ext.cli        |     112 |
| #103    | equ_ext.dsc        |      32 |
| #104    | equ_ext.ecb        |      48 |
| #105    | equ_ext.etl        |      76 |
| #106    | equ_ext.ier        |      48 |
| #107    | equ_ext.mlf        |     183 |
| #108    | equ_ext.msa        |     116 |
| #109    | equ_ext.vda        |     105 |
| #110    | eqxbnd.mod         |      57 |
| #111    | err_stat.mod       |      73 |
| #112    | fillcost.gms       |      43 |
| #113    | fillparm.gms       |      57 |
| #114    | fillsow.stc        |      47 |
| #115    | fillvint.gms       |      35 |
| #116    | fillwave.gms       |      21 |
| #117    | filparam.gms       |      43 |
| #118    | filshape.gms       |      26 |
| #119    | forcupd.cli        |      33 |
| #120    | gasgrids.vda       |     206 |
| #121    | gdxfilter.gms      |      30 |
| #122    | globals.def        |      16 |
| #123    | initmty.cli        |     131 |
| #124    | initmty.dsc        |      17 |
| #125    | initmty.etl        |      66 |
| #126    | initmty.ier        |      23 |
| #127    | initmty.mlf        |      60 |
| #128    | initmty.mod        |     508 |
| #129    | initmty.msa        |     117 |
| #130    | initmty.stc        |      82 |
| #131    | initmty.tm         |      56 |
| #132    | initmty.vda        |      76 |
| #133    | initsys.mod        |     187 |
| #134    | init_ext.abs       |      33 |
| #135    | init_ext.dsc       |      23 |
| #136    | init_ext.vda       |     154 |
| #137    | maindrv.mod        |     133 |
| #138    | main_ext.mod       |      23 |
| #139    | maplists.def       |     119 |
| #140    | mod_equa.mod       |     216 |
| #141    | mod_equa.tm        |      91 |
| #142    | mod_ext.abs        |      28 |
| #143    | mod_ext.cli        |      13 |
| #144    | mod_ext.dsc        |      12 |
| #145    | mod_ext.etl        |      21 |
| #146    | mod_ext.ier        |      18 |
| #147    | mod_ext.vda        |      55 |
| #148    | mod_vars.abs       |      54 |
| #149    | mod_vars.cli       |      26 |
| #150    | mod_vars.dsc       |      19 |
| #151    | mod_vars.etl       |      38 |
| #152    | mod_vars.mod       |      96 |
| #153    | mod_vars.msa       |      34 |
| #154    | mod_vars.tm        |      57 |
| #155    | par_uc.rpt         |      29 |
| #156    | pextlevs.stc       |      63 |
| #157    | powerflo.vda       |     449 |
| #158    | ppmain.mod         |    1357 |
| #159    | ppmain.tm          |      72 |
| #160    | ppm_ext.cli        |      55 |
| #161    | ppm_ext.dsc        |      16 |
| #162    | ppm_ext.ecb        |      50 |
| #163    | ppm_ext.mlf        |      92 |
| #164    | ppm_ext.vda        |     167 |
| #165    | pp_actef.vda       |      80 |
| #166    | pp_chp.ier         |      63 |
| #167    | pp_chp.mod         |      71 |
| #168    | pp_clean.mod       |      26 |
| #169    | pp_lvlbd.mod       |      47 |
| #170    | pp_lvlbr.mod       |      55 |
| #171    | pp_lvlfc.mod       |      45 |
| #172    | pp_lvlff.mod       |      40 |
| #173    | pp_lvlfs.mod       |      43 |
| #174    | pp_lvlif.mod       |      39 |
| #175    | pp_lvlpk.mod       |      55 |
| #176    | pp_lvlus.mod       |      40 |
| #177    | pp_micro.mod       |      91 |
| #178    | pp_off.mod         |      23 |
| #179    | pp_prelv.vda       |     125 |
| #180    | pp_qack.mod        |     388 |
| #181    | pp_qafs.mod        |     110 |
| #182    | pp_qaput.mod       |      16 |
| #183    | pp_reduce.red      |     188 |
| #184    | pp_shapr.mod       |      46 |
| #185    | prepparm.gms       |      77 |
| #186    | preppm.mod         |     252 |
| #187    | preppm.msa         |      78 |
| #188    | prepret.dsc        |     153 |
| #189    | prepxtra.mod       |      91 |
| #190    | prep_ext.abs       |      35 |
| #191    | prep_ext.dsc       |      20 |
| #192    | prep_ext.ier       |      21 |
| #193    | prep_ext.mlf       |      43 |
| #194    | prep_ext.stc       |      56 |
| #195    | prep_ext.tm        |      32 |
| #196    | prep_ext.vda       |      81 |
| #197    | preshape.gms       |      49 |
| #198    | presolve.mlf       |     103 |
| #199    | readbprice.mod     |      48 |
| #200    | recurrin.stc       |     182 |
| #201    | resloadc.vda       |     154 |
| #202    | rptlite.rpt        |     176 |
| #203    | rptmain.mod        |      48 |
| #204    | rptmain.rpt        |     282 |
| #205    | rptmain.stc        |     125 |
| #206    | rptmain.tm         |     140 |
| #207    | rptmisc.rpt        |     276 |
| #208    | rpt_dam.mod        |      56 |
| #209    | rpt_ext.cli        |      52 |
| #210    | rpt_ext.ecb        |      70 |
| #211    | rpt_ext.ier        |      50 |
| #212    | rpt_ext.mlf        |     115 |
| #213    | rpt_ext.msa        |      63 |
| #214    | rpt_obj.rpt        |     148 |
| #215    | rpt_objc.rpt       |     128 |
| #216    | rpt_par.cli        |      80 |
| #217    | sensis.stc         |      43 |
| #218    | setglobs.gms       |     375 |
| #219    | solprep.msa        |     133 |
| #220    | solputta.ans       |     263 |
| #221    | solsetv.v3         |     210 |
| #222    | solsubta.ans       |      50 |
| #223    | solsysd.v3         |      14 |
| #224    | solvcoef.msa       |      91 |
| #225    | solve.mod          |      47 |
| #226    | solve.msa          |     178 |
| #227    | solve.stc          |     134 |
| #228    | solve.stp          |     329 |
| #229    | sol_flo.red        |      43 |
| #230    | sol_ire.rpt        |      20 |
| #231    | spoint.mod         |      87 |
| #232    | stages.stc         |     272 |
| #233    | times2veda.vdd     |     163 |
| #234    | times2veda_stc.vdd |     149 |
| #235    | times2veda_v3.vdd  |     108 |
| #236    | timesrng.gms       |      16 |
| #237    | timslice.mod       |     123 |
| #238    | ucbet.vda          |     129 |
| #239    | uc_act.mod         |      52 |
| #240    | uc_cap.mod         |      52 |
| #241    | uc_cli.mod         |      43 |
| #242    | uc_com.mod         |      47 |
| #243    | uc_flo.mod         |      77 |
| #244    | uc_ire.mod         |      57 |
| #245    | uc_ncap.mod        |      50 |
| #246    | uc_pasti.mod       |      32 |
| #247    | units.def          |      38 |
| #248    | writeddf.msa       |      82 |
| #249    | wrtbprice.mod      |      35 |

## License

TBD
