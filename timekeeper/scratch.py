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
from timekeeper_utils import convert_date, set_default_cutoff_dates, format_response,trim_response


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
    all_cores_url = f"{BASE_URL}"
    ac = requests.get(
            url = all_cores_url,
            headers=HEADERS,
        )
    ac.raise_for_status()
    ac_resp = ac.json()
    with open("data/core_test.json", 'w') as f:
        json.dump(ac_resp,f)

    # Get single core
    s_cores_url = f"{BASE_URL}/{CORE_ID}"
    sc = requests.get(
            url = s_cores_url,
            headers=HEADERS,
        )
    sc.raise_for_status()
    sc_resp = sc.json()
    with open("data/single_cores_test.json", 'w') as s:
        json.dump(sc_resp,s)

    # # Get services
    sr_cores_url = f"{BASE_URL}/{CORE_ID}/services.json"
    sr = requests.get(
            url = sr_cores_url,
            headers=HEADERS,
        )
    sr.raise_for_status()
    sr_resp = sr.json()
    with open("data/service_list.json", 'w') as r:
        json.dump(sr_resp,r)

    # # Get equipment
    eq_cores_url = f"{BASE_URL}/{CORE_ID}/equipment.json"
    eq = requests.get(
            url = eq_cores_url,
            headers=HEADERS,
        )
    eq.raise_for_status()
    eq_resp = eq.json()
    with open("data/equipment_list.json", 'w') as e:
        json.dump(eq_resp,e)

    # # Get service requests
    srl_cores_url = f"{BASE_URL}/{CORE_ID}/service_requests.json"
    srl = requests.get(
            url = srl_cores_url,
            headers=HEADERS,
        )
    srl.raise_for_status()
    srl_resp = srl.json()
    with open("data/service_request_list_postsub.json", 'w') as sr:
        json.dump(srl_resp,sr)

    # # testing updates to request
    # # hard coded for now 
    # put_url = "https://api-eu.ilabsolutions.com/v1/cores/3655/service_requests/959258.json"
    # put = requests.put(
    #     url = put_url,
    #     headers=HEADERS,
    #     json={"service_request": {"state": "completed"}})
    # print("Status Code:", put.status_code)

    # print("Response Body:", put.content.decode())
    
    # testing reformat for table insertion
    FIELDS = ['name','id','state','submitted_at','start_on','end_on','assigned_to','service_name','owner.name']
    serv = trim_response(srl_resp, 'service_requests')
    df = format_response(serv,fields=FIELDS)
    import pdb; pdb.set_trace()
    
    
    
        
    