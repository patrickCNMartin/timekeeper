# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from build_ppt import convert_md_to_ppt
from format_convert import convert_sr_to_md
from request_utils import (
    filter_service_requests,
    get_cores,
    get_request_description,
    get_request_info,
    select_service_request,
    full_sr
)


# -----------------------------------------------------------------------------#
# IMPORT GENERIC UTILS
# -----------------------------------------------------------------------------#
from timekeeper_utils import convert_date, set_default_cutoff_dates

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


FILTER_CRITERIA = json.loads(os.getenv("FILTER_CRITERIA", "{}"))

rt = os.getenv("REQUEST_TYPE")
REQUEST_TYPE = json.loads(rt) if rt else ["new"]

# -----------------------------------------------------------------------------#
# DEFINE ILAB HEADERS
# -----------------------------------------------------------------------------#
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# -----------------------------------------------------------------------------#
# DEFINE ARGUMENTS
# -----------------------------------------------------------------------------#
def parse_args():
    parser = argparse.ArgumentParser(
        description="iLab API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python ilab_api.py --outfile file_out --build_report
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

    return parser.parse_args()


# -----------------------------------------------------------------------------#
# ENTRY
# -----------------------------------------------------------------------------#
if __name__ == "__main__":
    args = parse_args()
    # need to update this function
    if CORE_ID is None or CORE_ID == "":
        CORE_ID = get_cores(BASE_URL, HEADERS, "id")

    # Require args 
    outfile = args.outfile
    # API filtering is limited
    # Function does addition filtering based on post request json
    service_requests = select_service_request(
        BASE_URL, HEADERS, CORE_ID, DATE_RANGE, filters=FILTER_CRITERIA
    )
    # Adds custom form to each service request and dumps the lot.
    full = full_sr(service_requests, HEADERS)
    with open(f"{outfile}_full.json", "w") as f:
        json.dump(full,f)
        
    # Not ideal but for now I don't care to much about it
    if args.export_request:
        with open(f"{outfile}.json", "w") as f:
            json.dump(service_requests, f)
    else:
        # Start from a clean md so a rerun does not stack onto the last report
        Path(f"{outfile}.md").unlink(missing_ok=True)
        # Loop over request types to create a multi-type report
        # This will append to the same md file
        for rt in REQUEST_TYPE:
            # import pdb;pdb.set_trace()
            current_requests = filter_service_requests(service_requests, rt)
            # Pull information from request
            request_info = [get_request_info(i) for i in current_requests]
            # Pull Desription
            request_description = [
                get_request_description(
                    i,
                    HEADERS,
                    rt,
                )
                for i in current_requests
            ]
            convert_sr_to_md(request_info, request_description, rt, outfile)
        if args.build_report:
            convert_md_to_ppt(f"{outfile}.md", f"{outfile}.pptx")
