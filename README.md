# TIMES for GAMSPy (work in progress)

[![Release](https://img.shields.io/github/v/release/GAMS-dev/TIMES-2-GAMSPy?include_prereleases&sort=semver)](https://github.com/GAMS-dev/TIMES-2-GAMSPy/releases)
[![Native GAMSPy 71%](https://img.shields.io/badge/native%20GAMSPy-71%25-yellowgreen)](#status)
[![Coverage 88%](https://img.shields.io/badge/coverage-88%25-green)](#test-coverage)
[![License: GPLv3](https://img.shields.io/badge/license-GPLv3-blue)](TIMES_source/source/NOTICE-GPLv3.txt)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org)
[![GAMSPy ≥1.28](https://img.shields.io/badge/GAMSPy-%E2%89%A51.28-blue)](https://gamspy.readthedocs.io)
[![TIMES 4.9.2](https://img.shields.io/badge/TIMES-4.9.2-blue)](https://github.com/etsap-TIMES/TIMES_model)


This repository contains an **ongoing translation of the [IEA-ETSAP TIMES](https://github.com/etsap-TIMES/TIMES_model) model generator** from **GAMS** to **[GAMSPy](https://gamspy.readthedocs.io)**, the Python interface to GAMS. It is based on TIMES version 4.9.2 (Oct 19, 2025).

The goal is a Python code base that produces **the same results as the original GAMS TIMES**, while being easier to read, extend, test and integrate into Python workflows. We are sharing the current state so that the community can try it out, give feedback and write training material around it.

> [!NOTE]
> This is a snapshot of active development. Interfaces, file names and internals may still change.

---

## Status

The translation happens in two phases:

1. **Phase 1 (done): Structure.** Every upstream GAMS file has a Python counterpart. GAMS compile-time logic (`$IF`, `$SET`, `$BATINCLUDE`, `%MACRO%` substitution, …) is implemented in Python. Execution-time GAMS code was first carried over verbatim inside `add_gams_code(...)` blocks. The result already reproduces the GAMS results for all instances in our test suite.
2. **Phase 2 (ongoing): Native GAMSPy.** The embedded GAMS code is being replaced step by step with native GAMSPy (`Set`, `Parameter`, `Equation`, `Sum`, `.where[...]`, …) while keeping the numerical results identical.

As of October 2026, about **71%** of the originally embedded GAMS code has been replaced by native GAMSPy, and 192 of the 250 files in `src/core/` contain no embedded GAMS code at all.

### Versions and releases

Every update of this repository is published as a [GitHub release](https://github.com/GAMS-dev/TIMES-2-GAMSPy/releases). Version numbers follow the progress of the translation:

| Versions                     | Stage                                                                  |
|:-----------------------------|:-----------------------------------------------------------------------|
| `v0.1.0`                     | Phase 1 complete: full Python structure, results identical to GAMS     |
| `v0.2.0`, `v0.3.0`, …        | Alpha: Phase 2 in progress, a new minor version for every update       |
| `v1.0.0b1`, `v1.0.0b2`, …    | Beta: translation complete, testing and polishing                      |
| `v1.0.0`                     | First stable release                                                   |

All `0.x` and beta versions are marked as pre-releases. If you write training material, please refer to a specific release so readers can reproduce your examples.

---

## Quick Start

### Requirements

- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/) (recommended; plain `pip` also works)
- [GAMSPy](https://gamspy.readthedocs.io) and the other dependencies from [`pyproject.toml`](pyproject.toml)
- A GAMSPy license that allows `Container.addGamsCode()` (GAMSPy++). This is needed as long as parts of the model are still executed as embedded GAMS code (see [Status](#status)). You can get one from the [GAMS Portal](https://portal.gams.com). See the [GAMSPy installation guide](https://gamspy.readthedocs.io/en/latest/user/installation.html) for how to install a license.
- Optional: a GAMS installation, if you want to run the original TIMES code for comparison

### Installation

```bash
git clone https://github.com/GAMS-dev/TIMES-2-GAMSPy.git
cd TIMES-2-GAMSPy
uv sync --no-dev                     # creates .venv with the tested versions from uv.lock
source .venv/bin/activate            # Windows: .venv\Scripts\activate
gamspy install license <your-license> --use-uv   # also installs the solvers it includes, e.g. HiGHS
```

Without uv, create and activate a virtual environment, run `pip install -e .`, and drop `--use-uv` from the license install. This installs the latest compatible dependency versions instead of the tested ones from `uv.lock`.

To work with a specific release, check out its tag, e.g. `git checkout v0.2.0`. The package version is derived from these tags, so install from a git clone rather than from a downloaded ZIP archive; without git data the version shows up as `0.0.0`.

### Run the demo model

The TIMES Demo model data ships with the repository in [`TIMES_source/model`](TIMES_source/model) and [`TIMES_source/model-ge`](TIMES_source/model-ge), so the following run files in [`examples`](examples) run without any extra downloads:

| Run file                                                  | Data directory          | Description                                           |
|:----------------------------------------------------------|:------------------------|:------------------------------------------------------|
| [`demo12.toml`](examples/demo12.toml)                     | `TIMES_source/model`    | TIMES Demo12 model                                    |
| [`demo12Base.toml`](examples/demo12Base.toml)             | `TIMES_source/model-ge` | Demo12 base scenario (model-ge variant)               |
| [`demo12Base_ucbet.toml`](examples/demo12Base_ucbet.toml) | `TIMES_source/model-ge` | Demo12 base with extra user constraints (`ucbet.vda`) |

```bash
python src/main.py --run examples/demo12.toml --lp-solver HIGHS
```

This builds and solves the model with the open-source solver HiGHS, which works with any license, including the free personal one. It writes `demo12.lst` / `demo12.log` together with GDX files of the compile, execution and solution state to the working directory. Without `--lp-solver`, the default solver CPLEX is used, which needs a license that includes it (see [Choosing the solver](#choosing-the-solver)).

A run file is the counterpart of a TIMES `.run` file: milestone years, data files and the `%SWITCH%` settings (see [Running your own model](#running-your-own-model)). The test suite runs the same models from [`src/utils/run_registry.py`](src/utils/run_registry.py), where every instance is a `RunConfig` object; `--run` also accepts their names, e.g. `--run demo12`. The other registry instances (the `DemoS_*` series and others) use data sets that are not yet part of this repository.

#### Running your own model

To run your own model, write a TOML run file, the counterpart of a TIMES `.run` file, and pass its path to `--run`:

```bash
python src/main.py --run path/to/mymodel.toml --lp-solver HIGHS
```

[`examples/demo12.toml`](examples/demo12.toml) is [`demo12.run`](TIMES_source/model/demo12.run) translated line by line. [`examples/template.toml`](examples/template.toml) lists every key a run file accepts, with its allowed values and default; copy it and uncomment what you need. In short:

```toml
# mymodel.toml, next to the .dd files
run_name = "mymodel"              # default: the file name
time_slices = "mymodel_ts.dd"
data_modules = ["base.dd", "newtechs.dd", "syssettings.dd"]
milestone_years = [2005, 2010, 2015, 2020]
lp_solver = "CPLEX"               # optional, as is nlp_solver

[env_vars]                        # the $SET switches
reduce = "YES"
vda = "YES"
obj = "MOD"
botime = 1960
rpt_opt = [["NCAP", "1", 1]]      # $SET RPT_OPT NCAP.1 1

[options]                         # OPTION statements, by their GAMS names
reslim = 1000

[solver_options.cplex]            # instead of cplex.opt next to the .dd files
lpmethod = 4
```

`data_dir`, the folder with the `.dd` files, is relative to the run file and defaults to the run file's folder. A run file placed next to its `.dd` files therefore needs no `data_dir`. Unknown keys and invalid switch values are reported when the file is loaded, unknown `[options]` names when the run starts. `--lp-solver` and `--nlp-solver` specify solvers.

#### From a GAMS `.run` file to a TOML run file

A GAMS `.run` file sets compile-time switches, includes the data files and calls the TIMES driver. The driver calls are the same for every model and are made by [`src/main.py`](src/main.py), so a GAMSPy run file (`.toml`) keeps only the parts that differ between models:

| GAMS `.run` file | TOML run file |
|:--|:--|
| `$SET RUN_NAME demo12` | `run_name = "demo12"` (default: the file name) |
| `$SET <SWITCH> <value>`, e.g. `$SET REDUCE YES` | `reduce = "YES"` under `[env_vars]`: the switch name in lower case, the value as in the `.run` file |
| `$SET RPT_OPT NCAP.1 1` | `rpt_opt = [["NCAP", "1", 1]]` under `[env_vars]`, one `[item, j, value]` row per entry |
| `$BATINCLUDE initmty.mod IER` | `ier = "YES"` under `[env_vars]` |
| `$BATINCLUDE demo12_ts.dd` (the time slices, before `initsys.mod`) | `time_slices = "demo12_ts.dd"` |
| `$BATINCLUDE <file>.dd` (after `initmty.mod`) | `data_modules = ["base.dd", ...]`, in the same order |
| `SET MILESTONYR /2005,2010,2015/;` | `milestone_years = [2005, 2010, 2015]` |
| `OPTION LP=CPLEX;` | `lp_solver = "CPLEX"` (`nlp_solver` for NLP models) |
| `OPTION RESLIM=50000, ITERLIM=999999;` | `reslim = 50000` and `iterlim = 999999` under `[options]`: the option name in lower case. Without them, the `OPTION` settings of the demo `.run` files are used (see `DEFAULT_OPTIONS` in [`src/utils/config.py`](src/utils/config.py)) |
| `<solver>.opt` solver option file | the same file next to the `.dd` files, or its lines as `key = value` under `[solver_options.<solver>]`, e.g. `[solver_options.cplex]` |
| `idir` folder with the `.dd` files | `data_dir = "..."`, relative to the run file (default: its folder) |
| `$ONMULTI`, `$BATINCLUDE initsys.mod`, `initmty.mod`, `maindrv.mod mod` | nothing: [`src/main.py`](src/main.py) does this for every run |

Step by step:

1. Copy [`examples/demo12.toml`](examples/demo12.toml) next to your `.run` file and rename it, e.g. `mymodel.run` → `mymodel.toml`. Delete its `data_dir` line.
2. Replace the keys under `[env_vars]` with your `$SET` switches. Leave out any switch your `.run` file does not set; it keeps its TIMES default. [`examples/template.toml`](examples/template.toml) describes every supported switch and its allowed values.
3. Set `time_slices` to the time-slice file included before `initsys.mod`. List the remaining `$BATINCLUDE`d `.dd` files in `data_modules`, in the order of the `.run` file.
4. Copy the years of `SET MILESTONYR` to `milestone_years`, then set `run_name` and the solvers. These top-level keys must come before the first table such as `[env_vars]`, because TOML puts every key after a table header into that table.
5. Put `OPTION` statements that differ from the defaults under `[options]`. Leave a `<solver>.opt` file next to the `.dd` files, or move its lines to `[solver_options.<solver>]`.
6. Run `python src/main.py --run path/to/mymodel.toml` and compare the result with the GAMS run (see [Compare with the original GAMS TIMES](#compare-with-the-original-gams-times)).

Other GAMS statements in a `.run` file, such as extra data assignments, have no counterpart in a run file yet.

#### Choosing the solver

Select the solver with `--lp-solver` (LP and MIP models) and `--nlp-solver` (NLP models); without them the installation's default solver is used:

```bash
python src/main.py --run examples/demo12Base.toml --lp-solver CPLEX
python src/main.py --run examples/demo12.toml --lp-solver default --nlp-solver CONOPT4
```

Any solver installed for GAMSPy can be used: `gamspy list solvers` shows the installed ones, `gamspy install solver <name>` adds one. Commercial solvers such as CPLEX also need a license that includes them. Pass `default` to use the installation's default solver again.

### Compare with the original GAMS TIMES

The GAMS source of TIMES 4.9.2 is in [`TIMES_source/source`](TIMES_source/source), with small additions for the test pipeline such as the solver switches below. To run the same demo with GAMS:

```bash
gams TIMES_source/model/demo12.run idir1=TIMES_source/source idir2=TIMES_source/model filecase=4
```

`--LPSOLVER` and `--NLPSOLVER` select the solvers (default: the installation's default solver); an `OPTION LP=...` in the `.run` file has no effect on the TIMES solve.

---

## How the Code Is Organized

The translation is done **file by file**, with a clear 1:1 mapping between the upstream GAMS code and the Python code. This makes it easy to audit the translation and lets TIMES modelers find their way around the Python version.

- Every GAMS file has a Python counterpart: `foo.mod` becomes `src/core/foo_mod.py`, `foo.gms` becomes `foo_gms.py`, `foo.vda` becomes `foo_vda.py`, and so on.
- Every GAMS file is represented as a Python class (a subclass of `GamsClass`).
- The original GAMS header comments are kept, so both versions are easy to put side by side.

```text
src/
  main.py                    entry point: python src/main.py --run <instance or run file>
  core/                      one module per upstream TIMES file (e.g. eqactflo_mod.py, ppmain_mod.py)
  utils/
    times_model_class.py     the model context ("tc"): the GAMSPy Container, symbols and helpers
    compile_environment.py   Python replacement for GAMS compile-time variables (%REDUCE%, %VAR%, ...)
    run_registry.py          instance definitions (Python counterpart of .run files)
TIMES_source/
  source/                    original TIMES 4.9.2 GAMS source (GPLv3)
  model/, model-ge/          TIMES Demo model data (CC-BY-4.0)
tests/                       integration tests: GAMS vs. GAMSPy GDX comparison (need internal data)
```

### A side-by-side example

[`TIMES_source/source/eqactflo.mod`](TIMES_source/source/eqactflo.mod), which ties process activity to its primary commodity flows:

```gams
%EQ%_ACTFLO(RTP_VINTYR(%R_V_T%,P),S %SWT%)$(PRC_TS(R,P,S) *
$IF %REDUCE% == 'YES'                     (NOT RTPS_OFF(R,T,P,S)) *
                                          PRC_ACT(R,P)) ..
    %VAR%_ACT(R,V,T,P,S %SOW%)$RTP_VARA(R,T,P)
  =E=
    SUM(RPC_PG(R,P,C)$RTPCS_VARF(R,T,P,C,S),
        (%VAR%_FLO(R,V,T,P,C,S %SOW%)$RP_FLO(R,P) +
         SUM(RPC_IRE(R,P,C,IE)$RP_AIRE(R,P,IE),
             %VAR%_IRE(R,V,T,P,C,S,IE %SOW%))$RP_IRE(R,P)
        ) / PRC_ACTFLO(R,V,P,C));
```

and its translation in [`src/core/eqactflo_mod.py`](src/core/eqactflo_mod.py):

```python
VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
VAR_FLO = g.get_variable(f"{self.env.var}_FLO")
VAR_IRE = g.get_variable(f"{self.env.var}_IRE")

reduce_con = (~g.RtpsOff[r, t, p, s]) if self.env.reduce == "YES" else 1

eq = g.get_equation(f"{self.env.eq}_ACTFLO")
eq[g.RtpVintyr[*r_v_t, p], s, *swt].where[
    g.PrcTs[r, p, s] * (reduce_con) * g.PrcAct[r, p]
] = VAR_ACT[r, v, t, p, s, *sow].where[g.RtpVara[r, t, p]] == (
    Sum(
        c.where[g.RpcPg[r, p, c].where[g.RtpcsVarf[r, t, p, c, s]]],
        (
            VAR_FLO[r, v, t, p, c, s, *sow].where[g.RpFlo[r, p]]
            + Sum(
                g.RpcIre[r, p, c, ie].where[g.RpAire[r, p, ie]],
                VAR_IRE[r, v, t, p, c, s, ie, *sow],
            ).where[g.RpIre[r, p]]
        )
        / g.prc_actflo[r, v, p, c],
    )
)
```

GAMS compile-time switches such as `$IF %REDUCE% == 'YES'` become plain Python `if` statements. Macros such as `%VAR%` and `%SOW%` become fields of the compile environment (`self.env`).

### Compile time vs. execution time

GAMS separates compile time (`$`-directives, macros) from execution time (assignments, solves). GAMSPy does not. To preserve the original execution order, the Python modules process all compile-time logic first and defer execution-time code with an `enqueue()` mechanism.

---

## Feedback and Contributions

Development happens in an internal repository at GAMS. Its `main` branch is published here as a new release whenever we complete a step (see [Versions and releases](#versions-and-releases)), so this repository contains only the `main` branch. We welcome:

- **Issues** with bug reports, questions, or places where the GAMSPy translation behaves differently from GAMS TIMES
- **Training material, notebooks and examples** built on top of this code. Let us know about them in an issue.

---

## Known Limitations

- Less than a third of the execution-time code still runs as embedded GAMS code through `add_gams_code()`, which requires a GAMSPy++ license.
- Text output written with GAMS `PUT` statements (e.g. `QA_CHECK.LOG`, the VEDA report files and solution dumps) is not yet fully ported; much of it still runs as embedded GAMS code.
- Universe aliases (`ALIAS(*,ITEM)` patterns) need workarounds in GAMSPy.
- Individual modules cannot be tested in isolation; testing is done by comparing complete model runs against GAMS.
- Only the data sets listed in [Run the demo model](#run-the-demo-model) are publicly available so far.
- The test suite in `tests/` depends on internal test data and CI tooling, so it cannot be run from this repository yet. To check results, compare a GAMSPy run with the [original GAMS run](#compare-with-the-original-gams-times).

## Test coverage

The integration tests run about 80 TIMES instances (demo models and variants that switch on extensions such as ECB, MLF, ETL, CLI, ABS, stochastics and the reduction algorithm) and compare GAMS and GAMSPy results. Their statement and branch coverage of `src/` is currently **88%**: 24,717 statements and 3,140 branches across 258 files. 102 files are fully covered, and 14 translated TIMES files are below 50%:

| File | Coverage |
|---|---|
| `src/core/timesrng_gms.py` | 0% |
| `src/core/gdxfilter_gms.py` | 0% |
| `src/core/rptmain_rpt.py` | 12% |
| `src/core/dynslite_vda.py` | 16% |
| `src/core/forcupd_cli.py` | 20% |
| `src/core/eqobjinv_rpt.py` | 23% |
| `src/core/sensis_stc.py` | 24% |
| `src/core/resloadc_vda.py` | 35% |
| `src/core/rpt_ext_ecb.py` | 38% |
| `src/core/eqobsalv_rpt.py` | 40% |
| `src/core/ppm_ext_ecb.py` | 41% |
| `src/core/equ_ext_ecb.py` | 43% |
| `src/core/uc_cli_mod.py` | 46% |
| `src/core/preppm_msa.py` | 48% |


---

## License

- The GAMSPy translation in `src/` is derived from the TIMES model generator and, like it, is licensed under the **GNU General Public License v3.0** (see [`TIMES_source/source/NOTICE-GPLv3.txt`](TIMES_source/source/NOTICE-GPLv3.txt)).
- The original TIMES source in [`TIMES_source/source`](TIMES_source/source) is © ETSAP, licensed under GPLv3.
- The TIMES Demo model data in [`TIMES_source/model`](TIMES_source/model) and [`TIMES_source/model-ge`](TIMES_source/model-ge) is licensed under [CC-BY-4.0](TIMES_source/NOTICE-CC-BY-4.0.txt).

## Acknowledgements

TIMES is developed and maintained by the [Energy Technology Systems Analysis Programme (ETSAP)](https://iea-etsap.org) of the International Energy Agency. Documentation of the model is available in the [TIMES Documentation](https://github.com/etsap-TIMES/TIMES_Documentation) repository.
