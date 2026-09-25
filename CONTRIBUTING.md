# Contributor’s Guide: TIMES-to-GAMSPy Translation

Welcome! This guide outlines the workflow for translating the ETSAP TIMES model into GAMSPy while maintaining 1:1 functional parity with the legacy GAMS codebase. This repository contains both the GAMS TIMES source code as well as the GAMSPy translation.

---

## Environment Setup

Before starting your first translation, ensure your local environment is ready:

1. **Clone & Branch**:
```bash
git clone git@git.gams.com:consulting/times-2-gamspy.git
```

2. **Install Dependencies**:
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev,test]"
pre-commit install
gamspy install solver cbc
```
Note: Install a personal [license](https://portal.gams.com) for this setup. While a personal network license works, keep in mind it is limited to open-source solvers.

3. **Add Windows Defender Exclusion List** (Windows only)
If you are working on a windows machine, you want to add the TIMESPy repository to the exclusion list of Windows Defender, otherwise, running TIMESPy will be extremely slow.

Open powershell as administrator and navigate to the repository and run:

```bash
./.vscode/exclusionList.ps1
```

---

## Downloading Demo Instances

Before working on the project for the first time, you should download the demo instances used by the test suite.

### 1. Configure Nextcloud Credentials

Create a `.env` file in the root directory of the repository and add the following variable:

```bash
NEXTCLOUD_CREDS=<password>
```

You can find the password in GitLab:

1. Open the project in GitLab.
2. Navigate to **Settings → CI/CD**.
3. Navigate to the **CI/CD Variables** section.
4. Copy the value from the **Value** column of the NEXTCLOUD_CREDS variable.

### 2. Download Demo Instances

Activate your virtual environment and run the test suite once from the repository root:

```bash
source venv/bin/activate  # Windows: venv\Scripts\activate
pytest
```

During the first run, `pytest` will:

- Download all required demo instances from Nextcloud.
- Prepare the local test environment.
- Execute the test suite.

This initial setup can take several minutes. Once the tests complete successfully, your environment is fully configured.

---

## Using Visual Studio Code (Optional)

You are free to use any code editor or IDE. The following steps are only relevant if you are using **Visual Studio Code**.

Before running the model, make sure VS Code is using the project's Python virtual environment.

1. Open the Command Palette (`Ctrl+Shift+P`).
2. Search for and select **Python: Select Interpreter**.
3. Choose the interpreter from your project's virtual environment:
   - **Windows:** `venv\Scripts\python.exe`
   - **Linux/macOS:** `venv/bin/python`

Once the interpreter is configured, you can conveniently run or debug the model directly from `src/main.py`.
When launching `main.py`, you must provide the `--run` command-line argument to specify the demo instance to execute. For example:

```text
--run demos_012a
```

## Setting Up LARK

1. Pull the Repository from https://git.gams.com/devel/gams-lark
2. Goto [Using Lark](#using-lark)

---

## Phase 1 Summary
Phase 1 focused on migrating the overall structure of the TIMES codebase to Python while preserving the original GAMS execution semantics. Rather than translating the model directly into native GAMSPy on a statement-by-statement basis, the executable GAMS logic was largely preserved and executed through add_gams_code() blocks embedded within Python modules. At the same time, the surrounding infrastructure was translated to native Python: each GAMS module became a Python class, compile-time constructs such as $IF, $SET, $BATINCLUDE, and environment variables were replaced by Python logic, and the original execution flow was restructured using Python methods.

A particular challenge was that GAMS distinguishes between compile time and execution time, whereas GAMSPy does not. To preserve the original execution order and semantics, runtime code was therefore deferred using an enqueue() mechanism, allowing compile-time processing to complete before execution-time logic was evaluated. This provided a clean separation between preprocessing and model execution while maintaining behavior equivalent to the original GAMS implementation. Also see [The Core Workflow](#the-core-workflow) in the appendix from phase 1.

The result of Phase 1 was a fully functional Python representation of the TIMES model that faithfully reproduced the original GAMS behavior and established the infrastructure for the incremental replacement of runtime GAMS code with native GAMSPy in Phase 2. While the resulting code is not always the most elegant from a software engineering perspective, this intermediate architecture was a deliberate design choice. Preserving correctness and providing a safe, incremental migration path were considered more important than producing idiomatic GAMSPy code at this stage.

## Phase 2: Organization

Phase 2 is much simpler to organize than Phase 1. Instead of creating the initial Python translation for every GAMS module, the goal is now to incrementally replace `add_gams_code()` blocks with native GAMSPy while preserving the exact numerical behavior of the model.

### Step 1: Pick an Open Issue

Every GAMS file has a corresponding GitLab Issue. Go to the project's [Issue Board](https://git.gams.com/consulting/times-2-gamspy/-/boards), choose an unassigned file/issue in "up-next" that you would like to work on, and assign it to yourself.

### Step 2: Create a Merge Request

Create a merge request for your changes and link it to the corresponding issue. Work on the issue until the translation is complete.

### Step 3: Verify Your Changes

Before requesting a review, make sure that your changes do not alter the model's behavior.

The most important check is that the model still solves successfully. During development, it is usually sufficient to run **Demo 12**, as this catches the vast majority of translation issues. If Demo 12 runs successfully, there is a good chance that the remaining CI tests will also pass.

You can test the model by passing the instance name to pytest:

```bash
pytest -k demo_12
```

When you push your branch, the GitLab CI pipeline will execute a broader set of tests. Please ensure that the pipeline passes before requesting a review.

#### Step 4: Close Issues via Commit Message
Use commit messages that close the corresponding issues once it gets merged to the default branch. Example: `Translating initsys.mod Closes #133`

