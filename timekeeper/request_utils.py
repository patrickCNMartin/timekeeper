import re
import requests
# -----------------------------------------------------------------------------#
# IMPORT GENERIC UTILS
# -----------------------------------------------------------------------------#
from timekeeper_utils import trim_response


# -----------------------------------------------------------------------------#
# DEF FUNCTIONS
# -----------------------------------------------------------------------------#
# This is only for API selection and filtering
# Very limited filtering logic
# Could be worth creating a local database that will be used
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
        'completed' : []}
    for sr in service_requests:
        if sr is is_draft(sr):
            sorted_requests['drafts'] = sorted_requests['drafts'].append(sr)
        elif sr is is_unassigned_meeting(sr):
            sorted_requests['startup_meeting_unassigned'] = sorted_requests['startup_meeting_unassigned'].append(sr)
        elif sr is is_assigned_meeting(sr):
            sorted_requests['startup_meeting_assigned'] = sorted_requests['startup_meeting_assigned'].append(sr)
        elif sr is is_unassigned_supplementary_samples(sr):
            sorted_requests['supplementary_sample_unassigned'] = sorted_requests['supplementary_sample_unassigned'].append(sr)
        elif sr is is_assigned_supplementary_samples(sr):
            sorted_requests['supplementary_sample_assigned'] = sorted_requests['supplementary_sample_assigned'].append(sr)
        else:
            #For now skip what is not listed 
            continue
    return sorted_requests

# Select only what is needed for the meetings
FIELDS = ['name','description','state','submitted_at','start_on','end_on','assigned_to','service_name','owner.name']


def get_base_fields(d: dict, fields: list[str] = FIELDS) -> dict:
    def get(v, keys):
        return v if not keys else get(v.get(keys[0]), keys[1:]) if isinstance(v, dict) else None
    return {f: get(d, f.split(".")) for f in fields}

def extract_forms(service_requests:dict, form: str)-> dict:
    form_info = {}
    startup_form_fields = [i for i in service_requests["forms"] if i["name"] == form]
    for i in startup_form_fields[0]:
        form_info[i["name"]] = i["value"]
    return form_info



def is_draft(service_request:dict)-> dict:
    if re.search('draft',service_request['state']):
        draft = get_base_fields(service_request)
        return draft
    else:
        return None

def is_unassigned_meeting(service_request:dict) -> dict:
    if service_request['service_name'] == "Start-up meeting" and service_request['assigned_to'] is None:
        unassigned_meeting = get_base_fields(service_request)
        unassigned_meeting = unassigned_meeting.update(extract_forms(service_request, "Start-up Meeting Request form"))
        return unassigned_meeting
    else:
        return None

def is_assigned_meeting(service_request:dict) -> dict:
    if service_request['service_name'] == "Start-up meeting" and service_request['assigned_to'] is not None:
        assigned_meeting = get_base_fields(service_request)
        assigned_meeting = assigned_meeting.update(extract_forms(service_request, "Start-up Meeting Request form"))
        return assigned_meeting
    else:
        return None

def is_unassigned_supplementary_samples(service_request:dict) -> dict:
    if service_request['service_name'] == "Supplementary sample submission" and service_request['assigned_to'] is None:
        unassigned_supplementary = get_base_fields(service_request)
        unassigned_supplementary = unassigned_supplementary.update(extract_forms(service_request, "Additional Sample Submission Form"))
        return unassigned_supplementary
    else:
        return None

def is_assigned_supplementary_samples(service_request:dict) -> dict:
    if service_request['service_name'] == "Supplementary sample submission" and service_request['assigned_to'] is not None:
        assigned_supplementary = get_base_fields(service_request)
        assigned_supplementary = assigned_supplementary.update(extract_forms(service_request, "Additional Sample Submission Form"))
        return assigned_supplementary
    else:
        return False




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


