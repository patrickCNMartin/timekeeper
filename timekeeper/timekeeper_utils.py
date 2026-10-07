# -----------------------------------------------------------------------------#
# IMPORTS
# -----------------------------------------------------------------------------#
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import pandas as pd
import re
import requests
# -----------------------------------------------------------------------------#
# REQUEST UTILS
# -----------------------------------------------------------------------------#

def trim_response(response: dict, id: str, metadata: bool = False):
    """Extract actual info from response Dict or return iLab meta data"""
    if metadata:
        return response["ilab_response"]["ilab_metadata"]
    else:
        return response["ilab_response"].get(id, {})

def get_service_requests(
    base_url,
    headers,
    core_id: int,
    date_range: None | dict = None,
    per_page=30,
    filters: dict = {},
) -> list:
    all_requests = []
    page = 1
    while True:
        print(f"Checking and Filtering page {page}")
        params = {"page": page, "per_page": per_page, **filters}
        if date_range is not None:
            params["to_date"] = date_range["to_date"]
            params["from_date"] = date_range["from_date"]
        filtered_response = requests.get(
            f"{base_url}/{core_id}/service_requests.json",
            headers=headers,
            params=params,
        )
        filtered_response.raise_for_status()
        local_requests = trim_response(filtered_response.json(), "service_requests")
        if not local_requests:
            break
        all_requests.extend(local_requests)
        page += 1
    return all_requests


def add_forms(service_request:list, headers) -> list:
    counter = 1
    for sr in service_request:
        print(f"Processing service request: {counter}")
        sr['forms'] = get_custom_forms(sr,headers)
        sr['milestones'] = get_milestones(sr,headers)
        counter += 1
    return service_request


def sort_service_requests(service_requests: list)->dict:
    # Hardcoded fields for Proteomics core iLAB
    sorted_requests = {
        'drafts' : [],
        'startup_meeting_unassigned': [],
        'startup_meeting_assigned': [],
        'supplementary_sample_assigned' : [],
        'supplementary_sample_unassigned' : [],
        'processing' : [],
        'completed' : [],
        'cancelled' : []}
    
    # service name -> (bucket prefix, form to pull)
    services = {
        "Start-up meeting": ("startup_meeting", "Start-up Meeting Request form"),
        "Supplementary sample submission": ("supplementary_sample", "Additional Sample Submission Form"),
    }
    # State decides first, then service type; anything not listed is skipped
    for sr in service_requests:
        fields = get_base_fields(sr)
        if 'draft' in sr['state']:
            sorted_requests['drafts'].append(fields)
        elif sr['state'] in ('processing', 'completed', 'cancelled'):
            sorted_requests[sr['state']].append(fields)
        elif sr['service_name'] in services:
            prefix, form = services[sr['service_name']]
            assigned = 'assigned' if sr['assigned_to'] else 'unassigned'
            sorted_requests[f'{prefix}_{assigned}'].append(fields | extract_forms(sr, form))
    return sorted_requests

# Select only what is needed for the meetings
FIELDS = ['name','description','state','submitted_at','start_on','end_on','assigned_to','service_name','owner.name']


def get_base_fields(d: dict, fields: list[str] = FIELDS) -> dict:
    def get(v, keys):
        return v if not keys else get(v.get(keys[0]), keys[1:]) if isinstance(v, dict) else None
    return {f: get(d, f.split(".")) for f in fields}

def extract_forms(service_requests:dict, form: str)-> dict:
    """Field name -> value for the named form; empty if the request has no such form"""
    return {
        field["name"]: field["value"]
        for f in service_requests["forms"] if f["name"] == form
        for field in f["fields"]
    }


def get_custom_forms(service_request, headers, form="all"):
    """Get custom form associated with a specific service ID"""
    custom_form_action = service_request["actions"]["list_custom_forms"]["url"]
    response = requests.get(custom_form_action, headers=headers)
    response.raise_for_status()
    forms = trim_response(response.json(), "custom_forms")
    
    if form == "all":
        return forms
    else:
        form_list = [f for f in forms if f["name"] in form]
        if len(form_list) == 1:
            return form_list[0]
        else:
            return form_list


