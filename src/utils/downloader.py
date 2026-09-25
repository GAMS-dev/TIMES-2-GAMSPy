import base64
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from filelock import FileLock


def _nextcloud_headers() -> dict[str, str]:
    """Basic-auth header for Nextcloud WebDAV (Format: "user:app_password")."""
    nc_creds = os.environ.get("NEXTCLOUD_CREDS")
    if not nc_creds:
        print(
            "WARNING: NEXTCLOUD_CREDS environment variable not set. Request may fail."
        )
        return {}
    base64_creds = base64.b64encode(nc_creds.encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {base64_creds}"}


def ensure_nextcloud_data(
    instance_name: str, webdav_url: str, extract_directory: str
) -> None:
    """Downloads and extracts large dataset from a secure Nextcloud WebDAV share."""
    extract_dir = Path(extract_directory)

    # Several instances (e.g. the DemoS_012e/DemoS_007b variants) share the same
    # extract_directory. Serialize the check-then-extract section per directory so
    # concurrent test workers don't extract into it at the same time.
    lock_path = extract_dir.parent / f".{extract_dir.name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(lock_path)):
        _ensure_nextcloud_data_locked(instance_name, webdav_url, extract_dir)


def _ensure_nextcloud_data_locked(
    instance_name: str, webdav_url: str, extract_dir: Path
) -> None:
    # If the folder already has files, assume it's cached and skip the download
    if extract_dir.exists() and any(extract_dir.glob("*.dd")):
        print(f"\nData for {instance_name} already exists. Skipping download.")
        return

    print(f"\nDownloading {instance_name} data from Nextcloud...")

    req = urllib.request.Request(webdav_url, headers=_nextcloud_headers())

    zip_path = Path(f"{instance_name}_temp.zip")

    # Download the file
    with urllib.request.urlopen(req) as response, open(zip_path, "wb") as out_file:
        out_file.write(response.read())

    print(f"Extracting {instance_name} data into {extract_dir}...")
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    # Clean up the zip file
    zip_path.unlink()
    print("Download and extraction complete.")


def upload_gams_gdx_to_zip(
    webdav_url: str, extract_directory: str, *paths: Path
) -> None:
    """Adds freshly-generated GAMS reference GDX files as new entries in the
    instance's Nextcloud data zip (the same zip `ensure_nextcloud_data`
    downloads), so future runs find them already extracted in idir2 and can
    skip regenerating them via GAMS.

    Mirrors the safety pattern of
    .claude/skills/add-times-instance/scripts/sync_nextcloud_run_file.py:
    download + local backup, append-only (never touches existing entries),
    verify zip integrity and that every pre-existing entry stayed
    byte-identical, upload, then re-download and re-verify against the live
    file. This modifies a shared resource every teammate's CI relies on, so a
    cache miss here just means the next run regenerates via GAMS as before --
    never a correctness dependency, only a performance one.

    Several instances can share one zip (e.g. all DemoS_012e variants), so
    this is serialized with the same per-extract_directory lock
    `ensure_nextcloud_data` uses, to avoid two concurrent uploads clobbering
    each other's new entries.
    """
    if not webdav_url:
        return

    extract_dir = Path(extract_directory)
    lock_path = extract_dir.parent / f".{extract_dir.name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(lock_path)):
        _upload_gams_gdx_to_zip_locked(webdav_url, paths)


def _upload_gams_gdx_to_zip_locked(webdav_url: str, paths: tuple[Path, ...]) -> None:
    with tempfile.TemporaryDirectory(prefix="nextcloud_gdx_sync_") as scratch_dir:
        scratch = Path(scratch_dir)
        original_zip = scratch / "original.zip"
        updated_zip = scratch / "updated.zip"

        req = urllib.request.Request(webdav_url, headers=_nextcloud_headers())
        with urllib.request.urlopen(req) as response, open(original_zip, "wb") as f:
            f.write(response.read())
        updated_zip.write_bytes(original_zip.read_bytes())

        orig = zipfile.ZipFile(original_zip)
        with zipfile.ZipFile(updated_zip, "a", zipfile.ZIP_DEFLATED) as z:
            existing = set(z.namelist())
            # Another worker may have already uploaded some/all of these
            # (e.g. a sibling instance sharing this zip) between our cache
            # check and acquiring the lock -- only add what's still missing.
            new_paths = [p for p in paths if p.name not in existing]
            for p in new_paths:
                z.writestr(p.name, p.read_bytes())

        if not new_paths:
            return

        upd = zipfile.ZipFile(updated_zip)
        if upd.testzip() is not None:
            raise RuntimeError("Updated GAMS reference GDX zip failed integrity check")
        mismatches = [n for n in orig.namelist() if orig.read(n) != upd.read(n)]
        if mismatches:
            raise RuntimeError(
                f"Refusing to upload -- pre-existing zip entries changed: {mismatches}"
            )

        put_req = urllib.request.Request(
            webdav_url,
            data=updated_zip.read_bytes(),
            method="PUT",
            headers={**_nextcloud_headers(), "Content-Type": "application/zip"},
        )
        urllib.request.urlopen(put_req)

        # Re-download and re-verify against the live state.
        live_zip = scratch / "live_check.zip"
        req = urllib.request.Request(webdav_url, headers=_nextcloud_headers())
        with urllib.request.urlopen(req) as response, open(live_zip, "wb") as f:
            f.write(response.read())
        live = zipfile.ZipFile(live_zip)
        if live.testzip() is not None:
            raise RuntimeError("Live GAMS reference GDX zip failed integrity check")
        for p in new_paths:
            if live.read(p.name) != p.read_bytes():
                raise RuntimeError(f"Live content mismatch for {p.name} after upload")
        live_mismatches = [n for n in orig.namelist() if orig.read(n) != live.read(n)]
        if live_mismatches:
            raise RuntimeError(
                f"Live zip altered pre-existing entries: {live_mismatches}"
            )
