"""
fetch_refs.py — fetch Wikipedia refs, chunk them into per-country parquet files.

Repository layout:
    data/latam.csv                              input: page_id, iso3166
    data/refs/<ISO>/part-NNNNN.parquet          output: ≤ 2000 rows each
    data/failures/<ISO>.csv                     one row per failed page
    data/fetch_state.csv                        resume ledger

Usage:
    python code/fetch_refs.py

The script is resumable: re-run it and it will skip pages already
marked as attempted in data/fetch_state.csv.

Repository: https://github.com/silviaegt/wiki-latam-refs

Authorship note:
    This module was developed in collaboration with DeepSeek (DeepSeek-V3).
    The design, methodology, and scientific goals are original work by Silvia Gutiérrez. 
    The language model was used as a coding assistant, not as the
    originator of the research logic.
"""
from pathlib import Path
import sys
import time
from datetime import datetime

import pandas as pd

# ------------------------------------------------------------------ #
# CRITICAL: disable pyarrow-backed strings BEFORE touching parquet.
# ------------------------------------------------------------------ #
pd.set_option("mode.string_storage", "python")
pd.set_option("future.infer_string", False)

from tqdm.auto import tqdm

# Make `refdb` importable when the script is run from the repo root
# or from inside `code/`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from refdb import extract  # noqa: E402

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
# All paths are relative to the repository root.
# This makes the script runnable from anywhere inside the repo.
REPO_ROOT         = Path(__file__).resolve().parent.parent

INPUT_CSV         = REPO_ROOT / "data" / "latam.csv"
ROOT              = REPO_ROOT / "data" / "refs"
FAIL_DIR          = REPO_ROOT / "data" / "failures"
STATE_FILE        = REPO_ROOT / "data" / "fetch_state.csv"

ROWS_PER_FILE     = 2000
SLEEP             = 0.1
STATE_FLUSH_EVERY = 200
PARQUET_ENGINE    = "fastparquet"


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def write_parquet(df: pd.DataFrame, path: Path) -> None:
    df.to_parquet(path, index=False, engine=PARQUET_ENGINE)


def read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path, engine=PARQUET_ENGINE)


def append_csv(df: pd.DataFrame, path: Path) -> None:
    """Append rows to a CSV, creating it if it doesn't exist."""
    if df.empty:
        return
    header = not path.exists()
    df.to_csv(path, mode="a", header=header, index=False)


def append_state(rows: list[dict], path: Path) -> None:
    """Append state rows to the ledger CSV."""
    if not rows:
        return
    df = pd.DataFrame(rows)
    header = not path.exists()
    df.to_csv(path, mode="a", header=header, index=False)


# ------------------------------------------------------------------ #
# 0. Work slice — flip between these two lines
# ------------------------------------------------------------------ #
# latam_work = latam.head(50).copy()      # ← smoke test
latam_work = pd.read_csv(INPUT_CSV)


# ------------------------------------------------------------------ #
# 1. Resume state
# ------------------------------------------------------------------ #
ROOT.mkdir(parents=True, exist_ok=True)
FAIL_DIR.mkdir(parents=True, exist_ok=True)

if STATE_FILE.exists():
    state = pd.read_csv(STATE_FILE)
    done = set(zip(state["page_id"], state["iso3166"]))
    print(f"resuming: {len(done)} (page_id, iso) pairs already attempted")
else:
    done = set()
    print("starting fresh")

pending = latam_work[
    ~latam_work.apply(lambda r: (r["page_id"], r["iso3166"]) in done, axis=1)
].copy()

print(f"{len(pending)} pages to fetch across "
      f"{pending['iso3166'].nunique()} countries\n")


# ------------------------------------------------------------------ #
# 2. Fetch, chunk, write
# ------------------------------------------------------------------ #
def flush_state(state_buf: list[dict]) -> None:
    """Write state rows to disk, clear the buffer."""
    if state_buf:
        append_state(state_buf, STATE_FILE)
        state_buf.clear()


try:
    for iso, group in pending.groupby("iso3166", dropna=False):
        key     = str(iso) if pd.notna(iso) else "UNKNOWN"
        out_dir = ROOT / key
        out_dir.mkdir(exist_ok=True)

        existing = sorted(out_dir.glob("part-*.parquet"))
        chunk_no = len(existing) + 1

        buf       = []
        buf_size  = 0
        state_buf = []
        total     = len(group)

        print(f"\n=== {key}  ({total} pages) ===")
        bar = tqdm(group.itertuples(index=False),
                   total=total,
                   desc=f"{key:<8}",
                   unit="pg")

        for row in bar:
            pid = int(row.page_id)
            try:
                df = extract(pageid=pid)
                if not df.empty:
                    df = df.copy()
                    df["iso3166"] = key
                    buf.append(df)
                    buf_size += len(df)
                state_buf.append({
                    "page_id": pid, "iso3166": key, "status": "ok",
                    "ts": datetime.utcnow().isoformat(timespec="seconds"),
                })
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                append_csv(
                    pd.DataFrame([{
                        "page_id": pid, "iso3166": key, "error": err,
                        "ts": datetime.utcnow().isoformat(timespec="seconds"),
                    }]),
                    FAIL_DIR / f"{key}.csv",
                )
                state_buf.append({
                    "page_id": pid, "iso3166": key, "status": "fail",
                    "ts": datetime.utcnow().isoformat(timespec="seconds"),
                })

            # flush a parquet chunk when the buffer is full
            if buf_size >= ROWS_PER_FILE:
                df_chunk = pd.concat(buf, ignore_index=True)
                write_parquet(df_chunk, out_dir / f"part-{chunk_no:05d}.parquet")
                chunk_no += 1
                buf = []
                buf_size = 0

            # flush state ledger periodically
            if len(state_buf) >= STATE_FLUSH_EVERY:
                flush_state(state_buf)

            time.sleep(SLEEP)

        # end of country: flush remaining buf and state
        if buf:
            df_chunk = pd.concat(buf, ignore_index=True)
            write_parquet(df_chunk, out_dir / f"part-{chunk_no:05d}.parquet")
        flush_state(state_buf)

except KeyboardInterrupt:
    print("\ninterrupted — flushing current buffers")
    try:
        if buf:
            df_chunk = pd.concat(buf, ignore_index=True)
            write_parquet(df_chunk, out_dir / f"part-{chunk_no:05d}.parquet")
    except NameError:
        pass
    try:
        flush_state(state_buf)
    except NameError:
        pass


# ------------------------------------------------------------------ #
# 3. Summary
# ------------------------------------------------------------------ #
print("\n--- summary ---")
grand_total = 0
for iso_dir in sorted(ROOT.iterdir()):
    if iso_dir.is_dir():
        files = sorted(iso_dir.glob("part-*.parquet"))
        rows = sum(read_parquet(f).shape[0] for f in files)
        grand_total += rows
        print(f"  {iso_dir.name:<8}  {len(files):>3} files  {rows:>7} rows")
print(f"  {'TOTAL':<8}  {'':>3}        {grand_total:>7} rows")