def get_milestones(service_request, headers):
    """Get custom form associated with a specific service ID"""
    custom_milestone_action = service_request["actions"]["list_milestones"]["url"]
    response = requests.get(custom_milestone_action, headers=headers)
    response.raise_for_status()
    milestones = trim_response(response.json(), "object")
    return milestones
    

def get_request_info(
    service_request,
) -> str | list:
    state = service_request["state"].replace("_", " ")
    person = service_request["owner"]["name"]
    service_name = service_request["name"]
    assigned_to = service_request["assigned_to"]
    if assigned_to:
        assigned_to = assigned_to[0]
    else:
        assigned_to = "?"
    return {
        "State": state,
        "Person": person,
        "Service name": service_name,
        "Assigned to": assigned_to,
    }

# -----------------------------------------------------------------------------#
# DATE UTILS
# -----------------------------------------------------------------------------#

def convert_date(date: str):
    numeric_value = int(re.findall(r"\d+", date)[0])
    unit = re.findall(r"(?<=\d)[a-zA-Z]+", date)[0]
    unit = unit if unit.endswith("s") else unit + "s"
    return {unit: numeric_value}


def set_default_cutoff_dates(start_date: str, how_long: dict):
    if re.search(r"\btoday\b", start_date, re.IGNORECASE):
        today = datetime.now(timezone.utc)
        today = today + relativedelta(days=1)
    else:
        raise ValueError("Can only search from today")
    delta = relativedelta(**how_long)
    cut_off = today - delta
    today = today.isoformat(timespec="milliseconds")
    cut_off = cut_off.isoformat(timespec="milliseconds")
    return {"to_date": today, "from_date": cut_off}

# -----------------------------------------------------------------------------#
# FORMAT & OUTPUT UTILS
# -----------------------------------------------------------------------------#

# Columns that only exist in the summary table; they start empty
REPORT_METRICS = [
    'Name of responsible',
    'Project Name',
    'Nr of samples and quant (DIA, TMT, DDA)',
    'Sample type',
    'Request',
    'Meeting',
    'Approved/sent quote after meeting',
    'Samples position in the freezer (frezer name, shelf, rack, box, etc)',
    'Sample in Freezer',
    'Sample prep',
    'MS',
    'Search',
    'Data searched',
    'Data sent',
]


def format_response(sorted_requests: dict, report_metrics: list[str] = REPORT_METRICS) -> pd.DataFrame:
    """sort_service_requests output as a DataFrame: base fields, 'type' (the bucket), empty report_metrics"""
    rows = [
        {f: sr[f] for f in FIELDS} | {"type": bucket}
        for bucket, srs in sorted_requests.items() for sr in srs
    ]
    return pd.DataFrame(rows, columns=[*FIELDS, "type", *report_metrics])


def convert_sr_to_md(sorted_requests: dict, outfile: str = "file_out"):
    """Write sort_service_requests output to md: one '#' slide per request"""
    in_subtitle = ("name", "owner.name", "state", "assigned_to")
    with open(f"{outfile}.md", "w") as f:
        for bucket, bucket_requests in sorted_requests.items():
            for sr in bucket_requests:
                f.write(f"# {bucket.replace('_', ' ').capitalize()}\n")
                f.write(
                    f"## {sr['name']} - {sr['owner.name']}"
                    f" - {sr['state'].replace('_', ' ')}"
                    f" - {', '.join(sr['assigned_to']) or '?'}\n"
                )
                # ponytail: every non-empty field is a bullet, long forms overflow
                # a slide; pick fields per bucket when that matters
                f.writelines(
                    f"* **{key}** {' '.join(str(value).split())}\n"
                    for key, value in sr.items()
                    if value and key not in in_subtitle
                )


