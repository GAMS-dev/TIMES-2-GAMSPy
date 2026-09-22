# config.py
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from gamspy import Alias, Domain, Expression, Number, Set, Sum
from gamspy._algebra.condition import Condition
from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet
from gamspy.math import MathOp
from pydantic import BaseModel, ConfigDict, Field


class EnvironmentVariableSchema(BaseModel):
    """Defines strict types and documentation for TIMES compile-time environment variables."""

    model_config = {"arbitrary_types_allowed": True}

    # Core Identifiers
    run_name: str = Field(
        description="Gives a name to the model run, which will be used when generating various output files."
    )

    # Extensions
    abs: Literal["YES", "NO"] = Field(
        description="Option to use the Ancillary Balancing Services extension."
    )
    ier: Literal["YES", "NO"] = Field(
        description="Activates the IER (Institute for the Rational Use of Energy) CHP/market-share extension. Unlike most extensions, TIMES has no %IER%==YES switch for it -- it is passed positionally as `IER` to initmty.mod's BATINCLUDE."
    )
    chp_mode: Literal["YES", "NO"] = Field(
        description="Within the IER extension, activates extraction-condensing CHP handling (pp_chp.ier, eqchpelc.ier, rpt_chp.ier)."
    )
    abs_GP: Number = Field(
        description="Option to use the Ancillary Balancing Services extension."
    )
    cli: Literal["YES", "NO", "%cli%"] = Field(
        description="Activates the Climate Module to estimate atmospheric CO2 concentrations, changes in radiative forcing, and induced global mean surface temperature changes."
    )
    duc: Literal["YES", "NO"] = Field(
        description="Option to use the discrete (lumpy) unit commitment formulation."
    )
    etl: Literal["YES", "NO"] = Field(
        description="Option to use endogenous technology learning formulation. Alters the solve statement to Mixed-Integer Programming (MIP)."
    )
    micro: Literal["YES", "NO"] = Field(
        description="Option to use the non-linear elastic demand formulation."
    )
    retire: Literal["YES", "NO"] = Field(
        description="Enables early and lumpy retirements of process capacities. Valid values: NO (Disabled), LP (Continuous), MIP/YES (Lumpy/Discrete via PRC_RCAP/RCAP_BND)."
    )
    vda: Literal["YES", "%vda%"] = Field(
        description="Enables the Vintage Data Aggregation (VDA) pre-processor extension of TIMES."
    )
    vintopt: Literal["1", "2", "%vintopt%"] = Field(
        default="%vintopt%",
        description="Vintage-weighting option. 1: weight vintaged-attribute tables by PASTSUM (fillvint.gms fill branch). 2: additionally populates PRC_SIMV from PRC_VINT (excluding STG processes), activating vintage-simulation (coef_csv.mod/eqcapvac.mod).",
    )
    dsc: Literal["YES", "NO"] = Field(
        description="Option to use the discrete/lumpy investment formulation, automatically altering the solver execution statement to MIP."
    )

    # Objective Function Formulation
    obj: Literal["ALT", "MOD", "LIN", "STD", "AUTO"] = Field(
        default="AUTO",
        description="Objective function formulation selector. STD (Standard), ALT (Independent tracking), MOD (Flexible milestone midpoints), LIN (Linear evolution), or AUTO (Automatic selection based on B and E periods).",
    )
    mid_year: Literal["YES", "%mid_year%"] = Field(
        description="Enables mid-year discounting as a compromise between beginning-of-year (CRF underestimation) and end-of-year discounting."
    )
    oblong: Literal["YES", "NO", "%oblong%"] = Field(
        description="Synchronizes all capacity-related costs with process activities to eliminate cost-accounting distortions and small salvaging problems found in STD and MOD formulations."
    )
    damage: Literal["LP", "NLP", "NO"] = Field(
        default="LP",
        description="Inclusion mode for damage costs in the objective function: LP (Linearized default), NLP (Non-linear functions), or NO (Excluded from objective, reporting only).",
    )
    objann: Literal["YES", "NO"] = Field(
        description="Requests a period-wise objective formulation, useful for iterative updates of period-wise discount factors (e.g., in MACRO MSA decomposition)."
    )
    discshift: float = Field(
        description="Generalization of time-of-year discounting. Shifts payment streams forward in years relative to operation (e.g., 0.5 equals MID_YEAR, 1.0 equals end-of-year)."
    )
    varcost: Literal["LIN", "NO", "%varcost%"] = Field(
        description="Controls dense cost interpolation. LIN advises TIMES to derive intermediate values 'on the fly' via piecewise linear interpolation to conserve GAMS working memory."
    )

    # Stochastic and Sensitivity Analysis Controls
    sensis: Literal["YES", "NO"] = Field(
        description="Enables automatic warm-start optimization tracking facilities via GAMS BRATIO adjustments across successive sensitivity run cases."
    )
    spines: Literal["YES", "NO"] = Field(
        description="Activates stochastic mode while setting the SOW index inactive for capacity-related investment variables to find optimal strategies under recurring uncertainties."
    )
    stages: Literal["YES", "Yes", "yes", "NO", "%stages%"] = Field(
        description="Activates multi-stage stochastic programming features for sensitivity, uncertainty hedging, and tradeoff analysis."
    )

    # Equilibrium Mode Controls
    timesed: Literal["YES", "NO", "0", "%timesed%"] = Field(
        description="Activates full partial equilibrium features, employing elastic demands in the TIMES solution matrix."
    )
    macro: Literal["YES", "Yes", "MLF", "MSA", "CSA", "N", "%macro%"] = Field(
        description="Activates General Equilibrium mode. YES (Standard MACRO), MSA (Decomposition algorithm), MLF (Linearized formulation), or N (Disabled)."
    )

    # Step-Wise Foresight Options
    timestep: int = Field(
        description="Specifies the number of years optimized per step when running the model sequentially under limited foresight conditions."
    )
    fixboh: int | Literal["%fixboh%"] = Field(
        description="Binds the initial years of a run up to a specified milestone year to solution levels extracted from a prior optimization checkpoint."
    )

    # Debugging and Verification Controls
    debug: Literal["YES", "NO"] = Field(
        default="NO",
        description="Requests a dense dump of all user and system data structures into external files and enables extended compilation quality assurance checks.",
    )
    dumpsol: Literal["YES", "NO"] = Field(
        default="NO",
        description="Dumps out levels and marginals of specific tracking variables (VAR_NCAP, VAR_CAP, etc.) into an isolated plaintext file.",
    )
    solve_now: Literal["YES", "NO"] = Field(
        default="YES",
        description="Controls execution. If set to NO, the engine validates compilation syntax and data bindings but aborts before calling the optimization solver.",
    )
    xtqa: Literal["YES", "NO", "%xtqa%"] = Field(
        description="Triggers advanced technical quality assurance checking parameters across the data compiling matrix."
    )

    # Solution Reporting Customization
    anncost: Literal["LEV", "%anncost%"] = Field(
        description="Requests annualized levelized average reporting values across process lifetimes, capturing all intra-period expenditures to reconstruct total NPV."
    )
    bencost: Literal["YES", "NO", "%bencost%"] = Field(
        description="Enables basic cost-benefit evaluation reporting output tracking for newly introduced technologies."
    )
    rpt_flots: Literal["COM", "ANNUAL", "%rpt_flots%"] = Field(
        description="Restricts timeslice detail for flow levels reporting: COM (Commodity timeslices), ANNUAL (Aggregated annually to save space), or default variable settings."
    )
    solveda: Literal["YES", "1", "NO", "0", "%solveda%"] = Field(
        description="Formats and prepares output parameter blocks explicitly optimized for VEDA-BE data ingestion schemas."
    )

    # Core Macro String Tokens
    r_t: str = Field(
        description="Tracking string substitution index layer representing the baseline active multi-region mapping node."
    )
    r_t_GP: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet] = Field(
        description="Tracking string substitution index layer representing the baseline active multi-region mapping node."
    )

    # Miscellaneous Utility Handles
    validate_: Literal["NO", "%validate%"] = Field(
        default="%validate%",
        alias="validate",
        description="Requests a highly simplified objective function block emulating historical MARKAL configurations (Discouraged).",
    )
    reduce: Literal["YES", "NO", "%reduce%"] = Field(
        description="Toggles equation reduction algorithms. Substitutes emission flows and purges redundant capacity variables to clear working memory."
    )
    solans: Literal["YES", "NO"] = Field(
        default="NO",
        description="Produces specific data solution structures pre-formatted for direct import into the ANSWER shell engine.",
    )
    err_abort: Literal["YES", "NO"] = Field(
        default="YES",
        description="Toggles execution limits, forcing a hard compilation abort if initialization errors are flagged.",
    )
    gams_cgi: Literal["NO", "WWW"] = Field(
        default="NO",
        description="Specifies if execution pathways route via a web interface or a standard desktop process call.",
    )
    model_name: str = Field(
        default="TIMES",
        description="Identifies the core structural name string injected into the model tracking parameters.",
    )
    var_uc: Literal["YES", "", "%var_uc%"] = Field(
        description="Forces explicit tracking variables for user constraints by introducing equality slacks, which is highly useful for stochastic ranges."
    )
    dscauto: Literal["YES", "Yes", "%dscauto%"] = Field(
        description="Automated structural flag managing fallback parameters for discrete (lumpy) execution parameters."
    )
    datagdx: Literal["YES", "%datagdx%"] = Field(
        description="Dumps the entire input data space straight into an archived, dated GDX verification file."
    )
    botime: int = Field(
        default=1980,
        description="Beginning of Time marker. Establishes the absolute oldest baseline data tracking interval boundaries permitted.",
    )
    eotime: int = Field(
        default=2200,
        description="End of Time marker. Establishes the furthest technical tracking boundary for lifetimes, cycles, and constraints.",
    )
    vedavdd: Literal["YES", "%vedavdd%"] = Field(
        description="Toggles structural mapping formatting extensions needed for advanced VEDA visualization reporting blocks."
    )

    # Dynamic String Mapping Properties
    method: str = Field(
        description="Dynamic parameter mapping string tracking solution execution steps."
    )
    mixlp: str = Field(
        description="Solver control parameters for Mixed-Integer Linear Programming overrides."
    )
    nonlp: str = Field(
        description="Solver directive parameters for Non-Linear Programming solution paths."
    )
    ext: str = Field(
        description="String variable containing file extension tracking pathways."
    )
    load: str = Field(
        description="Dynamic file path targeting external point data restoration files."
    )
    pnt1: str = Field(
        description="First checkpoint identifier string mapped inside savepoint routines."
    )
    pnt2: str = Field(
        description="Second checkpoint identifier string mapped inside savepoint routines."
    )
    capon: str = Field(
        description="Conditional capacity assignment switch parameter tracked as text tokens."
    )
    capon_GP: Expression | Condition = Field(
        description="Conditional capacity assignment switch parameter tracked as text tokens."
    )
    mx: str = Field(
        description="Macro tracking name string identifier mapping specialized model equations."
    )
    mx_GP: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()] = (
        Field(
            description="Macro tracking name string identifier mapping specialized model equations."
        )
    )
    path: str = Field(
        description="Absolute system directory path targeting core operational include subroutines."
    )
    obmac: str = Field(
        description="Binary execution toggle string tracking whether GAMS macro blocks are globally compiled."
    )
    src: str = Field(
        description="Source data location lookup parameters tracking raw dictionary inputs."
    )
    shp1: str | Expression = Field(
        description="Dynamic load shape mapping variable utilized for seasonal load curves."
    )
    shg: str | Sequence[Set | Alias | str] = Field(
        description="Text replacement parameter mapping the baseline global optimization coordinates."
    )
    upscap0: str = Field(
        description="Initial capability update tracking parameter handling historical baseline records."
    )
    upscap0_GP: Condition = Field(
        description="Initial capability update tracking parameter handling historical baseline records."
    )
    vas: str = Field(
        description="Variable assignment tracking string mapping structural matrix parameters."
    )
    hs: str = Field(description="Historical scaling parameter tracking data limits.")
    sigo: str = Field(
        description="Output tracking switch handling environmental constraint emissions parameters."
    )
    sigi: str = Field(
        description="Input tracking switch handling environmental constraint emissions parameters."
    )
    ired: str = Field(
        description="Inter-regional exchange directionality assignment parameter tracking string."
    )
    take: str = Field(
        description="Conditional logic expression token indicating active filtering axes."
    )
    regy: str = Field(
        description="Regional execution context indicator string tracking geographic bounds."
    )
    awgt: str = Field(
        description="Annual aggregation weight parameter token mapped to process lifecycles."
    )
    iwgt: str = Field(
        description="Investment optimization weight parameter token mapped to capital costs."
    )
    ts: str = Field(
        description="Target time-slice identifier token tracking operational sub-annual intervals."
    )
    swt: str = Field(
        description="Dynamic switch template tracker managing temporary loop attributes."
    )
    swt_GP: tuple[Set | Alias | ImplicitSet, ...] | tuple[()] = Field(
        description="Dynamic switch template tracker managing temporary loop attributes."
    )
    swsw: str = Field(
        description="Nested operational matrix state control flag identifier."
    )
    swsw_GP: (
        tuple[Set | Alias | ImplicitSet, ...]
        | tuple[ImplicitSet, ImplicitParameter]
        | tuple[()]
    ) = Field(
        description="Nested operational matrix state control flag identifier. The second entry, when given, weights the summand with the state probability."
    )
    swtd: str = Field(
        description="Time-step differentiation switch expression string mapped to parameters."
    )
    swtd_GP: (
        tuple[Set | Alias | ImplicitSet, ...]
        | tuple[ImplicitSet, ImplicitParameter]
        | tuple[()]
        | str
    ) = Field(
        description="Time-step differentiation switch expression string mapped to"
        " parameters. A 2-tuple (domain, weight) form is used when the summand"
        " needs weighting by the state probability (the scum=='1' case)."
    )
    x1: str = Field(
        description="First arbitrary evaluation coordinate mapping temporary data values."
    )
    x2: str = Field(
        description="Second arbitrary evaluation coordinate mapping temporary data values."
    )
    zhalf: str = Field(
        description="Discount factor lookback coefficient string mapping half-period parameters."
    )
    zhalf_GP: MathOp = Field(
        description="Discount factor lookback coefficient expression mapping half-period parameters."
    )
    pass_: Expression | None = Field(
        alias="pass",
        description="Execution tracking code handling iterative loop counts.",
    )
    tpulse: str = Field(
        description="Pulse duration coefficient parameter mapping load peak curves."
    )
    tpulse_GP: tuple[Condition | Domain, Expression | ImplicitParameter | Number] = (
        Field(
            description="tpulse is always a tuple with format <(sum domain, multiplier of the summand)>."
        )
    )
    capwd: str = Field(
        description="Capacity width adjustment parameter string mapping operating lifetimes."
    )
    capwd_GP: ImplicitParameter | Number = Field(
        description="Capacity width adjustment factor mapping operating lifetimes."
    )
    sow: Literal["", ",SOW", ",WW", ",WW)", ",0", ",'0'", "1", "SOW.TL"] = Field(
        description="Stochastic World (Scenario State) active indexing identifier token."
    )
    sow_GP: tuple[Literal["0", "1"] | Set | Alias] | tuple[()] = Field(
        description="Stochastic World (Scenario State) active indexing identifier token."
    )
    sowtmp: str = Field(
        description="Temporary scenario tracking storage token utilized in nested loop blocks."
    )
    sowtmpend: str = Field(
        description="Terminal scenario tracking validation token used within multi-stage loops."
    )
    spoint: Literal["1", "2", "3", ""] = Field(
        description="Flag to generate a savepoint file."
    )
    data: str = Field(
        description="Input source folder directive tracking raw execution arrays."
    )
    tail: str = Field(
        description="Appended text token tracking dynamic reporting file suffixes."
    )
    def_: str = Field(
        alias="def", description="Structural constraint template definition variable."
    )
    sharetol: str = Field(
        description="Tolerance limits governing mathematical group allocation constraints."
    )
    var: str = Field(
        description="Primary model variable name indicator mapped to global execution structures."
    )
    var_GP: tuple[str, Any] | str = Field(
        description="Primary model variable name indicator mapped to global execution structures."
    )  # NOTE: Is required at equserco_mod.py:347
    varm: str = Field(
        description="Macro tracking variant variable used in objective calculation hooks."
    )
    varm_GP: tuple[str, ImplicitSet | None] = Field(
        description="varm is always a tuple with format <(variable prefix, set identifier for sum statement)>."
    )
    vart: str = Field(
        description="Temporal indexing mapping string tracking current variable periods."
    )
    vart_GP: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None] = (
        Field(
            description="vart is always a 2-tuple <(variable prefix, domain)>. The"
            " domain is either a plain set/condition for wrap_in_sum, or itself a"
            " (condition, weight) pair so wrap_in_sum multiplies in the SW_TPROB"
            " state-probability weight (the scum=='1' aggregated case)."
        )
    )
    vartt: str = Field(
        description="Nested temporal index mapping string tracking cumulative variable horizons."
    )
    vartt_GP: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None] = (
        Field(
            description="vartt is always a 2-tuple <(variable prefix, domain)>. The"
            " domain is either a plain set/condition for wrap_in_sum, or itself a"
            " (condition, weight) pair so wrap_in_sum multiplies in the SW_TPROB"
            " state-probability weight (the solveda=='1' aggregated case)."
        )
    )
    varv: str = Field(
        description="Vintage index mapping identifier tracking installed configuration years."
    )
    varv_GP: tuple[str, ImplicitSet | None] = Field(
        description="varv is always a tuple with format <(variable prefix, set identifier for sum statement)>."
    )
    cal_red: str = Field(
        description="Calculation reduction parameter mapping tracking array dimensions."
    )
    eq: Literal["EQ", "ES", "Q"] = Field(
        description="Equation declaration mapping identifier string."
    )
    sws: str = Field(
        description="Scenario switch tracking token handling multi-stage matrix settings."
    )
    sws_GP: tuple[Set | Alias | ImplicitSet, ...] | tuple[()] = Field(
        description="Scenario switch tracking token handling multi-stage matrix settings."
    )
    swstmp: str = Field(
        description="Temporary matrix scenario tracker state parameter."
    )
    swstmp_GP: tuple[Set | Alias, ...] | tuple[()] = Field(
        description="Temporary copy of the stochastic world index tuple."
    )
    swd: Literal["", ",WW", ",W", ",SOW", ")"] = Field(
        description="Solution domain tracking token mapped to variable dimensions."
    )
    swd_GP: tuple[Set | Alias] | tuple[()] = Field(
        description="Solution domain tracking token mapped to variable dimensions."
    )
    sw1: str = Field(
        description="Primary configuration flag used in file inclusion loops."
    )
    sw1_GP: tuple[Set | Alias | str | Literal[1]] | tuple[()] | str = Field(
        description="Primary configuration flag used in file inclusion loops."
    )
    sw2: str = Field(
        description="Secondary configuration flag used in file inclusion loops."
    )
    sw2_GP: tuple[str, Set] | tuple[Set | Alias] | tuple[()] = Field(
        description="Secondary configuration flag used in file inclusion loops."
    )
    uclim: str = Field(
        description="User constraint upper boundary mapping identifier token."
    )
    bext: str = Field(
        description="Backward extrapolation validation logic string mapping cost parameters."
    )
    fext: str = Field(
        description="Forward extrapolation validation logic string mapping cost parameters."
    )
    iled: str = Field(
        description="Investment lag lead index variable tracking installation steps."
    )
    iled_GP: bool = Field(
        description="Investment lag lead index variable tracking installation steps."
    )
    linflo: str = Field(
        description="Linear flow constraint tracking property mapped as text."
    )
    linacc: str = Field(
        description="Linear accumulation constraint tracking property mapped as text."
    )
    item: str = Field(
        description="Data record tracker string matching internal GDX files."
    )
    add: str = Field(
        description="Dynamic array extension command parameter tracked as text tokens."
    )
    opt: str = Field(
        description="GAMS optimization compiler configuration option string identifier."
    )
    ll: str = Field(
        description="Loop tracking calendar year index array reference code."
    )
    def_iebd: int = Field(
        description="Boundary conditions definition tracker managing baseline imports and exports."
    )
    extend: str = Field(
        description="Horizons extension directive switch tracked as string primitives."
    )
    msa: str = Field(
        description="Macro Stand-Alone sub-mode, derived from MACRO ('CSA' or the literal MACRO value) inside preppm.msa."
    )
    istep: str = Field(
        description="Iteration step count tracking identifier tracking multi-foresight steps."
    )
    istep_GP: MathOp | ImplicitParameter = Field(
        description="Iteration step count expression tracking multi-foresight steps."
    )
    capjd: str = Field(
        description="Technical capacity retirement degradation tracking marker."
    )
    capjd_GP: ImplicitParameter | Number = Field(
        description="Technical capacity retirement degradation tracking marker."
    )
    cufscal: int = Field(
        description="Capacity utilization factors scaling parameters modifier parameter."
    )
    cucscal: int = Field(
        description="Capacity optimization cost scaling factors modifier parameter."
    )
    semicont: str = Field(
        description="Semi-continuous limits tracking property mapped to variables."
    )
    reset: int = Field(
        description="System state cleanup parameter tracking uninitialized sets."
    )
    mip: str = Field(
        description="Mixed-Integer Programming active execution framework parameter text token."
    )
    tst: str = Field(
        description="Target time-slice testing configuration parameters identifier."
    )
    tst_GP: tuple[Condition | ImplicitSet, ...] = Field(
        description="GAMSPy counterpart of tst: a snapshot of the TSUM domain"
        " taken before a later branch (e.g. STAGES=='YES') overwrites it."
    )
    varmac: str = Field(
        description="Macro expansion variable configuration property indicator."
    )

    tx: str = Field(
        description="Temporal calculation index identifier utilized in subset configurations."
    )
    tx_GP: tuple[Set | Alias | ImplicitSet, ...] = Field(
        description="Temporal calculation index identifier utilized in subset configurations."
    )
    tsum: str = Field(
        description="Summary execution check identifier tracking mathematical summation steps."
    )
    rtpx: str = Field(
        description="Regional time process indexing axis identifier mapping configurations."
    )
    sw_tags: str = Field(
        description="Active tags configuration switch mapping parameter values."
    )
    sw_notags: str = Field(
        description="Deactivated tags configuration switch mapping parameter values."
    )
    r_v_t: str = Field(
        description="Region, Vintage, Time tracking parameter tracking block."
    )
    r_v_t_GP: tuple[Set | Alias | ImplicitSet, ...] = Field(
        description="Region, Vintage, Time tracking parameter tracking block."
    )
    pgprim: str = Field(
        description="Primary generation fuel tracking parameter identifier string."
    )
    declif: str = Field(
        description="Decommissioning lifetime adjustment parameter tracking array values."
    )
    invlif: str = Field(
        description="Investment active lifecycle tracking array parameter."
    )
    gtime: str = Field(description="System generation timestamp variable indicator.")
    gdate: str = Field(
        description="System generation calendar date variable indicator."
    )
    ctst: Literal["", "**EPS", "**0", "1"] = Field(
        description="Calculation time step parameter used inside optimization updates."
    )
    rts: Callable[[str], str] = Field(
        description="Regional sub-annual tracking parameter handling seasonal loads."
    )
    rts_GP: Callable[[Set | Alias], Set | Alias | Expression] = Field(
        description="Regional sub-annual tracking parameter handling seasonal loads."
    )
    rcapsub: str = Field(
        description="Capacity allocation sub-region configuration tracking parameters."
    )
    rcapsub_GP: Expression | Number = Field(
        description="Capacity allocation sub-region configuration tracking parameters."
    )
    rcapsbm: str = Field(
        description="Capacity allocation sub-region optimization model variables."
    )
    rcapsbm_GP: Expression | Condition | Number = Field(
        description="Capacity allocation sub-region optimization model variables."
    )
    swx: str = Field(
        description="Primary structural execution switch template mapping parameters."
    )
    swx_GP: tuple[Literal["1"] | Set | Alias] | tuple[()] = Field(
        description="Primary structural execution switch template mapping parameters."
    )
    swtx: str = Field(
        description="Secondary structural execution switch template mapping parameters."
    )
    swtx_GP: Number | ImplicitSet = Field(
        description="Secondary structural execution switch template mapping parameters."
    )
    sw_stvars: str = Field(
        description="Stochastic step evaluation parameters active variable indicator."
    )
    vsum: str = Field(
        description="SPINES stochastic summation prefix text fragment used to build SW_STVARS set definitions."
    )
    scum: str = Field(
        description="Cumulative scaling parameters check array parameter tracking strings."
    )
    scum_GP: ImplicitParameter | Number = Field(
        description="Cumulative scaling parameters check array parameter tracking strings."
    )
    ControlAbort: str = Field(
        description="System termination signal parameter matching execution logs."
    )
    cl: str = Field(description="Commodity constraint definition identifier string.")
    pl: str = Field(description="Process constraint definition identifier string.")
    rl: str = Field(description="Regional constraint definition identifier string.")
    rpoint: str = Field(
        description="Replicates a previous solution directly from a GDX reference save point without re-running the solver."
    )
    dflbl: str = Field(
        description="Default data file label mapping parameter suffix identifiers."
    )
    gdxpath: str = Field(
        description="Absolute file path targeting the destination GDX binary folder."
    )
    gdx_irebnd: str = Field(
        description="Base name (without .gdx) of a previous run's GDX, found under %GDXPATH%, to load exogenous IRE trade bounds (PREMILE/PAR_IRE) from."
    )
    gdx_ipric: str = Field(
        description="Base name (without .gdx) of a previous run's GDX, found under %GDXPATH%, to load exogenous IRE trade prices (PREMILE/PAR_IPRIC) from."
    )
    sysprefix: str = Field(
        description="Operating system directory architecture execution prefix string."
    )
    prf: str = Field(
        description="Profiler log destination file pathway string parameters."
    )
    g2x6: str = Field(
        description="System configuration formatting translator extension tracking parameter."
    )
    tmp: str = Field(
        description="Universal temporary string parameter utilized across structural loops."
    )
    tmp_GP: Expression | int = Field(
        default=1,
        description="GAMSPy counterpart of tmp where it carries a multiplier, e.g. the levelization factor 1/OBJ_PVT of cost_ann.rpt.",
    )
    sic: str = Field(
        default="1",
        description="Stochastic investment cost scaling term of cost_ann.rpt, either 1 or 1+PASTSUM(R,V,P).",
    )
    sic_GP: Expression | int = Field(
        default=1,
        description="GAMSPy counterpart of sic.",
    )
    maxsow: str = Field(
        description="Limits the maximum number of active Stochastic Worlds tracked in a single scenario run."
    )
    solmip: str = Field(
        description="Prepares the solution reporting values for Mixed-Integer Programming (MIP) parameters that are to be imported into the VEDA-BE results database manager, specifically tracking discrete choices like lumpy investments (DSC) and endogenous learning (ETL)."
    )

    # GAMS Savepoint / Loadpoint Controls
    sponint: Literal["1", "2", "3", "%sponint%"] = Field(
        description="GAMS savepoint frequency interval control variable."
    )
    lpoint: str = Field(
        description="GAMS control variable used to pass the scenario reference path for loadpoint features."
    )

    no_emty: str = Field(
        default="%no_emty%",
        description="Suppresses dump headers when a row is empty; passed to dumpsol.mod as %2.",
    )
    item2: str = "%item2%"  # solputta_ans.py -- secondary ITEM loop token
    flots: str = "%flots%"  # solputta_ans.py -- flow-level report selector
    supzero: str = "%supzero%"  # solputta_ans.py -- zero-supply handling

    swo: str
    send: str
    swts: str
    cpar: str
    powerflo: str
    pdtol: str
    bigm: str
    ireauxbal: str
    rpt_opt: pd.DataFrame
    stepped: str
    peakchp: str
    need: str
    witspine: bool
    ewispine: bool
    stg: str
    ix: str
    eqs: str
    v: str
    r_w_t: str


class UserConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    validate_: Literal["NO", "%validate%"] = Field(
        default="%validate%", alias="validate"
    )
    reduce: Literal["YES", "%reduce%"] = "%reduce%"
    vda: Literal["YES", "%vda%"] = "%vda%"
    vintopt: Literal["1", "2", "%vintopt%"] = "%vintopt%"
    debug: Literal["YES", "NO"] = "NO"
    dumpsol: Literal["YES", "NO"] = "NO"
    solans: Literal["YES", "NO"] = "NO"
    ier: Literal["YES", "NO"] = "NO"
    chp_mode: Literal["YES", "NO"] = "NO"
    abs: Literal["YES", "NO"] = "NO"
    err_abort: Literal["YES", "NO"] = "YES"
    gams_cgi: Literal["NO", "WWW"] = "NO"
    solve_now: Literal["YES", "NO"] = "YES"
    model_name: str = "TIMES"
    xtqa: Literal["YES", "%xtqa%"] = "%xtqa%"
    var_uc: Literal["YES", "", "%var_uc%"] = "%var_uc%"
    obj: Literal["ALT", "MOD", "LIN", "STD", "AUTO"] = "AUTO"
    mid_year: Literal["YES", "%mid_year%"] = "%mid_year%"
    oblong: Literal["YES", "NO", "%oblong%"] = "%oblong%"
    objann: Literal["YES", "NO", "%objann%"] = "%objann%"
    damage: Literal["LP", "NLP", "NO"] = "LP"
    stages: Literal["YES", "Yes", "NO", "%stages%"] = "%stages%"
    sensis: Literal["YES", "NO", "%sensis%"] = "%sensis%"
    spines: Literal["YES", "Yes", "NO", "%spines%"] = "%spines%"
    solveda: Literal["YES", "1", "%solveda%"] = "%solveda%"
    varcost: Literal["LIN", "%varcost%"] = "%varcost%"
    dscauto: Literal["YES", "%dscauto%"] = "%dscauto%"
    datagdx: Literal["YES", "%datagdx%"] = "%datagdx%"
    botime: int = 1980
    eotime: int = 2200
    vedavdd: Literal["YES", "%vedavdd%"] = "%vedavdd%"
    timesed: Literal["YES", "NO", "%timesed%"] = "%timesed%"
    anncost: Literal["LEV", "%anncost%"] = "%anncost%"
    macro: Literal["YES", "Yes", "MLF", "MSA", "CSA", "%macro%"] = "%macro%"
    cli: Literal["YES", "%cli%"] = "%cli%"
    etl: Literal["YES", "NO", "%etl%"] = "%etl%"
    fixboh: int | Literal["%fixboh%"] = "%fixboh%"
    lpoint: str = "%lpoint%"
    dsc: str = "%dsc%"
    timestep: int | str = "%timestep%"
    rpt_opt: pd.DataFrame | Literal["%rpt_opt%"] = "%rpt_opt%"
    gdxpath: str = "%gdxpath%"
    gdx_irebnd: str = "%gdx_irebnd%"
    gdx_ipric: str = "%gdx_ipric%"


class RunConfig(BaseModel):
    # Allow to accept un-validated custom Python classes (DataModules)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_name: str = "TEST"
    milestone_years: list[str]
    env_vars: UserConfig
    data_dir: Path
    data_modules: list[Path]

    time_slices: Path
    lp_solver: str = Field(default="CPLEX")
