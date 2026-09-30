# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import argparse
import json
import os
import requests

from pathlib import Path

from dotenv import load_dotenv
# -----------------------------------------------------------------------------#
# IMPORT GENERIC UTILS
# -----------------------------------------------------------------------------#
from utils import convert_date, set_default_cutoff_dates
from request_utils import select_service_request

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
# DEFINE SEARCH
# -----------------------------------------------------------------------------#


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
        required=False,
        type=str,
        help=(
            "Output file location "
            "if none provide default names will be used in current directory."
        ),
    )
    return parser.parse_args()


# -----------------------------------------------------------------------------#
# ENTRY
# -----------------------------------------------------------------------------#
if __name__ == "__main__":
    args = parse_args()
    outfile = args.outfile

    # Get all cores
    all_cores_url = f"{BASE_URL}/v1/cores"
    ac = requests.get(
            url = all_cores_url,
            headers=HEADERS,
        )
    ac.raise_for_status()
    ac_resp = ac.json()
    with open("data/cores.json", 'w') as f:
        json.dump(ac_resp,f)

    # Get single core
    s_cores_url = f"{BASE_URL}/v1/cores/{CORE_ID}"
    sc = requests.get(
            url = s_cores_url,
            headers=HEADERS,
        )
    sc.raise_for_status()
    sc_resp = sc.json()
    with open("data/single_cores.json", 'w') as s:
        json.dump(sc_resp,s)

    # Get services
    sr_cores_url = f"{BASE_URL}/v1/cores/{CORE_ID}/services.json"
    sr = requests.get(
            url = sr_cores_url,
            headers=HEADERS,
        )
    sr.raise_for_status()
    sr_resp = sr.json()
    with open("data/service_list.json", 'w') as r:
        json.dump(sr_resp,r)

    # Get equipment
    eq_cores_url = f"{BASE_URL}/v1/cores/{CORE_ID}/equipment.json"
    eq = requests.get(
            url = eq_cores_url,
            headers=HEADERS,
        )
    eq.raise_for_status()
    eq_resp = eq.json()
    with open("data/equipment_list.json", 'w') as e:
        json.dump(eq_resp,e)

    # Get service requests
    srl_cores_url = f"{BASE_URL}/v1/cores/{CORE_ID}/service_requests.json"
    srl = requests.get(
            url = srl_cores_url,
            headers=HEADERS,
        )
    srl.raise_for_status()
    srl_resp = srl.json()
    with open("data/service_request_list.json", 'w') as sr:
        json.dump(srl_resp,sr)

    # Get milestone
    test_request = 955420
    srow_cores_url = f"{BASE_URL}/v1/cores/{CORE_ID}/service_requests/{test_request}/milestones.json"
    srow = requests.get(
            url = srow_cores_url,
            headers=HEADERS,
        )
    srow.raise_for_status()
    srow_resp = srow.json()
    with open("data/service_row.json", 'w') as sro:
        json.dump(srow_resp,sro)  

    
    
        
    