# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
# -----------------------------------------------------------------------------#
# IMPORT GENERIC UTILS
# -----------------------------------------------------------------------------#
from build_ppt import convert_md_to_ppt
from timekeeper_utils import (
    convert_date,
    set_default_cutoff_dates,
    get_service_requests,
    add_forms,
    sort_service_requests,
    convert_sr_to_md,
    format_response)

# -----------------------------------------------------------------------------#
# SET ENV VARS
# -----------------------------------------------------------------------------#
# dotenv_path = Path.cwd() / "env" / ".ilab.env"
# Yes I know this is hardcoded - will change later
dotenv_path = (Path(__file__).resolve().parent / "../env/.env").resolve()
load_dotenv(dotenv_path=dotenv_path)


API_KEY = os.getenv("API_KEY", "")
BASE_URL = os.getenv("BASE_URL", "")
CORE_ID = os.getenv("CORE_ID", "")
CORE_NAME = os.getenv("CORE_NAME", "")


TO_DATE = os.getenv("TO_DATE", "today")
converted_date = convert_date(os.getenv("FROM_DATE", "7days"))
DATE_RANGE = set_default_cutoff_dates(TO_DATE, converted_date)


# -----------------------------------------------------------------------------#
# DEFINE ILAB HEADERS
# -----------------------------------------------------------------------------#
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# -----------------------------------------------------------------------------#
# CRON 
# -----------------------------------------------------------------------------#



# -----------------------------------------------------------------------------#
# DEFINE ARGUMENTS FOR TESTING
# -----------------------------------------------------------------------------#
def parse_args():
    parser = argparse.ArgumentParser(
        description="iLab API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python timekeeper.py --outfile file_out --build_report
        """,
    )
    parser.add_argument(
        "--outfile",
        required=True,
        type=str,
        help=(
            "Output file location "
            "if none provide default names will be used in current directory."
        ),
    )
    parser.add_argument(
        "--build_report",
        action="store_true",
        help="Should the full report be built? Used for testing purposes",
    )
    parser.add_argument(
        "--export_request",
        action="store_true",
        help="Export the full API request as json",
    )
    parser.add_argument(
        "--export_summary",
        action="store_true",
        help="Export the summary table (base fields + type) as csv",
    )

    return parser.parse_args()


# -----------------------------------------------------------------------------#
# ENTRY
# -----------------------------------------------------------------------------#
if __name__ == "__main__":
    args = parse_args()
    outfile = args.outfile
    build_report = args.build_report
    export_requests = args.export_request
    export_summary = args.export_summary

    # Let's get this party started.
    service_requests = get_service_requests(BASE_URL,HEADERS, CORE_ID,DATE_RANGE)
    service_requests = add_forms(service_requests,HEADERS)
    service_requests = sort_service_requests(service_requests) 

    sorted_df = format_response(service_requests)
    
    if export_requests:
        with open(f"{outfile}_sorted_requests.json",'w') as f:
            json.dump(service_requests, f)
    if export_summary:
        sorted_df.to_csv(f"{outfile}_summary.csv", index=False)
    if build_report:
        convert_sr_to_md(service_requests, outfile)
        convert_md_to_ppt(f"{outfile}.md", f"{outfile}.pptx")
