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


def filter_by_submitted_date(service_requests: list, date_range: dict) -> list:
    """Keep the requests submitted within date_range.
    The API date search runs on a creation date it does not return, not on submitted_at"""
    from_date = datetime.fromisoformat(date_range["from_date"])
    to_date = datetime.fromisoformat(date_range["to_date"])
    return [
        sr for sr in service_requests
        if sr["submitted_at"] and from_date <= datetime.fromisoformat(sr["submitted_at"]) <= to_date
    ]


def add_forms(service_request:list, headers) -> list:
    counter = 1
    for sr in service_request:
        print(f"Processing service request: {counter}")
        sr['forms'] = get_custom_forms(sr,headers)
        sr['milestones'] = get_milestones(sr,headers)
        counter += 1
    return service_request


# Hardcoded fields for Proteomics core iLAB
STARTUP_MEETING = "Start-up meeting"
SUPPLEMENTARY_SAMPLE = "Supplementary sample submission"
# Supplementary form: the request it follows up on, and how many new samples
PREVIOUS_REQUEST_FIELD = (
    "You are attempting to submit new sample batches, similar to a previous request you've had with us."
    " Please give us the iLab request ID for your previous request:"
)
NEW_SAMPLES_FIELD = "Number of samples:"


def is_processing(service_request: dict) -> bool:
    return service_request['state'] == 'processing'

def is_completed(service_request: dict) -> bool:
    return service_request['state'] == 'completed'

def is_new_meeting(
    service_request: dict, 
    service_type: str = STARTUP_MEETING
) -> bool:
    return service_request['service_name'] == service_type and not service_request['assigned_to']

def is_assigned_meeting(
    service_request: dict,
    service_type: str = STARTUP_MEETING
) -> bool:
    return service_request['service_name'] == service_type and bool(service_request['assigned_to'])

def is_supplementary_samples(
    service_request: dict,
    service_type: str = SUPPLEMENTARY_SAMPLE
) -> bool:
    return service_request['service_name'] == service_type and not service_request['assigned_to']

def is_supplementary_samples_request(
    service_request: dict,
    service_type: str = SUPPLEMENTARY_SAMPLE
) -> bool:
    return service_request['service_name'] == service_type and bool(service_request['assigned_to'])



RULES = [
    ('processing', is_processing, None),
    ('completed', is_completed, None),
    ('startup_meeting_request', is_new_meeting, "Start-up Meeting Request form"),
    ('startup_meeting', is_assigned_meeting, "Start-up Meeting Request form"),
    ('supplementary_sample', is_supplementary_samples, "Additional Sample Submission Form"),
    ('supplementary_sample_request', is_supplementary_samples_request, "Additional Sample Submission Form"),
]

# Bins in output order (json, csv and slides)
BINS = [
    'startup_meeting_request',
    'startup_meeting',
    'supplementary_sample',
    'supplementary_sample_request',
    'processing',
    'completed'
]


def sort_service_requests(service_requests: list)->dict:
    sorted_requests = {name: [] for name in BINS}
    # Anything that matches no rule is skipped
    for sr in service_requests:
        for name, rule, form in RULES:
            if rule(sr):
                fields = get_base_fields(sr)
                if form:
                    fields |= extract_forms(sr, form)
                sorted_requests[name].append(fields)
                break
    return sorted_requests

# Select only what is needed for the meetings
FIELDS = ['name','assigned_to','state','submitted_at','service_name','owner.name']


def get_base_fields(d: dict, fields: list[str] = FIELDS) -> dict:
    def get(v, keys):
        return v if not keys else get(v.get(keys[0]), keys[1:]) if isinstance(v, dict) else None
    return {f: get(d, f.split(".")) for f in fields}

