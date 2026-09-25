import platform
import subprocess
from pathlib import Path
from time import perf_counter

import gamspy_base  # type: ignore[import-untyped]
import pytest
from dotenv import load_dotenv
from gams_cache import ensure_reference_gdx  # type: ignore[import-not-found]

from main import run_times as run_gamspy
from utils.config import RunConfig
from utils.downloader import ensure_nextcloud_data
from utils.macros import macro_config
from utils.run_registry import REGISTRY

load_dotenv()


def win_tol(releps: str, eps: str | None = None) -> dict[str, str]:
    """Gdxdiff tolerance overrides, applied only on Windows."""
    if platform.system() != "Windows":
        return {}
    return {"gdxdiff_releps": releps, "gdxdiff_eps": eps or releps}


TEST_INSTANCES: dict[str, dict[str, str]] = {
    "demos_001": {
        "gms_file": "src/data/DemoS_001/demos_001.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_001",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_001.zip",
    },
    "demos_002": {
        "gms_file": "src/data/DemoS_002/demos_002.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_002",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_002.zip",
    },
    "demos_003": {
        "gms_file": "src/data/DemoS_003/demos_003.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_003",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_003.zip",
    },
    "demos_004": {
        "gms_file": "src/data/DemoS_004/demos_004.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_004",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_004.zip",
    },
    "demos_004a": {
        "gms_file": "src/data/DemoS_004a/demos_004a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_004a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_004a.zip",
    },
    "demos_004b": {
        "gms_file": "src/data/DemoS_004b/demos_004b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_004b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_004b.zip",
    },
    "demos_005": {
        "gms_file": "src/data/DemoS_005/demos_005.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_005",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_005.zip",
    },
    "demos_005a": {
        "gms_file": "src/data/DemoS_005a/demos_005a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_005a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_005a.zip",
    },
    "demos_005b": {
        "gms_file": "src/data/DemoS_005b/demos_005b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_005b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_005b.zip",
    },
    "demos_006": {
        "gms_file": "src/data/DemoS_006/demos_006.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_006",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_006.zip",
    },
    "demos_006_irebnd": {
        "gms_file": "src/data/DemoS_006/demos_006_irebnd.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_006",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_006.zip",
        "solve": "SOLVE",
    },
    "demos_006a": {
        "gms_file": "src/data/DemoS_006a/demos_006a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_006a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_006a.zip",
    },
    "demos_006b": {
        "gms_file": "src/data/DemoS_006b/demos_006b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_006b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_006b.zip",
    },
    "demos_007": {
        "gms_file": "src/data/DemoS_007/demos_007.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_007",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_007.zip",
    },
    "demos_007a": {
        "gms_file": "src/data/DemoS_007a/demos_007a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_007a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_007a.zip",
    },
    "demos_007b": {
        "gms_file": "src/data/DemoS_007b/demos_007b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_007b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_007b.zip",
        "solve": "SOLVE",
    },
    # "demos_007b_timesed": {
    #     "gms_file": "src/data/DemoS_007b/demos_007b_timesed.run",
    #     "idir1": "TIMES_source/source",
    #     "idir2": "src/data/DemoS_007b",
    #     "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_007b.zip",
    #     "solve": "SOLVE",
    # },
    "demos_007b_micro": {
        "gms_file": "src/data/DemoS_007b/demos_007b_micro.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_007b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_007b.zip",
    },
    "demos_007c": {
        "gms_file": "src/data/DemoS_007c/demos_007c.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_007c",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_007c.zip",
    },
    "demos_008": {
        "gms_file": "src/data/DemoS_008/demos_008.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_008",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_008.zip",
    },
    "demos_008a": {
        "gms_file": "src/data/DemoS_008a/demos_008a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_008a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_008a.zip",
    },
    "demos_008b": {
        "gms_file": "src/data/DemoS_008b/demos_008b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_008b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_008b.zip",
    },
    "demos_008c": {
        "gms_file": "src/data/DemoS_008c/demos_008c.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_008c",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_008c.zip",
    },
    "demos_009": {
        "gms_file": "src/data/DemoS_009/demos_009.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_009",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_009.zip",
    },
    "demos_009a": {
        "gms_file": "src/data/DemoS_009a/demos_009a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_009a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_009a.zip",
    },
    "demos_009b": {
        "gms_file": "src/data/DemoS_009b/demos_009b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_009b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_009b.zip",
    },
    "demos_009c": {
        "gms_file": "src/data/DemoS_009c/demos_009c.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_009c",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_009c.zip",
    },
    "demos_009d": {
        "gms_file": "src/data/DemoS_009d/demos_009d.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_009d",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_009d.zip",
    },
    "demos_009e": {
        "gms_file": "src/data/DemoS_009e/demos_009e.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_009e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_009e.zip",
    },
    "demos_010": {
        "gms_file": "src/data/DemoS_010/demos_010.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_010",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_010.zip",
    },
    "demos_010a": {
        "gms_file": "src/data/DemoS_010a/demos_010a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_010a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_010a.zip",
    },
    "demos_010b": {
        "gms_file": "src/data/DemoS_010b/demos_010b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_010b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_010b.zip",
    },
    "demos_010c": {
        "gms_file": "src/data/DemoS_010c/demos_010c.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_010c",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_010c.zip",
    },
    "demos_010d": {
        "gms_file": "src/data/DemoS_010d/demos_010d.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_010d",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_010d.zip",
    },
    "demos_010e": {
        "gms_file": "src/data/DemoS_010e/demos_010e.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_010e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_010e.zip",
    },
    "demos_011": {
        "gms_file": "src/data/DemoS_011/demos_011.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_011",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_011.zip",
    },
    "demos_011a": {
        "gms_file": "src/data/DemoS_011a/demos_011a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_011a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_011a.zip",
    },
    "demos_011b": {
        "gms_file": "src/data/DemoS_011b/demos_011b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_011b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_011b.zip",
    },
    "demos_011c": {
        "gms_file": "src/data/DemoS_011c/demos_011c.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_011c",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_011c.zip",
    },
    "demos_011d": {
        "gms_file": "src/data/DemoS_011d/demos_011d.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_011d",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_011d.zip",
    },
    "demos_011e": {
        "gms_file": "src/data/DemoS_011e/demos_011e.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_011e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_011e.zip",
    },
    "demos_012a": {
        "gms_file": "src/data/DemoS_012a/demos_012a.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012a",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012a.zip",
    },
    "demos_012b": {
        "gms_file": "src/data/DemoS_012b/demos_012b.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012b",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012b.zip",
    },
    "demos_012c": {
        "gms_file": "src/data/DemoS_012c/demos_012c.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012c",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012c.zip",
    },
    "demos_012d": {
        "gms_file": "src/data/DemoS_012d/demos_012d.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012d",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012d.zip",
    },
    "demos_012e": {
        "gms_file": "src/data/DemoS_012e/demos_012e.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
    },
    "demos_012e_noreduce": {
        "gms_file": "src/data/DemoS_012e/demos_012e_noreduce.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_vintopt": {
        "gms_file": "src/data/DemoS_012e/demos_012e_vintopt.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_novaruc": {
        "gms_file": "src/data/DemoS_012e/demos_012e_novaruc.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_dumpsol": {
        "gms_file": "src/data/DemoS_012e/demos_012e_dumpsol.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_objann": {
        "gms_file": "src/data/DemoS_012e/demos_012e_objann.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
    },
    "demos_012e_objlin": {
        "gms_file": "src/data/DemoS_012e/demos_012e_objlin.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_solans": {
        "gms_file": "src/data/DemoS_012e/demos_012e_solans.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_oblongno": {
        "gms_file": "src/data/DemoS_012e/demos_012e_oblongno.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_ier": {
        "gms_file": "src/data/DemoS_012e/demos_012e_ier.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_ier_chp": {
        "gms_file": "src/data/DemoS_012e/demos_012e_ier_chp.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_etl": {
        "gms_file": "src/data/DemoS_012e/demos_012e_etl.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_objalt": {
        "gms_file": "src/data/DemoS_012e/demos_012e_objalt.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demos_012e_abs": {
        "gms_file": "src/data/DemoS_012e/demos_012e_abs.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/DemoS_012e",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/DemoS_012e.zip",
        "solve": "SOLVE",
        **win_tol("1e-11"),
    },
    "demo12": {
        "gms_file": "TIMES_source/model/demo12.run",
        "idir1": "TIMES_source/source",
        "idir2": "TIMES_source/model",
        "download_url": "",  # Already in .git,
        "solve": "SOLVE",
    },
    "demo12_damage": {
        "gms_file": "src/data/Demo12Damage/demo12_damage.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/Demo12Damage",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/Demo12Damage.zip",
        "solve": "SOLVE",
    },
    "demo12Base": {
        "gms_file": "src/data/Demo12Base/demo12base.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/Demo12Base",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/Demo12Base.zip",
        "solve": "SOLVE",
    },
    # reaches: ucbet_vda.py (UC_ACTBET -> UC_FLOBET -> UcbetVda inclusion)
    "demo12Base_ucbet": {
        "gms_file": "src/data/Demo12Base/demo12base_ucbet.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/Demo12Base",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/Demo12Base.zip",
        "solve": "SOLVE",
    },
    "demo12BaseMLF": {
        "gms_file": "src/data/Demo12BaseMLF/demo12mlf-baserep.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/Demo12BaseMLF",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/Demo12BaseMLF.zip",
        "solve": "SOLVE",
    },
    "demo12BaseMLF_csa": {
        "gms_file": "src/data/Demo12BaseMLF/demo12mlf-baserep_csa.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/Demo12BaseMLF",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/Demo12BaseMLF.zip",
        "solve": "SOLVE",
        # MSA/CSA's MACRO calibration (solvcoef_msa.py/mod_vars_msa.py) is
        # natively translated, so it no longer runs byte-identical GAMS text
        # against the reference -- algebraically-equivalent but differently
        # ordered floating-point arithmetic produces expected ULP-level
        # drift (observed ~1e-9 relative, e.g. TM_GROWV) that cascades into
        # every symbol downstream of the calibration. Both sides solve to
        # the exact same objective value, confirming the model itself is
        # unaffected. RelEps tolerates that drift for normal-magnitude
        # values; Eps (absolute) is needed on top because some LP marginals
        # sit at a near-degenerate ~0 (e.g. 1.35E-10 vs 3.47E-11) where a
        # purely relative comparison blows up despite both sides being
        # noise. A real regression would produce differences many orders of
        # magnitude larger than either tolerance.
        "gdxdiff_releps": "1e-6",
        "gdxdiff_eps": "1e-6",
    },
    "AdvDemo": {
        "gms_file": "src/data/AdvDemo/ademoref_1w.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/AdvDemo",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/AdvDemo.zip",
    },
    "PowFlow": {
        "gms_file": "src/data/PowFlow/powflodaylp.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/PowFlow",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/PowFlow.zip",
    },
    "SWEBAS": {
        "gms_file": "src/data/SWEBAS/swebasmall.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/SWEBAS",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/SWEBAS.zip",
    },
    "TimeStep": {
        "gms_file": "src/data/TimeStep/fod0550d.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/TimeStep",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/TimeStep.zip",
    },
    "StochDemosStoc": {
        "gms_file": "src/data/StochDemos/demos7-stoc.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/StochDemos",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/StochDemos.zip",
        "solve": "SOLVE",
    },
    "StochDemosSensi": {
        "gms_file": "src/data/StochDemos/demos7-sensi.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/StochDemos",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/StochDemos.zip",
        "solve": "SOLVE",
    },
    "StochDemosSpine": {
        "gms_file": "src/data/StochDemos/demos7-spine.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/StochDemos",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/StochDemos.zip",
        "solve": "SOLVE",
    },
    "PhilipCase": {
        "gms_file": "src/data/PhilipCase/myph10.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/PhilipCase",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/PhilipCase.zip",
    },
    "GridDemo": {
        "gms_file": "src/data/GridDemo/gasPOWDAY.run",
        "idir1": "TIMES_source/source",
        "idir2": "src/data/GridDemo",
        "download_url": "https://cloud.gams.com/remote.php/dav/files/816c3582-e7f4-103c-8f90-d5e89bc61045/TIMES_GAMSPy_Instances/GridDemo.zip",
    },
}

# Assuming gamspy_base.directory is where your GAMS binaries live
GAMS_BIN_DIR = Path(gamspy_base.directory)


def run_gdxdiff(
    file1: Path,
    file2: Path,
    diff_file: Path,
    releps: str | None = None,
    eps: str | None = None,
) -> int:
    """
    Runs gdxdiff. If differences exist, it returns the RC.
    """

    # 1. Dump the symbols from the GAMSPy GDX file (file2)
    dump_result = subprocess.run(
        [GAMS_BIN_DIR / "gdxdump", str(file2), "symbols"],
        capture_output=True,
        text=True,
        check=True,  # Raises an exception if gdxdump fails
    )

    # 2. Parse the output
    skip_ids = [
        "VAS_EXPOBJ",  # declared but not defined in GAMS
        "EQ_OBJ",  # TODO: waiting for dependency gamspy equations bounds
        "EQ_UTIL",  # TODO: waiting for dependency gamspy equations bounds
        "EQ_UTILP",  # TODO: waiting for dependency gamspy equations bounds
        "DUR_MAX",  # time measure
        # Layout scratch for the DUMPSOL plaintext dump, declared only in
        # dumpsol1.mod / dumpsolv.mod (e.g. `scalar colcnt;` paginates columns at
        # 19 per block). The GAMSPy translation builds the same dump with pandas
        # instead of emitting these helpers, so they exist on the GAMS side only.
        # They hold no model content -- verified to appear in no other TIMES
        # source file.
        "col",
        "colcnt",
        "row3",
        "row4",
        "row5a",
        "row6a",
        "row7a",
        "u1",
        "u5",
        "u6",
        "u7",
        "u8",
        "u9",
        # calibase.mlf (demo12BaseMLF) declares TM_TOL with a literal data
        # list and later reassigns TM_TOL('DEM')/('GDP') at runtime inside
        # its Negishi/MSA calibration loop. `$gdxUnload` (used for
        # %COMPILE_GDX%) is a compile-time-only GAMS command -- verified via
        # an isolated repro, it fires during compilation, before ANY
        # execution statement runs, regardless of its textual position in
        # the source -- so it can never see that runtime reassignment and
        # always reports TM_TOL without DEM/GDP. GAMSPy's compile GDX is
        # written only after the whole pipeline (including this loop) has
        # already executed, so it always has the real (co-)computed value.
        # This is a permanent asymmetry between what "compile phase" means
        # in each engine for a literal-then-reassigned symbol, not a
        # translation bug and not fixable in calibase_mlf.py -- it's a
        # structural "Keys are different", so RelEps can't cover it either.
        # (Convert/execute already match without this skip -- both use
        # execute_unload, which reflects full runtime state on both sides.)
        "TM_TOL",
        # LOADSOLUTION's guarded `Parameter savepointModelstat;` (solve.mod)
        # carries the faked modelstat between execute_unload/execute_load; on
        # the GAMS side it's compiled as part of the monolithic .run file
        # before any solve, so it's already present at --COMPILE_GDX= time.
        # GAMSPy's equivalent declaration is added via addGamsCode inside a
        # tc.enqueue'd (deferred) function, which only runs in the "run"
        # phase -- after output_compile is already written -- so it's absent
        # from compile_gamspy's GDX. Pure plumbing, never a real model result.
        "savepointModelstat",
        # RptmiscRpt's `_once_set()` (rptmisc_rpt.py) declares a dedicated
        # singleton driver Set purely to give a one-pass Loop() a domain --
        # not a TIMES model set, no GAMS-source equivalent, holds no model
        # content. Pure GAMSPy-side plumbing.
        "RPTMISC_ONCE",
    ]
    lines = dump_result.stdout.splitlines()

    # Slice from [1:] to skip the header line (mimicking `sed '1d'`)
    for line in lines[1:]:
        parts = line.split()
        # Scan the columns for the symbol name.
        for token in parts:
            if (
                token.startswith(("autogenerated", "autotemp", "violations"))
                or token == "Z"
            ):
                skip_ids.append(token)
                break

    # 3. Construct the gdxdiff command
    cmd = [GAMS_BIN_DIR / "gdxdiff", str(file1), str(file2), str(diff_file)]

    if skip_ids:
        for id in skip_ids:
            cmd.append(f"SkipID={id}")

    if releps:
        cmd.append(f"RelEps={releps}")

    if eps:
        cmd.append(f"Eps={eps}")

    # 4. Run the diff
    result = subprocess.run(
        cmd,  # type: ignore
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"\n--- GDXDIFF SUMMARY FOR {diff_file.name} ---")
        # gdxdiff prints a summary table to stdout/stderr
        print(result.stdout)
        print(result.stderr)

    return result.returncode


@pytest.fixture(scope="module", params=TEST_INSTANCES.keys())
def generate_models(request: pytest.FixtureRequest) -> dict[str, Path]:
    """
    Module-scoped fixture. This code runs exactly ONCE per instance.
    It generates the GAMS and GAMSPy models and yields their file paths to the tests.
    """
    macro_config.reset()

    instance_name = request.param
    gams_config = TEST_INSTANCES[instance_name]
    gamspy_config: RunConfig = REGISTRY[instance_name]

    # Fetch data if necessary
    if gams_config["download_url"]:
        ensure_nextcloud_data(
            instance_name=instance_name,
            webdav_url=gams_config["download_url"],
            extract_directory=gams_config["idir2"],
        )

    test_dir = Path("test_output", instance_name)
    test_dir.mkdir(parents=True, exist_ok=True)

    compile_gamspy_gdx = test_dir / f"compile_gamspy_{instance_name.lower()}.gdx"
    execute_gamspy_gdx = test_dir / f"execute_gamspy_{instance_name.lower()}.gdx"
    convert_gamspy_gdx = test_dir / f"convert_gamspy_{instance_name.lower()}.gdx"

    solvemode = "SOLVE" if "solve" in gams_config else "LOADSOLUTION"

    # 1. Ensure the GAMS reference GDX files exist (see .ci/gams_cache.py):
    # generates and caches via Nextcloud whatever's missing, including the
    # per-instance LOADSOLUTION savepoint.
    compile_gams_gdx, execute_gams_gdx, convert_gams_gdx = ensure_reference_gdx(
        instance_name=instance_name,
        gams_config=gams_config,
        gamspy_config=gamspy_config,
        test_dir=test_dir,
    )

    # 2. Run GAMSPy (happens once per model)
    start = perf_counter()
    run_gamspy(
        output_compile=compile_gamspy_gdx,
        output_execute=execute_gamspy_gdx,
        output_convert=convert_gamspy_gdx,
        config=gamspy_config,
        solve=solvemode == "SOLVE",
    )
    gamspy_time = perf_counter() - start

    print(f"GAMSPy Performance: {round(gamspy_time, 2)} secs.")

    # 3. Return the paths for the tests to use
    return {
        "test_dir": test_dir,
        "instance_name": Path(instance_name),
        "compile_gams": compile_gams_gdx,
        "compile_gamspy": compile_gamspy_gdx,
        "execute_gams": execute_gams_gdx,
        "execute_gamspy": execute_gamspy_gdx,
        "convert_gams": convert_gams_gdx,
        "convert_gamspy": convert_gamspy_gdx,
    }


def test_times_pipeline(generate_models: dict[str, Path]) -> None:
    """
    Tests the Compile, Convert, and Execute phases for a given model.
    Evaluates all phases before asserting so all debug diffs are generated.
    VS Code will neatly group this as test_times_pipeline -> [instance_name].
    """
    paths = generate_models
    errors = []
    instance = paths["instance_name"].name
    releps = TEST_INSTANCES[instance].get("gdxdiff_releps")
    eps = TEST_INSTANCES[instance].get("gdxdiff_eps")

    # 1. Test Compile Phase
    compile_dif = paths["test_dir"] / f"compile_dif_{instance}.gdx"
    rc_compile = run_gdxdiff(
        paths["compile_gams"], paths["compile_gamspy"], compile_dif, releps, eps
    )
    if rc_compile != 0:
        errors.append(f"Compile GDX files differ. Check CI artifacts in {compile_dif}")

    # 2. Test Convert Phase (Algebra and Equations)
    convert_dif = paths["test_dir"] / f"convert_dif_{instance}.gdx"
    rc_convert = run_gdxdiff(
        paths["convert_gams"], paths["convert_gamspy"], convert_dif, releps, eps
    )
    if rc_convert != 0:
        errors.append(f"Convert GDX files differ. Check CI artifacts in {convert_dif}")

    # 3. Test Execute Phase (Final Solved Values)
    execution_dif = paths["test_dir"] / f"execution_dif_{instance}.gdx"
    rc_execute = run_gdxdiff(
        paths["execute_gams"], paths["execute_gamspy"], execution_dif, releps, eps
    )
    if rc_execute != 0:
        errors.append(
            f"Execution GDX files differ. Check CI artifacts in {execution_dif}"
        )

    # 4. Final Assertion
    assert not errors, "\n".join(errors)
