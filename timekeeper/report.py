# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import tempfile
from datetime import date
from pathlib import Path

# -----------------------------------------------------------------------------#
# IMPORT GENERIC UTILS
# -----------------------------------------------------------------------------#
from build_ppt import convert_md_to_ppt
from timekeeper_utils import (
    add_forms,
    convert_sr_to_md,
    filter_by_submitted_date,
    format_response,
    get_service_requests,
    set_default_cutoff_dates,
    sort_service_requests,
)

# -----------------------------------------------------------------------------#
# DEFINE GLOBAL VARS
# -----------------------------------------------------------------------------#
BASE_URL = "https://api-eu.ilabsolutions.com/v1/cores"

# The API date search runs on a creation date it does not return, not on
# submitted_at: query a wide range, then filter on submitted_at ourselves
QUERY_DAYS = 360


# -----------------------------------------------------------------------------#
# REPORT
# -----------------------------------------------------------------------------#
def run_report(
    api_key: str, core_id: str, core_name: str, out_dir: str, days: int
) -> tuple[Path, Path]:
    """Pull the requests submitted in the last `days` days and save them as
    <out_dir>/core_meeting_<today>.pptx and .csv"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    query_range = set_default_cutoff_dates("today", {"days": max(QUERY_DAYS, days)})
    filter_range = set_default_cutoff_dates("today", {"days": days})

    service_requests = get_service_requests(BASE_URL, headers, core_id, query_range)
    queried = len(service_requests)
    service_requests = filter_by_submitted_date(service_requests, filter_range)
    print(f"Queried {queried} requests, {len(service_requests)} submitted in the last {days} days")
    service_requests = add_forms(service_requests, headers)
    sorted_requests = sort_service_requests(service_requests)

    out = Path(out_dir) / f"core_meeting_{date.today():%Y-%m-%d}"
    csv_path = out.with_suffix(".csv")
    pptx_path = out.with_suffix(".pptx")
    # utf-8-sig so Excel shows accented names correctly
    format_response(sorted_requests).to_csv(csv_path, index=False, encoding="utf-8-sig")
    # The slides are built from an intermediate md that we don't keep
    with tempfile.TemporaryDirectory() as tmp:
        md_stem = Path(tmp) / "report"
        convert_sr_to_md(sorted_requests, str(md_stem))
        convert_md_to_ppt(f"{md_stem}.md", str(pptx_path), core_name)
    return pptx_path, csv_path
