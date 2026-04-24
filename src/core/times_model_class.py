# times_model_class.py

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List

from gamspy import Container, Options, Parameter, Set, Variable

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment


class TimesModelClass:
    """
    Central orchestrator / shared state ("tc") for the TIMES model embedding workflow.
    """

    def __init__(
        self,
        env: "CompileEnvironment",
        output_compile: Path,
        output_execute: Path,
        test: bool,
    ):
        self.env = env
        self.execution_list: list[Callable] = []
        self.output_compile = output_compile
        self.output_execute = output_execute
        self.test_run = test
        self.compile_states: dict = {}
        # self.container = Container(debugging_level="keep")
        self.container = Container()
        self._solve_options: Options
        self.logger = logging.getLogger("TimesModel")

        # Ordered list of registered modules
        self._modules: List[GamsClass] = []

        # Sets
        self.rp_upl: Set = None
        self.miyr_l: Set = None
        self.rtp_varp: Set = None
        self.tsl: Set = None
        self.rtp_shape: Set = None
        self.rcs_combal: Set = None
        self.cur_grp: Set = None
        self.prc_simv: Set = None
        self.uc_tsl: Set = None
        self.rtp_ishpr: Set = None
        self.prc_map: Set = None
        self.rp_flo: Set = None
        self.stl: Set = None
        self.units: Set = None
        self.vnt: Set = None
        self.dem_smap: Set = None
        self.uc_gmap_c: Set = None
        self.s2: Set = None
        self.obj_sumiii: Set = None
        self.rpc_capflo: Set = None
        self.g_uanrg: Set = None
        self.r: Set = None
        self.uc_mapcost: Set = None
        self.trackpc: Set = None
        self.allsow: Set = None
        self.prc_foff: Set = None
        self.com_tsl: Set = None
        self.fs_emis: Set = None
        self.obj_2b: Set = None
        self.rt_pp: Set = None
        self.uc_newflo: Set = None
        self.mat_type: Set = None
        self.bnd_type: Set = None
        self.datayear: Set = None
        self.g_ucnrg: Set = None
        self.rtc_net: Set = None
        self.rtpgig: Set = None
        self.uc_name: Set = None
        self.fstsl: Set = None
        self.rmkc: Set = None
        self.rj_sl: Set = None
        self.obj_sali: Set = None
        self.rtp_ian: Set = None
        self.prc_aoff: Set = None
        self.obj_1a: Set = None
        self.rx_mark: Set = None
        self.rvpt: Set = None
        self.obj_idc: Set = None
        self.uc_gmap_p: Set = None
        self.ts_off: Set = None
        self.ble_opr: Set = None
        self.rtps_off: Set = None
        self.opyear: Set = None
        self.prc: Set = None
        self.pyr: Set = None
        self.uc_attr: Set = None
        self.obj_sumsi: Set = None
        self.ble_speopr: Set = None
        self.rtp_cptyr: Set = None
        self.com_var: Set = None
        self.no_rvp: Set = None
        self.invstep: Set = None
        self.k_eoh: Set = None
        self.rs_prev: Set = None
        self.uc_qaflo: Set = None
        self.ne: Set = None
        self.rpc_aire: Set = None
        self.actcg: Set = None
        self.uc_rtsuc: Set = None
        self.g_rcur: Set = None
        self.rpc_stgn: Set = None
        self.solvestat: Set = None
        self.costcat: Set = None
        self.com_grp: Set = None
        self.my_ts: Set = None
        self.rtpc: Set = None
        self.milestonyr: Set = None
        self.g_ucmat: Set = None
        self.dem_sect: Set = None
        self.xpt: Set = None
        self.rp_pg: Set = None
        self.units_mony: Set = None
        self.obj_vflo: Set = None
        self.com2: Set = None
        self.uc_ts_sum: Set = None
        self.imp: Set = None
        self.uc_capflo: Set = None
        self.bdupx: Set = None
        self.uc_uts: Set = None
        self.rs_tree: Set = None
        self.uc_map_flo: Set = None
        self.rvps: Set = None
        self.cg4: Set = None
        self.modlyear: Set = None
        self.rtp_capyr: Set = None
        self.com_tmap: Set = None
        self.rcs: Set = None
        self.uc_rhsmap: Set = None
        self.uc_gmap_u: Set = None
        self.nrg_grid: Set = None
        self.obj_sums: Set = None
        self.uc_ds: Set = None
        self.uc_dt: Set = None
        self.prc_rcap: Set = None
        self.rpc_ffunc: Set = None
        self.rps_caflac: Set = None
        self.r_uc: Set = None
        self.cg: Set = None
        self.obj_i2: Set = None
        self.bd: Set = None
        self.env_map: Set = None
        self.trackc: Set = None
        self.prc_grp: Set = None
        self.agej: Set = None
        self.ble_spe: Set = None
        self.com_pkts: Set = None
        self.rtp_off: Set = None
        self.rtc: Set = None
        self.annual: Set = None
        self.k: Set = None
        self.rtp_tt: Set = None
        self.rpg_1ace: Set = None
        self.cg3: Set = None
        self.periodyr: Set = None
        self.com1: Set = None
        self.uc_dynt: Set = None
        self.cur_map: Set = None
        self.rpc_irein: Set = None
        self.g_uamat: Set = None
        self.sameas: Set = None
        self.cgtest: Set = None
        self.js: Set = None
        self.prc_tsl: Set = None
        self.com_lim: Set = None
        self.dem: Set = None
        self.eohyear: Set = None
        self.rpg_ace: Set = None
        self.obj_sums3: Set = None
        self.lim_type: Set = None
        self.dp_losd: Set = None
        self.shedj: Set = None
        self.subt: Set = None
        self.rp_ire: Set = None
        self.cg1: Set = None
        self.ykk: Set = None
        self.rpc_cur: Set = None
        self.invspred: Set = None
        self.fin_map: Set = None
        self.chp: Set = None
        self.ble_env: Set = None
        self.rp_pl: Set = None
        self.reg_grp: Set = None
        self.rtp_mrk: Set = None
        self.rp: Set = None
        self.sow: Set = None
        self.rp_sts: Set = None
        self.ructs: Set = None
        self.rs_below: Set = None
        self.mi_dmas: Set = None
        self.rjlvl: Set = None
        self.rtps_bd: Set = None
        self.mat_grp: Set = None
        self.superyr: Set = None
        self.prc_act: Set = None
        self.uc_ts_each: Set = None
        self.rpg_afcx: Set = None
        self.rdcur: Set = None
        self.obj_sumii: Set = None
        self.rpcc_ffunc: Set = None
        self.rreg: Set = None
        self.obj_2a: Set = None
        self.rhs: Set = None
        self.units_act: Set = None
        self.rpcg_ptran: Set = None
        self.rtcs_sing: Set = None
        self.rc: Set = None
        self.uc_grptype: Set = None
        self.rtx_mrk: Set = None
        self.rvpcsl: Set = None
        self.rp_nrg: Set = None
        self.rtpx: Set = None
        self.nrg: Set = None
        self.premile: Set = None
        self.fin_grp: Set = None
        self.rpc_stg: Set = None
        self.cgtes2: Set = None
        self.rtp_vara: Set = None
        self.yk: Set = None
        self.rpc_market: Set = None
        self.uc_perds: Set = None
        self.lnx: Set = None
        self.rp_upc: Set = None
        self.rpc_eqire: Set = None
        self.prc_stgtss: Set = None
        self.nrgelc: Set = None
        self.prc_pkno: Set = None
        self.miyr_1: Set = None
        self.prc_ts2: Set = None
        self.obj_1b: Set = None
        self.prc_noff: Set = None
        self.t: Set = None
        self.v: Set = None
        self.com: Set = None
        self.rtpcs_out: Set = None
        self.com_unit: Set = None
        self.com_desc: Set = None
        self.rpc_noflo: Set = None
        self.rlup: Set = None
        self.costagg: Set = None
        self.rt_ian: Set = None
        self.allyear: Set = None
        self.mat_wt: Set = None
        self.uc_n: Set = None
        self.all_r: Set = None
        self.eachyear: Set = None
        self.prc_dscncap: Set = None
        self.trackpg: Set = None
        self.ble_tp: Set = None
        self.rvp: Set = None
        self.bdval: Set = None
        self.rtp_pl: Set = None
        self.rvp_kmap: Set = None
        self.obj_fcur: Set = None
        self.uc_r_each: Set = None
        self.rtp_grp: Set = None
        self.phyr: Set = None
        self.rpc_ire: Set = None
        self.tslvl: Set = None
        self.mreg: Set = None
        self.rcs_comts: Set = None
        self.rtp_vntbyr: Set = None
        self.ktyage: Set = None
        self.rtp_shapi: Set = None
        self.c: Set = None
        self.prc_capunt: Set = None
        self.nrg_fmap: Set = None
        self.bdneq: Set = None
        self.s: Set = None
        self.impexp: Set = None
        self.top_ire: Set = None
        self.rp_stl: Set = None
        self.tpulseyr: Set = None
        self.perdinv: Set = None
        self.units_com: Set = None
        self.r_uct: Set = None
        self.rpc_act: Set = None
        self.obj_icur: Set = None
        self.rp_prc: Set = None
        self.uncd7: Set = None
        self.backward: Set = None
        self.j: Set = None
        self.uncd1: Set = None
        self.kage: Set = None
        self.rcs_comprd: Set = None
        self.lim: Set = None
        self.all_reg: Set = None
        self.uc_ut: Set = None
        self.cov_map: Set = None
        self.cvt: Set = None
        self.fscks: Set = None
        self.rcj: Set = None
        self.fil: Set = None
        self.rp_inout: Set = None
        self.obj_spred: Set = None
        self.obj_sumiv: Set = None
        self.cost_gmap: Set = None
        self.bohyear: Set = None
        self.p: Set = None
        self.rpc_spg: Set = None
        self.rps_prcts: Set = None
        self.mat: Set = None
        self.unit: Set = None
        self.int_default: Set = None
        self.rs_up: Set = None
        self.forward: Set = None
        self.phantom: Set = None
        self.prc_ts: Set = None
        self.sl: Set = None
        self.l: Set = None
        self.uc_jmap: Set = None
        self.rhs_comprd: Set = None
        self.tt: Set = None
        self.rps_stg: Set = None
        self.rp_aire: Set = None
        self.y_eoh: Set = None
        self.mat_tmap: Set = None
        self.rd_agg: Set = None
        self.upt: Set = None
        self.uc_annul: Set = None
        self.ffcks: Set = None
        self.bdlox: Set = None
        self.yk1: Set = None
        self.rxx: Set = None
        self.ble_speinp: Set = None
        self.afs: Set = None
        self.top: Set = None
        self.rpc_emis: Set = None
        self.age: Set = None
        self.ips: Set = None
        self.uc_cost: Set = None
        self.cg_grp: Set = None
        self.prc_desc: Set = None
        self.uc_tmap: Set = None
        self.nrg_type: Set = None
        self.nrg_tmap: Set = None
        self.ykage: Set = None
        self.com_peak: Set = None
        self.uc_on: Set = None
        self.rp_pgtype: Set = None
        self.rp_cgc: Set = None
        self.com_gmap: Set = None
        self.g_uds: Set = None
        self.rp_cgg: Set = None
        self.prc_vint: Set = None
        self.u: Set = None
        self.rtc_shed: Set = None
        self.rc_cumcom: Set = None
        self.pyr_s: Set = None
        self.life: Set = None
        self.rp_dp: Set = None
        self.y: Set = None
        self.rtcs_varc: Set = None
        self.rtp_vintyr: Set = None
        self.ele: Set = None
        self.rp_ux: Set = None
        self.spe: Set = None
        self.ts_group: Set = None
        self.pastyear: Set = None
        self.rpc_ireio: Set = None
        self.nrg_gmap: Set = None
        self.fsck: Set = None
        self.rp_ccg: Set = None
        self.prc_cg: Set = None
        self.lastll: Set = None
        self.uc_number: Set = None
        self.nrg_form: Set = None
        self.rp_grp: Set = None
        self.hpl: Set = None
        self.obj_sumivs: Set = None
        self.prc_pkaf: Set = None
        self.rc_iop: Set = None
        self.uc_t_sum: Set = None
        self.ts_ann: Set = None
        self.pg_smap: Set = None
        self.jj: Set = None
        self.opr: Set = None
        self.rtc_prd: Set = None
        self.mat_vol: Set = None
        self.com_off: Set = None
        self.ire_dist: Set = None
        self.rpc_ace: Set = None
        self.span: Set = None
        self.afups: Set = None
        self.rp_sgs: Set = None
        self.opr2: Set = None
        self.year: Set = None
        self.obv: Set = None
        self.prc_rsourc: Set = None
        self.prc_cap: Set = None
        self.fin: Set = None
        self.rs_below1: Set = None
        self.fs_emcb: Set = None
        self.prc_stgips: Set = None
        self.rp_dpl: Set = None
        self.ble_inp: Set = None
        self.curr: Set = None
        self.io: Set = None
        self.uc_dyndir: Set = None
        self.dumimp: Set = None
        self.prc_spg: Set = None
        self.ts: Set = None
        self.ll: Set = None
        self.all_ts: Set = None
        self.eohyears: Set = None
        self.rpc_pg: Set = None
        self.cur: Set = None
        self.rpg_red: Set = None
        self.rc_agp: Set = None
        self.obj_yes: Set = None
        self.rp_upr: Set = None
        self.ts_map: Set = None
        self.rps_ups: Set = None
        self.prc_nstts: Set = None
        self.rtp: Set = None
        self.rp_pgact: Set = None
        self.rtx_mark: Set = None
        self.rpg_pace: Set = None
        self.rpc_ls: Set = None
        self.no_act: Set = None
        self.rpc_cumflo: Set = None
        self.mat_gmap: Set = None
        self.w: Set = None
        self.matprc: Set = None
        self.prc_rmap: Set = None
        self.trackp: Set = None
        self.prc_actunt: Set = None
        self.env_grp: Set = None
        self.rp_pgflo: Set = None
        self.uc_t_each: Set = None
        self.ble: Set = None
        self.keep_flof: Set = None
        self.side: Set = None
        self.agefil: Set = None
        self.com_ts: Set = None
        self.reg_rmap: Set = None
        self.rtp_cg: Set = None
        self.pastmile: Set = None
        self.rtp_cgc: Set = None
        self.rpc_pkc: Set = None
        self.ucn: Set = None
        self.reg: Set = None
        self.chp_elc: Set = None
        self.rp_xred: Set = None
        self.finest: Set = None
        self.rp_std: Set = None
        self.rc_rc: Set = None
        self.rp_ups: Set = None
        self.uc_map_ire: Set = None
        self.jot: Set = None
        self.uc_dynbnd: Set = None
        self.rvt: Set = None
        self.rpc: Set = None
        self.rp_stg: Set = None
        self.item: Set = None
        self.uc_rhstmp: Set = None
        self.in_out: Set = None
        self.sw_t: Set = None
        self.rpc_conly: Set = None
        self.rpc_aflo: Set = None
        self.cg2: Set = None
        self.rtpcs_varf: Set = None
        self.rp_gic: Set = None
        self.ref: Set = None
        self.dm_year: Set = None
        self.com_type: Set = None
        self.fs_emit: Set = None
        self.rps_s2: Set = None
        self.rhs_combal: Set = None
        self.units_cap: Set = None
        self.rp_upt: Set = None
        self.rps_s1: Set = None
        self.my_fil: Set = None
        self.uc_t: Set = None
        self.uc_r_sum: Set = None
        self.ie: Set = None
        self.rpcs_var: Set = None
        self.costype: Set = None
        self.uc_t_succ: Set = None
        self.rp_dcgg: Set = None

        # Parameters
        self.yearval: Parameter = None
        self.coef_iled: Parameter = None
        self.flo_cost: Parameter = None
        self.act_cstup: Parameter = None
        self.stgout_bnd: Parameter = None
        self.obj_divi: Parameter = None
        self.miyr_boh: Parameter = None
        self.ncap_ftax: Parameter = None
        self.objsic: Parameter = None
        self.rcap_bnd: Parameter = None
        self.gg_kgf: Parameter = None
        self.salv_dec: Parameter = None
        self.x_rpgcs: Parameter = None
        self.act_cost: Parameter = None
        self.ncap_ftaxm: Parameter = None
        self.uc_rhss: Parameter = None
        self.ncap_elife: Parameter = None
        self.my_f: Parameter = None
        self.done: Parameter = None
        self.x_rpgcgs: Parameter = None
        self.g_chngmony: Parameter = None
        self.g_drate: Parameter = None
        self.dfunc: Parameter = None
        self.d: Parameter = None
        self.x_rp: Parameter = None
        self.gr_vargen: Parameter = None
        self.com_ie: Parameter = None
        self.ipd: Parameter = None
        self.ob_fsb: Parameter = None
        self.coef_cap: Parameter = None
        self.pyr_v1: Parameter = None
        self.prc_sgl: Parameter = None
        self.dam_step: Parameter = None
        self.ncap_dlag: Parameter = None
        self.com_voc: Parameter = None
        self.obj_iad: Parameter = None
        self.ncap_clag: Parameter = None
        self.par_objflo: Parameter = None
        self.my_array: Parameter = None
        self.obj_crf: Parameter = None
        self.ncap_afs: Parameter = None
        self.com_cumnet: Parameter = None
        self.ncap_bpme: Parameter = None
        self.dam_bqty: Parameter = None
        self.rvprl: Parameter = None
        self.bl_varomc: Parameter = None
        self.com_mshgv: Parameter = None
        self.com_pkrsv: Parameter = None
        self.uc_cumflo: Parameter = None
        self.prc_gmap: Parameter = None
        self.ncap_af: Parameter = None
        self.coef_cio: Parameter = None
        self.obj_rfr: Parameter = None
        self.g_iledno: Parameter = None
        self.dam_cost: Parameter = None
        self.flo_fr: Parameter = None
        self.gr_endfr: Parameter = None
        self.rpc_pkf: Parameter = None
        self.com_bprice: Parameter = None
        self.rpt_opt: Parameter = None
        self.yr_vl: Parameter = None
        self.ncap_fsub: Parameter = None
        self.uc_comnet: Parameter = None
        self.e: Parameter = None
        self.stg_maxcyc: Parameter = None
        self.ob_fcos: Parameter = None
        self.x_uzrpcs: Parameter = None
        self.ncap_iled: Parameter = None
        self.par_objsal: Parameter = None
        self.obj_diviv: Parameter = None
        self.uc_time: Parameter = None
        self.prc_semi: Parameter = None
        self.lagt: Parameter = None
        self.cnt: Parameter = None
        self.x_rpcgsb: Parameter = None
        self.tslvlnum: Parameter = None
        self.cap_bnd: Parameter = None
        self.rs_stgprd: Parameter = None
        self.dam_voc: Parameter = None
        self.gr_ptdf: Parameter = None
        self.ob_com: Parameter = None
        self.com_cumprd: Parameter = None
        self.act_cstrmp: Parameter = None
        self.flo_deliv: Parameter = None
        self.uc_comprd: Parameter = None
        self.par_objels: Parameter = None
        self.com_cstbal: Parameter = None
        self.com_proj: Parameter = None
        self.ire_tscvt: Parameter = None
        self.par_objcom: Parameter = None
        self.ncap_valu: Parameter = None
        self.rp_afb: Parameter = None
        self.ncap_dlagc: Parameter = None
        self.g_tlife: Parameter = None
        self.ncap_semi: Parameter = None
        self.par_flo: Parameter = None
        self.prc_refit: Parameter = None
        self.yr_v1: Parameter = None
        self.rtforc: Parameter = None
        self.ru_cvt: Parameter = None
        self.r_df: Parameter = None
        self.my_fyear: Parameter = None
        self.gr_demfr: Parameter = None
        self.salv_inv: Parameter = None
        self.obj_ipric: Parameter = None
        self.cor_salvi: Parameter = None
        self.rs_fr: Parameter = None
        self.ob_dlc: Parameter = None
        self.bl_delivc: Parameter = None
        self.ncap_dcost: Parameter = None
        self.flo_emis: Parameter = None
        self.dur_max: Parameter = None
        self.ncap_com: Parameter = None
        self.vda_ceh: Parameter = None
        self.lead: Parameter = None
        self.rs_tslvl: Parameter = None
        self.ncap_pkcnt: Parameter = None
        self.g_cycle: Parameter = None
        self.uc_rhsts: Parameter = None
        self.par_objble: Parameter = None
        self.x_rusl: Parameter = None
        self.ncap_fsubx: Parameter = None
        self.stg_chrg: Parameter = None
        self.x_rul: Parameter = None
        self.ts_bd: Parameter = None
        self.ncap_chpr: Parameter = None
        self.obj_blndv: Parameter = None
        self.obj_compd: Parameter = None
        self.fil2: Parameter = None
        self.ncap_afbx: Parameter = None
        self.com_agg: Parameter = None
        self.ru_feq: Parameter = None
        self.gr_genmap: Parameter = None
        self.multi: Parameter = None
        self.ncap_cost: Parameter = None
        self.flo_shar: Parameter = None
        self.uc_ncap: Parameter = None
        self.act_lospl: Parameter = None
        self.x_rpgsb: Parameter = None
        self.cst_annc: Parameter = None
        self.micro: Parameter = None
        self.vda_flop: Parameter = None
        self.ob_act: Parameter = None
        self.uc_com: Parameter = None
        self.ire_xbnd: Parameter = None
        self.dp_non: Parameter = None
        self.gr_genfr: Parameter = None
        self.par_irem: Parameter = None
        self.prc_mark: Parameter = None
        self.x_rpsb: Parameter = None
        self.reg_cumcst: Parameter = None
        self.g_unca: Parameter = None
        self.bl_com: Parameter = None
        self.flo_sum: Parameter = None
        self.ncap_fsubm: Parameter = None
        self.prc_react: Parameter = None
        self.shape: Parameter = None
        self.act_eff: Parameter = None
        self.x_rpcsl: Parameter = None
        self.g_vint: Parameter = None
        self.cm_maxc_m: Parameter = None
        self.com_bqty: Parameter = None
        self.uc_rhsrs: Parameter = None
        self.sum_obj: Parameter = None
        self.gr_genlev: Parameter = None
        self.ncap_afsm: Parameter = None
        self.com_cum: Parameter = None
        self.dump0: Parameter = None
        self.reg_fixt: Parameter = None
        self.acl: Parameter = None
        self.com_bndnet: Parameter = None
        self.ncap_start: Parameter = None
        self.uc_actbet: Parameter = None
        self.coef_af: Parameter = None
        self.stoa: Parameter = None
        self.errlev: Parameter = None
        self.com_taxnet: Parameter = None
        self.ncap_olife: Parameter = None
        self.objscc: Parameter = None
        self.par_objfix: Parameter = None
        self.x_rpgs: Parameter = None
        self.g_yrfr: Parameter = None
        self.rcap_blk: Parameter = None
        self.par_flom: Parameter = None
        self.cor_salvd: Parameter = None
        self.ncap_delif: Parameter = None
        self.minyr: Parameter = None
        self.refunit: Parameter = None
        self.act_minld: Parameter = None
        self.x_rpg: Parameter = None
        self.peakda_bl: Parameter = None
        self.ncap_bnd: Parameter = None
        self.ncap_cled: Parameter = None
        self.uc_act: Parameter = None
        self.ncap_msprf: Parameter = None
        self.x_rpcl: Parameter = None
        self.act_cum: Parameter = None
        self.tpulse: Parameter = None
        self.ncap_pasty: Parameter = None
        self.beoh: Parameter = None
        self.bl_inp: Parameter = None
        self.ncap_icom: Parameter = None
        self.ifq: Parameter = None
        self.rd_shar: Parameter = None
        self.coef_vnt: Parameter = None
        self.flo_funcx: Parameter = None
        self.uc_flo: Parameter = None
        self.uc_rhsrt: Parameter = None
        self.uc_rhs: Parameter = None
        self.com_elast: Parameter = None
        self.obj_jd: Parameter = None
        self.gr_xbnd: Parameter = None
        self.my_fil2: Parameter = None
        self.ob_fom: Parameter = None
        self.uc_ire: Parameter = None
        self.cst_dam: Parameter = None
        self.obj_fsub: Parameter = None
        self.par_objinv: Parameter = None
        self.uc_cumcom: Parameter = None
        self.rtp_capvl: Parameter = None
        self.bl_start: Parameter = None
        self.rs_stg: Parameter = None
        self.vda_disc: Parameter = None
        self.coef_rpti: Parameter = None
        self.ncap_cpx: Parameter = None
        self.gr_thmin: Parameter = None
        self.ncap_afc: Parameter = None
        self.act_lossd: Parameter = None
        self.prc_ymin: Parameter = None
        self.ob_isub: Parameter = None
        self.x_mark: Parameter = None
        self.coef_afups: Parameter = None
        self.first_val: Parameter = None
        self.g_curex: Parameter = None
        self.ob_dcc: Parameter = None
        self.obj_pvt: Parameter = None
        self.flo_func: Parameter = None
        self.par_objact: Parameter = None
        self.endoff: Parameter = None
        self.ncap_afac: Parameter = None
        self.dam_coef: Parameter = None
        self.bl_spec: Parameter = None
        self.ob_icost: Parameter = None
        self.gg_klp: Parameter = None
        self.startoff: Parameter = None
        self.com_taxprd: Parameter = None
        self.prc_ymax: Parameter = None
        self.stgin_bnd: Parameter = None
        self.miyr_v1: Parameter = None
        self.g_offthd: Parameter = None
        self.ncap_afm: Parameter = None
        self.com_subprd: Parameter = None
        self.ire_flosum: Parameter = None
        self.ob_fdel: Parameter = None
        self.obj_wd: Parameter = None
        self.g_overlap: Parameter = None
        self.putout: Parameter = None
        self.ob_ftax: Parameter = None
        self.ncap_afx: Parameter = None
        self.ncap_isub: Parameter = None
        self.coef_icom: Parameter = None
        self.coef_cpt: Parameter = None
        self.ncap_afsx: Parameter = None
        self.rd_nlp: Parameter = None
        self.f: Parameter = None
        self.prc_resid: Parameter = None
        self.ie_default: Parameter = None
        self.coef_rtp: Parameter = None
        self.prc_actflo: Parameter = None
        self.rs_modus: Parameter = None
        self.pastsum: Parameter = None
        self.gg_pp: Parameter = None
        self.bl_unit: Parameter = None
        self.ncap_pasti: Parameter = None
        self.cm_result: Parameter = None
        self.ob_ire: Parameter = None
        self.com_fr: Parameter = None
        self.flo_ashar: Parameter = None
        self.obj_dceoh: Parameter = None
        self.ire_ccvt: Parameter = None
        self.shaped: Parameter = None
        self.altobj: Parameter = None
        self.obj_d: Parameter = None
        self.par_ipric: Parameter = None
        self.reg_bndcst: Parameter = None
        self.rs_hr: Parameter = None
        self.prc_dynuc: Parameter = None
        self.act_ups: Parameter = None
        self.obj_c: Parameter = None
        self.stg_eff: Parameter = None
        self.uc_cap: Parameter = None
        self.putgrp: Parameter = None
        self.ob_ftx: Parameter = None
        self.ncap_fomx: Parameter = None
        self.uc_comcon: Parameter = None
        self.dam_elast: Parameter = None
        self.uc_sign: Parameter = None
        self.ncap_afa: Parameter = None
        self.act_bnd: Parameter = None
        self.obj_altv: Parameter = None
        self.ire_bnd: Parameter = None
        self.flo_tax: Parameter = None
        self.ncap_tlife: Parameter = None
        self.flo_bnd: Parameter = None
        self.dam_tqty: Parameter = None
        self.ble_bal: Parameter = None
        self.rtcs_fr: Parameter = None
        self.uc_flobet: Parameter = None
        self.flo_feq: Parameter = None
        self.act_maxnon: Parameter = None
        self.diag: Parameter = None
        self.x_rpggs: Parameter = None
        self.rb: Parameter = None
        self.dam_tvoc: Parameter = None
        self.obj_comnt: Parameter = None
        self.bdsig: Parameter = None
        self.uc_rhsr: Parameter = None
        self.ncap_fom: Parameter = None
        self.flo_eff: Parameter = None
        self.tm_result: Parameter = None
        self.stg_sift: Parameter = None
        self.dp_uns: Parameter = None
        self.prc_sc: Parameter = None
        self.vda_emcb: Parameter = None
        self.fpd: Parameter = None
        self.ncap_drate: Parameter = None
        self.ncap_ocom: Parameter = None
        self.rtp_ffcx: Parameter = None
        self.obj_diviii: Parameter = None
        self.g_dyear: Parameter = None
        self.bl_type: Parameter = None
        self.ncap_afcs: Parameter = None
        self.norts: Parameter = None
        self.last_val: Parameter = None
        self.obj_crfd: Parameter = None
        self.ire_price: Parameter = None
        self.ts_array: Parameter = None
        self.coef_pvt: Parameter = None
        self.rs_stgav: Parameter = None
        self.uc_cumact: Parameter = None
        self.ncap_disc: Parameter = None
        self.ncap_dlife: Parameter = None
        self.dp_psud: Parameter = None
        self.com_pkflx: Parameter = None
        self.com_subnet: Parameter = None
        self.flo_pkcoi: Parameter = None
        self.ncap_ceh: Parameter = None
        self.g_rfrir: Parameter = None
        self.com_elastx: Parameter = None
        self.obj_life: Parameter = None
        self.flo_sub: Parameter = None
        self.flo_cum: Parameter = None
        self.obj_disc: Parameter = None
        self.x_rpb: Parameter = None
        self.com_step: Parameter = None
        self.uc_ucn: Parameter = None
        self.g_nointerp: Parameter = None
        self.par_ire: Parameter = None
        self.optfileid: Parameter = None
        self.act_flo: Parameter = None
        self.act_cstsd: Parameter = None
        self.uc_rhst: Parameter = None
        self.obj_lint: Parameter = None
        self.obj_pasti: Parameter = None
        self.rtp_cpx: Parameter = None
        self.rpcg_ashar: Parameter = None
        self.gg_gamma: Parameter = None
        self.gg_dens: Parameter = None
        self.convert: Parameter = None
        self.par_objdec: Parameter = None
        self.ncap_lcost: Parameter = None
        self.m: Parameter = None
        self.my_sum: Parameter = None
        self.stg_loss: Parameter = None
        self.flo_bdlvl: Parameter = None
        self.ire_flo: Parameter = None
        self.coef_ocom: Parameter = None
        self.coef_ptran: Parameter = None
        self.r_curex: Parameter = None
        self.gg_prbd: Parameter = None
        self.reg_bdncap: Parameter = None
        self.x_rcs: Parameter = None
        self.com_cstnet: Parameter = None
        self.flo_mark: Parameter = None
        self.ncap_itax: Parameter = None
        self.act_cstpl: Parameter = None
        self.js_ccl: Parameter = None
        self.no_rt: Parameter = None
        self.ts_cycle: Parameter = None
        self.act_sdtime: Parameter = None
        self.ncap_fdr: Parameter = None
        self.z: Parameter = None
        self.stoal: Parameter = None
        self.ob_itax: Parameter = None
        self.ncap_ispct: Parameter = None
        self.par_objlat: Parameter = None
        self.prc_capact: Parameter = None
        self.miyr_vl: Parameter = None
        self.env_bl: Parameter = None
        self.coef_rvpt: Parameter = None
        self.maxlife: Parameter = None
        self.act_time: Parameter = None
        self.com_cstprd: Parameter = None
        self.ncap_fomm: Parameter = None
        self.b: Parameter = None
        self.ncap_cdme: Parameter = None
        self.ykval: Parameter = None
        self.uc_rhsrts: Parameter = None
        self.com_bndprd: Parameter = None
        self.ncap_lfom: Parameter = None
        self.ncap_ftaxx: Parameter = None

        # Variables
        self.VAR_OBJELS: Variable = None
        self.VAR_UCT: Variable = None
        self.VAR_RLD: Variable = None
        self.VAR_DNCAP: Variable = None
        self.VAR_UDP: Variable = None
        self.VAR_DAM: Variable = None
        self.VAR_CUMFLO: Variable = None
        self.VAR_COMPRD: Variable = None
        self.VAR_OBJ: Variable = None
        self.VAR_UCR: Variable = None
        self.VAR_UCRTS: Variable = None
        self.VAR_RCAP: Variable = None
        self.VAR_IRE: Variable = None
        self.VAR_ELAST: Variable = None
        self.OBJZ: Variable = None
        self.VAR_UCRT: Variable = None
        self.VAR_BLND: Variable = None
        self.VAR_UCTS: Variable = None
        self.VAR_DEM: Variable = None
        self.VAS_UPDEV: Variable = None
        self.VAR_UPS: Variable = None
        self.VAR_NCAP: Variable = None
        self.VAR_SCAP: Variable = None
        self.VAR_SNCAP: Variable = None
        self.VAR_COMNET: Variable = None
        self.VAR_UPT: Variable = None
        self.VAR_CUMCOM: Variable = None
        self.VAR_FLO: Variable = None
        self.VAR_CUMCST: Variable = None
        self.VAR_SOUT: Variable = None
        self.VAR_UC: Variable = None
        self.VAR_CAP: Variable = None
        self.VAR_SIN: Variable = None
        self.VAR_ACT: Variable = None
        self.VAS_EXPOBJ: Variable = None

    def register_module(self, module: GamsClass) -> None:
        """Register a module object."""
        if not isinstance(module, GamsClass):
            raise TypeError(
                f"Object {module} does not implement the required TIMES interface."
            )
        self._modules.append(module)

    # -----------------------
    # Code embedding helpers
    # -----------------------
    def add_gams_code(
        self,
        module: GamsClass,
        phase: str,
        code: str,
    ) -> None:
        """
        Add raw GAMS code into the Container with a traceable header.
        """

        header = (
            f"\n* ============================================================\n"
            f"* {module.module_name} :: {phase}\n"
            f"* source: {module.gams_source}\n"
            f"* ============================================================\n"
        )

        self.container.addGamsCode(header + code)

    def dump_generated_gams(self, path: str = "generated_times.gms") -> None:
        """
        Write the currently generated GAMS code to a file for inspection.
        """
        gms = self.container.generateGamsString()
        with open(path, "w", encoding="utf-8") as f:
            f.write(gms)

    def save_test_state(self, env, checkpoint):
        """
        Saves the state of all compile time variables for later testing.

        :param self: Description
        :param env: Description
        :param checkpoint: name of the checkpoint
        """
        state = env.get_test_state()
        self.compile_states[checkpoint] = state

    # -----------------------
    # Orchestration phases
    # -----------------------
    def initialization(self) -> None:
        """Modules are initialized / compiled within their __init__ method. Only used to write GDX state after compilation."""
        # self.container.write(self.output_compile, eps_to_zero=False)
        self.container.addGamsCode(f"execute_unload '{self.output_compile}';")

    def enqueue(self, func, *args, **kwargs):
        """Adds a function call to the end of the execution queue."""
        self.execution_list.append((func, args, kwargs))

    def run(self):
        """Executes all queued functions in order."""
        self.logger.info("Phase: run")
        for func, args, kwargs in self.execution_list:
            func(*args, **kwargs)
        # self.container.write(self.output_execute, eps_to_zero=False)
        self.container.addGamsCode(f"execute_unload '{self.output_execute}';")

    # -----------------------
    # Utils
    # -----------------------
    def defined(self, symbol: str) -> bool:
        return symbol.upper() in self.container.listSymbols() and (
            self.container[symbol.upper()].number_records > 0
        )
