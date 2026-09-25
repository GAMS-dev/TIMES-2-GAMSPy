import logging
import subprocess
from pathlib import Path

import gamspy_base  # type: ignore[import-untyped]
import pandas as pd
import pytest

from core.pp_qaput_mod import QALogger, pp_qaput

GAMS_BIN_DIR = Path(gamspy_base.directory)
PP_QAPUT_SOURCE = (
    Path(__file__).resolve().parents[1] / "TIMES_source" / "source" / "pp_qaput.mod"
)

MESSAGE_TEMPLATE = "WARNING       - Test violation:   P={P}"
PRODUCTS = ["P1", "P2", "P3"]


def _run_pp_qaput_via_gams(tmp_path: Path, err_level: int, group_desc: str) -> str:
    """
    Runs the real pp_qaput.mod (via $BATINCLUDE) through real GAMS, standalone,
    and returns the resulting QLOG text. Mirrors the FILE/SCALAR declarations
    the real driver uses (TIMES_source/source/ppmain.mod:13-14, pp_qack.mod:36-40).
    """
    (tmp_path / "pp_qaput.mod").write_text(PP_QAPUT_SOURCE.read_text())
    gms_file = tmp_path / "probe.gms"
    gms_file.write_text(
        "SETS P / P1, P2, P3 /;\n"
        "FILE QLOG / qa_check.log /;  QLOG.LW = 0;\n"
        "SCALARS PUTOUT / 0 /, PUTGRP / 0 /, ERRLEV / 0 /;\n"
        "PUT QLOG;  QLOG.NW = 10; QLOG.ND = 2; QLOG.PW = 150;\n"
        "LOOP(P,\n"
        f"$  BATINCLUDE pp_qaput.mod PUTOUT PUTGRP {err_level} '{group_desc}'\n"
        "   PUT QLOG ' WARNING       - Test violation:   P=', P.TL;\n"
        ");\n"
        "PUTCLOSE QLOG;\n"
    )
    subprocess.run(
        [str(GAMS_BIN_DIR / "gams"), "probe.gms", "lo=0"],
        cwd=tmp_path,
        check=True,
    )
    return (tmp_path / "qa_check.log").read_text()


def _run_qalogger(
    caplog: pytest.LogCaptureFixture, err_level: int, group_desc: str
) -> list[str]:
    caplog.set_level(logging.WARNING)
    violations = pd.DataFrame({"P": PRODUCTS})
    QALogger().log_violations(
        violations_df=violations,
        err_level=err_level,
        group_desc=group_desc,
        message_template=MESSAGE_TEMPLATE,
    )
    return [record.getMessage() for record in caplog.records]


@pytest.mark.parametrize("err_level", [1, 10])
def test_qalogger_output_matches_real_gams(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, err_level: int
) -> None:
    group_desc = f"Test Group Level{err_level}"

    gams_text = _run_pp_qaput_via_gams(tmp_path, err_level, group_desc)
    gams_lines = {line.strip() for line in gams_text.splitlines() if line.strip()}

    python_messages = _run_qalogger(caplog, err_level, group_desc)
    python_lines = {
        line.strip()
        for message in python_messages
        for line in message.splitlines()
        if line.strip()
    }

    header = f"*** {group_desc}"
    assert header in gams_lines
    assert header in python_lines

    level_code = f"*{min(99, err_level):02d}"
    for product in PRODUCTS:
        expected_line = f"{level_code} WARNING       - Test violation:   P={product}"
        assert expected_line in gams_lines
        assert expected_line in python_lines


def test_log_violations_noop_on_empty_or_none(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    qa_logger = QALogger()

    qa_logger.log_violations(
        violations_df=None,
        err_level=1,
        group_desc="Unused Group",
        message_template=MESSAGE_TEMPLATE,
    )
    qa_logger.log_violations(
        violations_df=pd.DataFrame({"P": []}),
        err_level=1,
        group_desc="Unused Group",
        message_template=MESSAGE_TEMPLATE,
    )

    assert caplog.records == []
    assert qa_logger.seen_groups == set()
    assert qa_logger.max_err_level == 0


def test_log_violations_group_header_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    qa_logger = QALogger()
    violations = pd.DataFrame({"P": ["P1"]})

    qa_logger.log_violations(
        violations_df=violations,
        err_level=1,
        group_desc="Group A",
        message_template=MESSAGE_TEMPLATE,
    )
    qa_logger.log_violations(
        violations_df=violations,
        err_level=1,
        group_desc="Group A",
        message_template=MESSAGE_TEMPLATE,
    )
    qa_logger.log_violations(
        violations_df=violations,
        err_level=1,
        group_desc="Group B",
        message_template=MESSAGE_TEMPLATE,
    )

    headers = [
        record.getMessage() for record in caplog.records if "***" in record.getMessage()
    ]
    assert len(headers) == 2
    assert "Group A" in headers[0]
    assert "Group B" in headers[1]


def test_log_violations_tracks_max_err_level() -> None:
    qa_logger = QALogger()
    violations = pd.DataFrame({"P": ["P1"]})

    qa_logger.log_violations(
        violations_df=violations,
        err_level=1,
        group_desc="Group A",
        message_template=MESSAGE_TEMPLATE,
    )
    assert qa_logger.max_err_level == 1

    qa_logger.log_violations(
        violations_df=violations,
        err_level=10,
        group_desc="Group B",
        message_template=MESSAGE_TEMPLATE,
    )
    assert qa_logger.max_err_level == 10

    qa_logger.log_violations(
        violations_df=violations,
        err_level=1,
        group_desc="Group C",
        message_template=MESSAGE_TEMPLATE,
    )
    assert qa_logger.max_err_level == 10


def test_pp_qaput_omits_errlev_line_when_arg3_is_star() -> None:
    code = pp_qaput("PUTOUT", "PUTGRP", "*", "ALL QUALITY CHECKS PASSED ***")

    assert "ALL QUALITY CHECKS PASSED ***" in code
    assert "ERRLEV" not in code


def test_pp_qaput_includes_errlev_line_for_numeric_level() -> None:
    code = pp_qaput("PUTOUT", "PUTGRP", "01", "Some QA check")

    assert "Some QA check" in code
    assert "ERRLEV$(01>ERRLEV)=01;" in code
