# TIMES for GAMSPy (work-in-progress)

This repository contains an **ongoing translation of the ETSAP TIMES model** from **GAMS** to a **GAMSPy-based** workflow. The translation is based on [TIMES](https://github.com/etsap-TIMES/TIMES_model) version 4.9.2 from Oct 19, 2025.

---

## File Structure

The translation is done **file-by-file**. This keeps a clear 1:1 mapping between the upstream GAMS codebase and the GAMSPy project. This ensures maintainability, simplifies auditing, and allows developers familiar with the original TIMES model to navigate the Python version easily.

- Each original **GAMS file** has a **Python counterpart**.
- Naming Convention: Original files like `foo.gms` or `foo.mod` are translated to `foo_gms.py` or `foo_mod.py`.
- Encapsulation: Each GAMS file is represented as a Module Class.

---

## Compilation vs. Execution

GAMS has a strict separation between **compile-time** and **execution-time** behavior. GAMSPy doesn’t compile like GAMS, but executes Python. In this repo, each translation unit is represented as a **module class** with two methods:

- `compile(tc)`: compile-time logic
- `run(tc)`: execution-time logic

The model orchestrator calls these phases in a deterministic order. Keep the naming consistent across all modules.

---

## Compile Time Variables: The Fork & Snapshot Architecture

In GAMS, `$set` and `$setglobal` are pre-processor macros. They are substituted into the code at the exact moment the compiler reads the line. In Python, variables are live references. If you use a variable in a method that runs later (during the execution phase), it will reflect the final value of that variable, not the value it had when the module was initialized. This breaks GAMS logic where a global variable changes halfway through the script.

To replicate GAMS accurately, we use a `CompileTimeEnvironment` with a two-step state management system:

- `fork()`: Manages Scope. Shares `$setglobal` variables and ensures scoped `$set` and `setlocal` variables are isolated to the correct module and its children.
- `snapshot()`: Manages Timing. "Freezes" the state of all compile time variables at a specific line, mimicking the GAMS string substitution.

In addition, we keep track of variable values using:

- `set_local`("VAL", 500)`: Set/change a local variable that is only shared in this file.
- `set_scoped`("VAL", 500)`: Set/change a scoped variable that is shared with children.
- `set_global`("VAL", 500)`: Set/change a global variable that is shared globally.

### Passing Down and Forking

Every module must receive an env (`CompileEnvironment`) object.

Rule: Always `fork()` the environment when initializing a sub-module. This mimics entering a new GAMS file.

```python
def __init__(self, tc, env):
    self.env = env.fork() # Fork for the current file
    self._sub_modules = {}
    self.compile(tc)

def compile(self, tc):
    # Passing environment to a sub-include: $include "sub.gms"
    self.include('SubModule', SubModule(tc, self.env))
```

### The Snapshot Pattern

A snapshot creates a static dictionary of all Global, Scoped, and Local variables at that exact moment.

Rule: Take snapshots in the `__init__` (the "Compilation" phase).

Rule: Use that snapshot in the `run()` method (the "Execution" phase).

```python
def __init__(self, tc, env):
    self.env = env.fork()
    self.compile_snapshot = self.env.snapshot() # Freeze state HERE
```

```python
def run(self, tc):
    # m = %VAL%
    val = self.compile_snapshot.get("VAL")
    tc.add_gams_code(code=f"m = {val};")
```

### Handling Values Changing Within a Class

Sometimes a single GAMS file changes a value internally:

```
$set VAL 10
m = %VAL%;
$set VAL 20
p = %VAL%;
```

In this case, a single `self.compile_snapshot` is insufficient. You must create multiple snapshots to represent different "time-steps" within the same file.

```python
def compile(self, tc):
    # State at the start of the file
    self.env.set_scoped("VAL", 10)
    self.snap_1 = self.env.snapshot()

    # State after some logic
    self.env.set_scoped("VAL", 20)
    self.snap_2 = self.env.snapshot()

def execute(self, tc):
    # Use snap_1 for the first block of GAMS code
    val1 = self.snap_1.get("VAL")
    tc.add_gams_code(code=f"m = {val1};")

    # Use snap_2 for the second block
    val2 = self.snap_2.get("VAL")
    tc.add_gams_code(code=f"p = {val2};")
```

---

## Control Flow: `$label` and `$goto`
TIMES relies heavily on using `$goto` to jump between initialization, declaration, and model phases within the same file. We replicate this using conditional method dispatching.

Instead of a single block of code, the compile and run methods route logic to protected "Phase Methods" based on arguments passed during the include (e.g., `%1 = INIT`, `DECL`, or `MODEL`).

```
$ IF NOT '%1'=='' $GOTO %1%2
  SET I ;
$ EXIT
$ LABEL DECL
  POSITIVE VARIABLE X;
$ EXIT
$ LABEL MODEL
* Do something
```

```python
    def compile(self, tc: "TimesModelClass") -> None:
        # Manages $GOTO
        if self.arg1 == "INIT":
            self._initialize_init_phase(tc)
        elif self.arg1 == "DECL":
            self._initialize_declaration_phase(tc)
        elif self.arg1 == "MODEL":
            self._initialize_model_phase(tc)
        else:
            raise ValueError("Wrong argument passed.")

    def run(self, tc: "TimesModelClass") -> None:
        # Manages $GOTO
        if self.arg1 == "INIT":
            self._run_init_phase(tc)
        elif self.arg1 == "DECL":
            self._run_declaration_phase(tc)
        elif self.arg1 == "MODEL":
            pass
        else:
            raise ValueError("Wrong argument passed.")
```

---

## Data input

`.dd` files are not translated. The GAMSPy model assumes a **single GDX file** containing all relevant scenario data.

- A **single, centralized data-loading step** is used (currently handled in one place, not file-by-file).
- The GDX path (`gdx_path`) is currently configured in one central entrypoint (in `main.py`).


---

### Cheat-Sheet for Translation

| GAMS | Python|
| --- | --- |
| `$include "file.gms"` | `self.include('SubModule', SubModule(tc, self.env))`  |
| `$batinclude "file.gms" "A"` | `self.include('SubModule', SubModule(tc, self.env, arg1="A"))`  |
| `$setlocal VAR 10` | `self.env.set_local("VAR", 10)` |
| `$set VAR 10` | `self.env.set_scoped("VAR", 10)` |
| `$setglobal VAR 10` | `self.env.set_global("VAR", 10)` |
| `%VAR%` | `self.snapshot.get("VAR")` |


---

## Example Module

```python
from src.core.base_module import GamsModule
from src.core.times_model_class import TimesModelClass

class MyTranslatedModule(GamsModule):
    # Instance attributes
    module_name: str = "my_translated_module"
    gams_source: str = "my_translated_module.gms"

    def __init__(self, tc: TimesModelClass, env, arg1=None, arg2=None):
        """
        Standard constructor for all TIMES modules.
        """
        # 1. Fork environment
        self.env = env.fork()

        # 2. Python attributes for easy access (usually batinclude arguments %1 %2)
        self.arg1 = arg1
        self.arg2 = arg2

        # 3. Compile-time snapshot
        # Freezes %VAL%, %MUL%, etc., for the execution phase
        self.snapshot = self.env.snapshot()

        # 4. Initialize child modules storage
        self._sub_modules = {}

        # 5. Trigger compilation
        self.compile(tc)

    def compile(self, tc: TimesModelClass) -> None:
        """
        Equivalent to GAMS Compilation Phase.
        Define Sets, Parameters, Variables, and Equations here.
        """
        # Example of handling $GOTO style logic
        if self.arg1 == "DECL":
            self._initialize_declarations(tc)

        # Example of a nested include: $batinclude "sub_file.gms" "A"
        self.include('SubKey', SubModule(tc, self.env, "A"))

    def run(self, tc: TimesModelClass) -> None:
        """
        Equivalent to GAMS Execution Phase.
        Procedural logic, assignments, and solves go here.
        """
        # Use the frozen snapshot value (Timing Persistence)
        val = self.snapshot.get("VAL")

        # Use Python attributes (Pythonic Readability)
        if self.arg1 == "DECL":
            tc.add_gams_code(
                module_name="my_module",
                phase="execute",
                code=f"Parameter p; p = {val};"
            )

        # Execute sub-modules in the order they were included
        self._sub_modules['SubKey'].run(tc)
```

---

## Project layout

A typical layout looks like this:

- `src/`
  - `core/`
    - `times_model_class.py` (the orchestrator / model context, aka `tc`)
    - one Python module per upstream GAMS file (e.g. `initsys_mod.py`, `setglobs_gms.py`, …)
  - `main.py` (entrypoint: create config, build model, run phases)
  - `data/` (GDX or example datasets)

---

## Naming conventions

**Python variable names** are chosen for readability, while **GAMS symbol names are preserved**.

- **Sets**: `lowercase`
- **Subsets**: `CamelCase`
- **Parameters**: `snake_case`
- **Variables**: `ALL_CAPS`

Rules:

- Keep the legacy GAMS name as the GAMSPy symbol `name="..."`.
- Use a **descriptive Python attribute/variable name** for the symbol handle.
  - Example: `tc.all_year = Set(m, name="ALLYEAR", ...)`

This preserves compatibility with upstream naming while keeping Python code readable.

---

## How to run

Example (adjust paths and config to your setup):

```bash
python -m src.main
```

You need:
- a GAMSPy++ licence that allows to run `addGamsCode()`
- `gamspy` and dependencies installed
- a valid input GDX file

---

## Development guidelines

### Keep provenance clear
When translating, keep it obvious where code came from:

- Preserve upstream comments where possible
- Keep module boundaries aligned with upstream file boundaries

### Order matters
TIMES is complex and depends heavily on symbol declaration order and on "phase" behavior. The orchestrator should be the main source of truth for ordering.

## Known gaps / limitations (current)

- `.dd` files are not yet included.
- Some upstream compile-time features (macros, `$BATINCLUDE` argument substitution, `%1` / `%2`, etc.) require careful handling when reproduced in Python.
- Universe aliases / `ALIAS(*,ITEM)` patterns can require workarounds in GAMSPy, depending on the exact synchronization flow.

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
| #203    | rptmain.mod        |      48 |
| #204    | rptmain.rpt        |     282 |
| #205    | rptmain.stc        |     125 |
| #206    | rptmain.tm         |     140 |
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
