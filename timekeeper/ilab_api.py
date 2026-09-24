# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

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
from utils import convert_date, set_default_cutoff_dates

# -----------------------------------------------------------------------------#
# SET ENV VARS
# -----------------------------------------------------------------------------#
# dotenv_path = Path.cwd() / "env" / ".ilab.env"
# Yes I know this is hardcoded - will change later
dotenv_path = (Path(__file__).resolve().parent / "../env/.env").resolve()
load_dotenv(dotenv_path=dotenv_path)


API_KEY = os.getenv("API_KEY", "")
BASE_URL = os.getenv("BASE_URL", "")
CORE_LOC = os.getenv("CORE_LOC", "v1/cores")

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
  python ilab_api.py --outfile file_out.md
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
        CORE_ID = get_cores(BASE_URL, CORE_LOC, HEADERS, "id")
    # Building report by converting to md then to ppt or which ever format is required
    if args.outfile is None:
        outfile = "file_out"
    else:
        outfile = args.outfile
    # API filtering is limited
    # Function does addition filtering based on post request json
    service_requests = select_service_request(
        BASE_URL, CORE_LOC, HEADERS, CORE_ID, DATE_RANGE, filters=FILTER_CRITERIA
    )
    full = full_sr(service_requests, HEADERS)
    with open(f"{outfile}_full.json", "w") as f:
        json.dump(full,f)
        
    # Not ideal but for now I don't care to much about it
    if args.export_request:
        with open(f"{outfile}.json", "w") as f:
            json.dump(service_requests, f)
    else:
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
        