### Step 5: Request a Review

Once your implementation is complete and all CI checks have passed, add **Justine** or **Robin** as a reviewer to your merge request.

---

## Moving from `add_gams_code` to Native GAMSPy

While `self.tc.add_gams_code` is a powerful tool for injecting legacy GAMS strings, the ultimate goal of the translation is to leverage **native GAMSPy syntax**.

When translating equations or data assignments natively, follow these core patterns:

### 1. Symbol Lifecycle and Scoping
Instead of executing generic string declarations, pull all multidimensional parameters, variables, and sets off the global TimesModelClass container instance (abbreviated locally as g).

- **Global Attributes**: Do not instantiate core symbols inside your module. Use the pre-existing attributes attached to the main tc container (e.g., ``g.coef_icom``, ``g.ncap_ocom``).

- **Python Naming Parity**: While your variable definitions follow readable [Naming Conventions](#naming-conventions), ensure they reference their exact legacy GAMS text names inside the backend compiler engine (e.g., ``g.coef_icom`` maps to GAMS ``name="COEF_ICOM"``).

```python
from gamspy import Set

g = self.tc
g.PrcDscncap = Set(
    m,
    name="PRC_DSCNCAP",
    domain=[g.r, g.p],
    description="Processes with discrete capacity additions",
)
```

Use `self.tc.set_parameter()` or `self.tc.set_variable()` if you encounter something along the lines of:

```
Variable  %VAR%_UC(UC_N)			Slacks for UC constraints;
```

This translates to:

```python
g = self.tc
m = g.container
g.set_variable(
    name=f"{self.env.var}_UC(UC_N)",
    var=Variable(
        m,
        name=f"{self.env.var}_UC(UC_N)",
        domain=[g.ucn],
        description="Slacks for UC constraints"
        )
    )
```


### 2. Unpacking for Readability
When writing complex algebraic assignments, referencing `g.symbol_name` repeatedly makes the code difficult to read. Always unpack **domain sets** and the global class handler at the top of your execution methods.

```python
def modifications(self) -> None:
    # 1. Alias the global container handle to a brief, concise pointer
    g = self.tc

    # 2. Unpack the exact coordinate domain indexing sets required for code snippet
    r, v, p, c, t = g.r, g.v, g.p, g.c, g.t
```

### 3. Syntax Mapping Rules

When moving legacy logic into GAMSPy, follow this mapping matrix to convert math statements accurately:

| Legacy GAMS |	Native GAMSPy Equivalent |	Architectural Requirement |
| --- | --- | ------- |
| `IF(PARAM('i1', 'j2'), ... );`| `if g.param['i1', 'j2'].toDense(): ...` | Check for non-zero value of a parameter. |
| `A(R,P) $= B(R,P);` | `a[r,p].where[b[r,p]] = b[r,p]` | [Sparse Assignments](https://www.gams.com/latest/docs/UG_CondExpr.html#INDEX_assignment_22_sparse_21_assignments) `$=` will assign a value to the left-hand side of the ``=`` sign only if the right-hand side is nonzero. For long right hand sides, a `SparseExpr` helper variable should be used for readability.
| ``OPTION CLEAR = CNT;`` | ``cnt.setRecords(None)`` | Clearing standard parameter records in memory. |
| ``X = EPS$(NOT COND);`` | ``x[...] = Number(SpecialValues.EPS).where[~cond]`` | SpecialValues Filtering: Chaining an algebraic conditional `.where[]` onto a `SpecialValue` (`EPS`, `Inf`) requires casting it as an abstract numerical `gp.Number()`. |
| `OPTION A < B;` | `project(b, a)` or `aggregate(b, a)` | [Projection/Aggregation GAMS](https://www.gams.com/latest/docs/UG_OptionStatement.html#INDEX_projection) [``gp.project``](https://gamspy.readthedocs.io/en/latest/reference/gamspy.math.html#gamspy.math.project) [``gp.aggregate``](https://gamspy.readthedocs.io/en/latest/reference/gamspy.math.html#gamspy.math.aggregate)
| ``LOOP(<condition>, <expression>);`` | `with Loop(<condition>): <expression>` | [``gp.Loop``](https://gamspy.readthedocs.io/en/latest/reference/gamspy.Loop.html#gamspy.Loop) |
| `FOR(CNT = 1 TO CEIL(DFUNC), <expression>);` | `with For(cnt, start=1, end=ceil(dfunc)): <expression>` | [`gp.For`](https://gamspy.readthedocs.io/en/latest/reference/gamspy.For.html) |
| `IF(<condition>, <expression>);` | `with If(<condition>): <expression>` | [``g.If``](https://gamspy.readthedocs.io/en/latest/reference/gamspy.If.html#gamspy.If) |
| `IF(D GT 1, ... ELSE ...);` | `with If(d > 1): ... with Else(): ...` |  |
| `self.env.variable` | `self.env.variable_GP` | Read more [here](#4-migrating-compile-time-variables-to-gamspy). |

### 4. Migrating Compile-Time Variables to GAMSPy

Legacy GAMS compile-time string macros (variables accessed via ``self.env.variable_name``) need to ve moved into GAMSPy ready statements.

Consider the following `.add_gams_code()` you are about to translate:
```python
self.tc.add_gams_code(module=self, phase="init", code=f"Variable  VAR_UC(UC_N {self.env.sow}) Slacks for UC constraints;")
```

For most of the variables we need to maintain a `str` representation that all not yet translated `.add_gams_code` snippets can process and a GAMSPy version that can be used for translated parts.

`src/utils/config.py` lists all compile time variables. Check if there is already a GAMSPy ready translation with the suffix `_GP`.

- Case A (`sow_GP` exists): You can use `self.env.sow_GP` out of the box.
- Case B (only `sow` exists):
    1. Use the search to find all occurences for `sow` (`set_local("sow"`, `set_scoped("sow"`, `set_global("sow"`).
    2. Tighten the typing to match occurences for `sow`, e.g., change `sow: str` to `sow: Literal[',WW', ',WW,S']`.
    3. Add a GAMSPy version, e.g., `sow_GP`: tuple[Set | Alias, ...] .
    4. Add GAMSPy versions to every occurence, e.g., `self.set_[local, scoped, global]('sow_GP', (g.ww))` .
    5. Use `sow_GP` in you translation.


#### Step 5. Refactoring `batinclude` Arguments via Dataclass Processing

Instead of consuming `str` arguments of a `Class`, define a strongly typed ``Dataclass`` data schema container inside the module you are translating. This replaces anonymous positioning with explicit, self-documenting references and type hinting.

##### Define the Configuration Schema (``pp_lvlus_mod.py``)

```python
@dataclass
class PpLvlusConfig:
    """Strongly typed data contract replacing legacy positional batch-include loops."""
    arg1: Parameter
    arg2: tuple[Alias | Set, ...]
    arg3: Set
    arg4: tuple[str, ...] | tuple[()]
    arg5: tuple[Set, ...] | tuple[()]
    arg6: tuple[Set, ...] | tuple[()]
    arg7: Set
    arg8: Set
    arg9: Parameter | ImplicitParameter | int = 0
    arg10: tuple[Set, ...] | tuple[()] = ()
```

##### Consume the Properties via Splat Unpacking (``pp_lvlus_mod.py``)

Inside the processing unit constructor, ingest the configuration payload cleanly:

```python
def __init__(self, tc: TimesModelClass, env: CompileEnvironment, config: PpLvlusConfig):
        super().__init__(tc, env)
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self.compile()
```

##### Instantiate the Symbol Matrix in parent files

```python
# Ensure all arguments are typed as live, active GAMSPy symbols
        pp_lvlus_batincludes: list[PpLvlusConfig] = [
            PpLvlusConfig(
                uc_parameter=g.uc_act, arg2=(g.p,), arg3=g.PrcTs,
                arg4=('0', '0'), arg5=(), arg6=(), arg7=g.p, arg8=g.PrcTsl
            ),
            PpLvlusConfig(
                uc_parameter=g.uc_flo, arg2=(g.p, g.c), arg3=g.RpcsVar,
                arg4=('0',), arg5=(), arg6=(), arg7=g.p, arg8=g.PrcTsl,
                arg9=g.prc_sgl[g.r, g.p], arg10=(g.c,)
            ),
            PpLvlusConfig(
                uc_parameter=g.uc_ire, arg2=(g.p, g.c), arg3=g.PrcTs,
                arg4=(), arg5=(g.ie,), arg6=(), arg7=g.p, arg8=g.PrcTsl
            ),
            PpLvlusConfig(
                uc_parameter=g.uc_com, arg2=(g.c,), arg3=g.ComTs,
                arg4=(), arg5=(g.ucgrptype,), arg6=(g.comvar,), arg7=g.c, arg8=g.ComTsl
            ),
        ]

        # Pass the clean configuration payload directly to the child module block
        for config in pp_lvlus_batincludes:
            self.include(PpLvlusMod(tc=self.tc, env=self.env, config=config))
```

Here is the dedicated reference section covering domain tuple configuration rules for the contributor's guide.

---

##### Domain Parameter Rules: Multi-Element Tuples vs. Empty Tuples

When translating legacy GAMS text-replacement macros into native GAMSPy configurations, you must convert positional parameters into precise sequence types. Follow these two structural rules to determine how to format your configuration fields:

###### Rule A: Use `tuple[Alias | Set, ...]` for Active Coordinate Domains

If a GAMS macro parameter represents a comma-separated list of active indexing dimensions (e.g., `%2`/`self.arg2` passed as `"P"` or `"P,C"`), map it to a **tuple containing live GAMSPy `Set` or `Alias` symbols**.

* **Why:** This tells the static type checker that the field is an iterable collection of coordinate axes, allowing you to pass single-dimension arrays `(g.p,)` or multi-dimensional matrices `(g.p, g.c)` using a single, unified type signature.

###### Rule B: Use `tuple[()]` for Empty GAMS Domains (`""`)

If a domain is omitted or passed as a blank string (e.g., `%2`/`self.arg2` left as `""`), **always type-hint and initialize it as a strictly empty tuple `()**`.

* **Why:** In legacy GAMS, a blank string literal (`""`) simply evaluates to nothing during compilation text-pasting. In Python, you cannot pass an empty string primitive `""` into a GAMSPy index domain array without causing a structural syntax error. Representing an empty dimension as `tuple[()]` satisfies the type system while allowing safe structural unpacking.

---

##### Structural Mechanics: How Sequence Unpacking (`*`) Resolves Dimensions

By enforcing `tuple[()]` for empty text placements, you can build your mathematical index tracking loops using Python’s list unpacking operator (`*`). This guarantees that the dimensions are constructed dynamically at runtime without manual `if/else` array slicing.

```python
loop_domain = [ucn, *cc.arg6, side, r, t, *cc.arg2, s, *cc.arg5]
```

The table below illustrates how GAMSPy evaluates this structural unpacking line based on your type-hinted configurations:

| Configuration Context | Field Value | Evaluated Unpacking Output (`*field`) | Resulting Index Array Shape |
| --- | --- | --- | --- |
| **Active Domain (Rule A)** | `cc.arg2 = (g.p, g.c)` | `g.p, g.c` | Expands into two distinct, active coordinate axes inside the array. |
| **Single Axis Domain (Rule A)** | `cc.arg2 = (g.p,)` | `g.p` | Expands into a single active axis. |
| **Omitted GAMS String (Rule B)** | `cc.arg2 = ()` | *(Evaluates to absolutely nothing)* | The slot vanishes. The remaining axes shift forward seamlessly with no empty placeholders. |

##### Syntax Implementation Example

When defining your configuration structures, ensure the default values match these empty sequence contracts exactly:

```python
@dataclass
class PpLvlusConfig:
    arg1: Alias | Set                               # Active Domain: Always holds a single domain
    arg2: tuple[Alias | Set, ...]                   # Active Domain: Always holds symbol dimensions of variing length
    arg6: tuple[Alias | Set] | tuple[()]            # Optional Slot: Type-hinted to accept an empty tuple
    arg10: tuple[Alias | Set, ...] | tuple[()] = () # Optional Slot: Defaults to an empty tuple sequence

```

When instantiating a matrix row where a dimension must be suppressed, pass the empty sequence primitive cleanly:

```python
# Row 1: arg6 maps to an active symbol, arg10 is omitted and defaults to ()
PpLvlusConfig(uc_parameter=g.uc_com, arg2=(g.c,), arg3=g.ComTs, arg4=(), arg5=(g.ucgrptype,), arg6=(g.comvar,), arg7=g.c, arg8=g.ComTsl)

# Row 2: arg6 is completely empty to mimic an empty string in legacy GAMS
PpLvlusConfig(uc_parameter=g.uc_act, arg2=(g.p,), arg3=g.PrcTs, arg4=('0', '0'), arg5=(), arg6=(), arg7=g.p, arg8=g.PrcTsl)
```

---

### Using LARK

LARK is a great tool to automate some of the translation.

1. Copy a GAMS snippet into a file, e.g. `gams-lark/examples/times.py`.
2. Run `uv run run_transformer.py --times-renamer --renamer-config-file lark-config.json examples/times.gms > test.py`
3. Copy relevant parts from ``test.py`` into your TIMES project file.

In case you encounter an issue with LARK, create an issue in the LARK repository.

---

### Common Translation Pitfalls

#### Be Careful with Python Operator Precedence

This:

```python
with If(~ips[io] & f > 0):
```

is interpreted as:

```python
with If(((~ips[io]) & f) > 0):
```

not:

```python
with If((~ips[io]) & (f > 0)):
```

Always add parentheses explicitly when combining logical operators and comparisons:

```python
with If((~ips[io]) & (f > 0)):
```

---

#### `$=` Uses the RHS as the Condition

GAMS:

```gams
A(R,P) $= B(R,P);
```

can be translated as:

```python
a[r, p] = sparse(b[r, p])
```

The assignment only happens when the RHS is nonzero.

## Nested quotation

We previously used nested quotations to capture certain strings when translating GAMS code to Python (for example, `arg1="'1'"`). However, it is now necessary to update these to standard quotations, such as `arg1="1"`. This rule should apply to most cases.

## Naming conventions

**Python variable names** are chosen for readability, while **GAMS symbol names are preserved**.

- **Sets**: `lowercase`
- **Subsets**: `PascalCase`
- **Parameters**: `snake_case`
- **Variables**: `ALL_CAPS`

Rules:
- Keep the legacy GAMS name as the GAMSPy symbol `name="..."`.
- Use a **descriptive Python attribute/variable name** for the symbol handle (e.g., `tc.all_year = Set(m, name="ALLYEAR", ...)`).



## Verification & Testing

### Compile-Time States: Verifying Variable Checkpoints
We ensure our Python `CompileEnvironment` accurately tracks macro changes by comparing states.
1. **GAMS**: Add `display "checkpoint_id"; $show` to the `.gms` file.
2. **GAMSPy**: Call `tc.save_test_state(env=self.env, checkpoint="checkpoint_id")` if `tc.test_run` is true.
3. **Tests**: Add `"checkpoint_id"` to `test_compile_time_variable_state.py`.

### GDX Diff: Verifying Compile and Execution States
Our test suite uses a module-scoped `pytest` fixture to run the heavy model generation once, and then evaluates the compile-time and execution-time states as distinct tests. This provides granular feedback.

#### How to Synchronize Code for Testing
1. **Halt GAMS**: Add `$gdxUnload %COMPILE_GDX%`, `execute_unload "%EXECUTE_GDX%";`, and `$stop` to the `.gms` file where your translated segment ends.
2. **Halt Python**: Insert an early `raise EscapeStack()` statement right after the module you are currently translating inside its parent file to prevent downstream logic from generating unverified AST.

Run the tests using:
```bash
pytest tests/
```
If compile matches but execution differs, `pytest` will independently pass the compile test and fail the execution test, allowing you to isolate AST generation errors quickly.

---

## Definition of Done (DoD)

- [ ] Module follows the 1:1 naming (e.g., `initsys.mod` -> `initsys_mod.py`).
- [ ] All `$IF` / `$IFI` logic is correctly mapped to Python `if` statements.
- [ ] GAMS logic is cleanly separated into `init` and `run` phases to prevent Error 349.
- [ ] All checkpoints match GAMS `.lst` output exactly.
- [ ] `pre-commit run --all-files` passes locally.
- [ ] `pytest` integration and GDX diff tests pass.
- [ ] Merge Request opened against the `develop` branch.
- [ ] Assign @rschuchmann or @jbroihan as reviewer.

## How to Run manually

### Run GAMS
`gams TIMES_source/model/demo12.run idir1=TIMES_source/source idir2=TIMES_source/model Filecase=4`

### Run GAMSPy
`python src/main.py`


---

# Appendix from Phase 1
## The Core Workflow

GAMS separates **Compile-time** (macros/setglobals) from **Execution-time** (assignments/solves). We replicate this using the following pattern:

### A. Forking the Environment
Every module must isolate its local variables. Always fork the passed `env` in the `__init__` method.

```python
def __init__(self, tc, env, arg1=None):
    # Forking ensures $SETLOCAL doesn't leak back to parents
    self.env = env.fork()
    self.tc = tc
    self.arg1 = arg1
    self.compile()
```

### B. Capturing Variables (The Snapshot)
Because Python executes linearly, you must "freeze" the value of a compile-time variable *before* sending it to a deferred task.

```python
def compile(self):
    # 1. Capture the current state of the GAMS macro
    current_val = self.env.botime

    # 2. Enqueue the logic with the frozen value
    tc.enqueue(self.assign_logic, val=current_val)
```

### C. Enqueuing - Deferred Execution
Logic inside enqueued methods will run only after the full model structure is built.

```python
def assign_logic(self, val):
    # Use the captured 'val', not the live 'self.env.botime'
    self.tc.add_gams_code(module=self, phase="run", code=f"Parameter p; p = {val};")
```

---

## Special Concepts & GAMS Quirks

### Lowercase Environment Variables

When setting or accessing environment variables (macros) via the `env` object, always use **lowercase names**. Additionally, because GAMS evaluates macros as text replacements, you must format all assigned values as **strings**, even if they represent numerical data.

```python
# Correct: Lowercase variable name, string value
self.env.set_global("abc", "5")

# Accessing the variable using lowercase
print(self.env.abc)  # Outputs: '5'
```

### Control Flow: `$label` and `$goto`

TIMES relies heavily on archaic `$goto` statements. Since Python does not support `goto`, we replicate this behavior using conditional method dispatching based on `self.arg1`.

**Best Practice**: Always name your routing methods `_label_[name]` to make it instantly obvious which GAMS `$label` they correspond to.

#### Handling Label Fall-Through (No `$exit`)

In GAMS, if a `$label` block ends *without* an explicit `$exit` or `$goto` statement, the compiler naturally continues reading line-by-line, "falling through" into the next `$label` block.

Because we translate these blocks into isolated Python methods, **Python will not automatically fall through to the next method**. You must explicitly call the next label method at the end of your current method to replicate this behavior.

**Legacy GAMS:**
```gams
$LABEL BLOCK_A
* Do something
* Notice there is no $EXIT here! Execution falls through to BLOCK_B.

$LABEL BLOCK_B
* Do something else
$EXIT
```

**Python Translation:**
```python
def compile(self, tc: "TimesModelClass") -> None:
    if self.arg1 == "BLOCK_A":
        self._label_block_a(tc)
    elif self.arg1 == "BLOCK_B":
        self._label_block_b(tc)

def _label_block_a(self, tc):
    # [Translate BLOCK_A logic here]

    # CRITICAL: Replicate GAMS fall-through by explicitly calling the next block
    self._label_block_b(tc)

def _label_block_b(self, tc):
    # [Translate BLOCK_B logic here]
    pass
```

### Conditionals: `$IF` vs. `$IFI`
- `$IF` is strictly **case-sensitive** (`if self.env.dsc == "YES":`).
- `$IFI` is **case-insensitive** (`if self.env.dsc.upper() == "YES":`).
*Note: Never normalize GAMS variables to Python booleans (`True`/`False`). Always maintain the string values exactly as they are assigned in TIMES.*

### GAMS Phase Rules
GAMS strictly separates **compile-time declarations** (`Set`, `Parameter`, `Variable`) from **execution-time statements** (`IF`, `LOOP`, `=`).
Always pass the correct `phase` argument to `add_gams_code`:
* `phase="init"`: Corresponds to compile time. Will be executed immediately.
* `phase="run"`: Corresponds to execution time. All code needs to be enqueued.



---

## Translation Cheat Sheet

| GAMS | Python Equivalent | Purpose |
| :--- | :--- | :--- |
| `$include file.gms` | `self.include(FileGms(tc, self.env))` | Direct include |
| `$batinclude file.gms "A"` | `self.include(FileGms(tc, self.env, arg1="A"))` | Include with arguments |
| `$setlocal VAR 10` | `self.env.set_local("var", "10")` | File-local variable |
| `$set VAR 10` | `self.env.set_scoped("var", "10")` | File-scoped variable |
| `$setglobal VAR 10` | `self.env.set_global("var", "10")` | System-wide variable |
| `$if %VAR% == YES` | `if self.env.var == "YES":` | **Case-sensitive** check |
| `$ifi %VAR% == YES` | `if self.env.var.upper() == "YES":` | **Case-insensitive** check |
| `$if declared PARAM` | `if 'PARAM' in tc.container.listSymbols()` | Declared check |
| `$if defined PARAM` | `if self.tc.defined('PARAM'):` | Defined check |