def extract_forms(service_requests:dict, form: str)-> dict:
    """Field name -> value for the named form; empty if the request has no such form"""
    output = {}
    for f in service_requests["forms"]:
        if f["name"] == form:
            for field in f["fields"]:
                if "value" in field:
                    output[field["name"]] = field["value"]
                # else:
                #     import pdb;pdb.set_trace()
    return output
    


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
    else:
        raise ValueError("Can only search from today")
    delta = relativedelta(**how_long)
    cut_off = today - delta
    # to_date is tomorrow so that today's requests are included
    tomorrow = today + relativedelta(days=1)
    tomorrow = tomorrow.isoformat(timespec="milliseconds")
    cut_off = cut_off.isoformat(timespec="milliseconds")
    return {"to_date": tomorrow, "from_date": cut_off}


def to_local_date(timestamp: str):
    """Day of an iLab timestamp in this machine's time zone (iLab sends them in UTC-4/-5)"""
    return datetime.fromisoformat(timestamp).astimezone().date()

# -----------------------------------------------------------------------------#
# FORMAT & OUTPUT UTILS
# -----------------------------------------------------------------------------#

# Columns that only exist in the summary table; they start empty
REPORT_METRICS = [
    'Number of Samples',
    "Quant",
    'Sample type',
    'Request Date',
    'Meeting Date',
    'Approved Quote Date',
    'Sample Location',
    'Sample in Freezer Date',
    'Processing',
    'MS Search',
    'Search Completed Date',
    'Completion Date',
]


def format_response(sorted_requests: dict, report_metrics: list[str] = REPORT_METRICS) -> pd.DataFrame:
    """sort_service_requests output as a DataFrame: base fields, 'submission_date'
    (local day of submitted_at), 'type' (the bucket), empty report_metrics"""
    rows = [
        {f: sr[f] for f in FIELDS} | {"type": bucket}
        for bucket, srs in sorted_requests.items() for sr in srs
    ]
    df = pd.DataFrame(rows, columns=[*FIELDS, "type", *report_metrics])
    df.insert(df.columns.get_loc("submitted_at") + 1, "submission_date", df["submitted_at"].map(to_local_date))
    return df


# Bins that only show these fields as bullets, in this order
BIN_BULLETS = dict.fromkeys(
    ('supplementary_sample_assigned', 'supplementary_sample_unassigned'),
    ("submitted_at", "service_name", NEW_SAMPLES_FIELD, PREVIOUS_REQUEST_FIELD),
)
# Shorter bullet labels for long form questions
BULLET_LABELS = {PREVIOUS_REQUEST_FIELD: "Previous request"}


def convert_sr_to_md(sorted_requests: dict, outfile: str = "file_out", bins: list[str] | None = None):
    """Write sort_service_requests output to md: one '#' slide per request.
    bins: which bins to write, in that order; all of them if None"""
    print(f"Converting Service Request to markdown")
    in_subtitle = ("name", "owner.name", "state", "assigned_to")
    # utf-8 explicitly: build_ppt reads it back as utf-8, and Windows defaults to cp1252
    with open(f"{outfile}.md", "w", encoding="utf-8") as f:
        for bucket in bins or sorted_requests:
            for sr in sorted_requests[bucket]:
                f.write(f"# {bucket.replace('_', ' ').capitalize()}\n")
                f.write(
                    f"## {sr['name']} - {sr['owner.name']}"
                    f" - {sr['state'].replace('_', ' ')}"
                    f" - {', '.join(sr['assigned_to']) or 'Unassigned'}\n"
                )
                # Show the local day of submission, not the raw iLab timestamp
                submitted = to_local_date(sr["submitted_at"])
                shown = sr | {"submitted_at": f"{submitted:%B} {submitted.day}, {submitted.year}"}
                # Every non-empty field is a bullet, unless the bin picks its own in BIN_BULLETS
                f.writelines(
                    f"* **{BULLET_LABELS.get(key, key)}** {' '.join(str(shown[key]).split())}\n"
                    for key in BIN_BULLETS.get(bucket, shown)
                    if shown.get(key) and key not in in_subtitle
                )


