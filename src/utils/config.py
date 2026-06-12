# config.py
from pathlib import Path
from typing import Literal

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
    discshift: int | float | Literal["0"] = Field(
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
    stages: Literal["YES", "Yes", "NO", "%stages%"] = Field(
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

    # Miscellaneous Utility Handles
    validate_: Literal["NO", "%validate%"] = Field(
        default="%validate%",
        alias="validate",
        description="Requests a highly simplified objective function block emulating historical MARKAL configurations (Discouraged).",
    )
    reduce: Literal["YES", "%reduce%"] = Field(
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
    var_uc: Literal["YES", "%var_uc%"] = Field(
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
    mx: str = Field(
        description="Macro tracking name string identifier mapping specialized model equations."
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
    shp1: str = Field(
        description="Dynamic load shape mapping variable utilized for seasonal load curves."
    )
    shg: str = Field(
        description="Text replacement parameter mapping the baseline global optimization coordinates."
    )
    upscap0: str = Field(
        description="Initial capability update tracking parameter handling historical baseline records."
    )
    vas: str = Field(
        description="Variable assignment tracking string mapping structural matrix parameters."
    )
    hs: str = Field(description="Historical scaling parameter tracking data limits.")
    tucn: str = Field(
        description="Tracking identifier mapped to constraint tracking nodes."
    )
    tsum: str = Field(
        description="Summary execution check identifier tracking mathematical summation steps."
    )
    swflo: str = Field(
        description="Flow control switch expression token managing internal operational boundaries."
    )
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
    swsw: str = Field(
        description="Nested operational matrix state control flag identifier."
    )
    swtd: str = Field(
        description="Time-step differentiation switch expression string mapped to parameters."
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
    pass_: str = Field(
        alias="pass",
        description="Execution tracking code handling iterative loop counts.",
    )
    tpulse: str = Field(
        description="Pulse duration coefficient parameter mapping load peak curves."
    )
    capwd: str = Field(
        description="Capacity width adjustment parameter string mapping operating lifetimes."
    )
    sow: str = Field(
        description="Stochastic World (Scenario State) active indexing identifier token."
    )
    sowend: str = Field(
        description="Terminal slice identifier token for Stochastic World trees."
    )
    sowtmp: str = Field(
        description="Temporary scenario tracking storage token utilized in nested loop blocks."
    )
    sowstart: str = Field(
        description="Initial node identifier token for stochastic branch optimization structures."
    )
    sowtmpend: str = Field(
        description="Terminal scenario tracking validation token used within multi-stage loops."
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
    varm: str = Field(
        description="Macro tracking variant variable used in objective calculation hooks."
    )
    vart: str = Field(
        description="Temporal indexing mapping string tracking current variable periods."
    )
    vartt: str = Field(
        description="Nested temporal index mapping string tracking cumulative variable horizons."
    )
    vart1: str = Field(
        description="First shift temporal index mapping string tracking period boundaries."
    )
    varv: str = Field(
        description="Vintage index mapping identifier tracking installed configuration years."
    )
    cal_red: str = Field(
        description="Calculation reduction parameter mapping tracking array dimensions."
    )
    eq: str = Field(description="Equation declaration mapping identifier string.")
    sws: str = Field(
        description="Scenario switch tracking token handling multi-stage matrix settings."
    )
    swstmp: str = Field(
        description="Temporary matrix scenario tracker state parameter."
    )
    swd: str = Field(
        description="Solution domain tracking token mapped to variable dimensions."
    )
    sw1: str = Field(
        description="Primary configuration flag used in file inclusion loops."
    )
    sw2: str = Field(
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
    def_iebd: str = Field(
        description="Boundary conditions definition tracker managing baseline imports and exports."
    )
    extend: str = Field(
        description="Horizons extension directive switch tracked as string primitives."
    )
    ucbd: str = Field(
        description="User constraint bounds description tracking index identifier."
    )
    istep: str = Field(
        description="Iteration step count tracking identifier tracking multi-foresight steps."
    )
    capjd: str = Field(
        description="Technical capacity retirement degradation tracking marker."
    )
    cufscal: str = Field(
        description="Capacity utilization factors scaling parameters modifier parameter."
    )
    cucscal: str = Field(
        description="Capacity optimization cost scaling factors modifier parameter."
    )
    semicont: str = Field(
        description="Semi-continuous limits tracking property mapped to variables."
    )
    reset: str = Field(
        description="System state cleanup parameter tracking uninitialized sets."
    )
    mip: str = Field(
        description="Mixed-Integer Programming active execution framework parameter text token."
    )
    tst: str = Field(
        description="Target time-slice testing configuration parameters identifier."
    )
    varmac: str = Field(
        description="Macro expansion variable configuration property indicator."
    )
    tx: str = Field(
        description="Temporal calculation index identifier utilized in subset configurations."
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
    pgprim: str = Field(
        description="Primary generation fuel tracking parameter identifier string."
    )
    declif: str = Field(
        description="Decommissioning lifetime adjustment parameter tracking array values."
    )
    invlif: str = Field(
        description="Investment active lifecycle tracking array parameter."
    )
    upscaps: str = Field(
        description="Upper capacity scaling modifiers validation tracking text parameter."
    )
    gtime: str = Field(description="System generation timestamp variable indicator.")
    gdate: str = Field(
        description="System generation calendar date variable indicator."
    )
    ctst: str = Field(
        description="Calculation time step parameter used inside optimization updates."
    )
    rts: str = Field(
        description="Regional sub-annual tracking parameter handling seasonal loads."
    )
    rcapsub: str = Field(
        description="Capacity allocation sub-region configuration tracking parameters."
    )
    rcapsbm: str = Field(
        description="Capacity allocation sub-region optimization model variables."
    )
    swx: str = Field(
        description="Primary structural execution switch template mapping parameters."
    )
    swtx: str = Field(
        description="Secondary structural execution switch template mapping parameters."
    )
    sw_stvars: str = Field(
        description="Stochastic step evaluation parameters active variable indicator."
    )
    scum: str = Field(
        description="Cumulative scaling parameters check array parameter tracking strings."
    )
    shff: str = Field(
        description="Shifting frequency variable string mapped inside sub-annual loops."
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


class UserConfig(BaseModel):
    validate_: Literal["NO", "%validate%"] = Field(
        default="%validate%", alias="validate"
    )
    reduce: Literal["YES", "%reduce%"] = "%reduce%"
    vda: Literal["YES", "%vda%"] = "%vda%"
    debug: Literal["YES", "NO"] = "NO"
    dumpsol: Literal["YES", "NO"] = "NO"
    solans: Literal["YES", "NO"] = "NO"
    err_abort: Literal["YES", "NO"] = "YES"
    gams_cgi: Literal["NO", "WWW"] = "NO"
    solve_now: Literal["YES", "NO"] = "YES"
    model_name: str = "TIMES"
    xtqa: Literal["YES", "%xtqa%"] = "%xtqa%"
    var_uc: Literal["YES", "%var_uc%"] = "%var_uc%"
    obj: Literal["ALT", "MOD", "LIN", "STD", "AUTO"] = "AUTO"
    mid_year: Literal["YES", "%mid_year%"] = "%mid_year%"
    oblong: Literal["YES", "NO", "%oblong%"] = "%oblong%"
    damage: Literal["LP", "NLP", "NO"] = "LP"
    stages: Literal["YES", "Yes", "NO", "%stages%"] = "%stages%"
    solveda: Literal["YES", "%solveda%"] = "%solveda%"
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
    fixboh: int | Literal["%fixboh%"] = "%fixboh%"
    lpoint: str = "%lpoint%"


class RunConfig(BaseModel):
    # Allow to accept un-validated custom Python classes (DataModules)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_name: str = "TEST"
    milestone_years: list[str]
    env_vars: UserConfig
    data_modules: list[Path]

    time_slices: Path
    lp_solver: str = Field(default="CBC")
