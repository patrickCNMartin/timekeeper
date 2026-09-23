import re

import requests

# -----------------------------------------------------------------------------#
# IMPORT GENERIC UTILS
# -----------------------------------------------------------------------------#
from utils.utils import trim_response


# -----------------------------------------------------------------------------#
# DEF FUNCTIONS
# -----------------------------------------------------------------------------#
def get_cores(base_url, core_loc, headers, return_info: str = "all"):
    response = requests.get(f"{base_url}/{core_loc}.json", headers=headers)
    response.raise_for_status()
    cores = trim_response(response.json(), "cores")
    match return_info:
        case "all":
            return cores
        # Potentially use a filter dict instead
        # Tha assumption is you don't know what the core info is
        case "id":
            return [i["id"] for i in cores]
        case "name":
            return [n["name"] for n in cores]
        case _:
            raise ValueError("Unknown information to return")


# This is only for API selection and filtering
# Very limited filtering logic
# Could be worth creating a local database that will be used
def select_service_request(
    base_url,
    core_loc,
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
            f"{base_url}/{core_loc}/{core_id}/service_requests.json",
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


# simple quick function
# will probably use a data base to run more complex commands
# Allow AND OR stuff and potentially easier to push towards kantele later
def filter_service_requests(service_requests: list, request_type: str = "new") -> list:
    match request_type:
        case "new":
            service_requests = is_assgined(service_requests, assigned=False)
        case "assigned":
            service_requests = is_assgined(service_requests, assigned=True)
        case "all":
            service_requests = service_requests
        case _:
            raise ValueError("Unknow request type")
    service_requests = is_unlinked(service_requests)
    service_requests = is_active(service_requests)
    return service_requests


def is_unlinked(service_request):
    service_request = [sr for sr in service_request if not re.search("CID", sr["name"])]
    return service_request


def is_active(service_request):
    service_request = [
        sr
        for sr in service_request
        if sr["state"] not in ["cancelled", "research_draft"]
    ]
    return service_request


def is_assgined(service_request, assigned: bool = False) -> list:
    if assigned:
        status = [sr for sr in service_request if sr["assigned_to"]]
    else:
        status = [sr for sr in service_request if not sr["assigned_to"]]
    return status


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


def get_form_request(form_name: str = "Start-up Meeting Request form"):
    match form_name:
        case "new":
            return "Start-up Meeting Request form"
        case "assigned":
            return "Meeting protocol"
        case "all":
            return "all"
        case _:
            raise ValueError("Unknown form request")
    return 0


def get_field_labels(form_name: str = "new"):
    match form_name:
        case "new":
            return [
                "What_is_the_background_of_your_project_and_the_aim_with_the_analysis_",
                "What_type_of_samples_do_you_have__species__blood_or_tissue__pellet_or_gel__etc__",
                "how_many_samples_would_you_analyze_",
            ]
        case "assigned":
            return ["BACKGROUND_OF_PROJECT_", "TYPE_OF_SAMPLES", "Number_of_samples_"]
        case _:
            raise ValueError("Unknown form request")
    return 0


def get_request_description(
    service_request,
    headers,
    request_type: str = "new",
):
    form_name = get_form_request(request_type)
    field_labels = get_field_labels(request_type)
    form = get_custom_forms(service_request, headers, form_name)

    if len(form) == 0:
        return "No Description \n"

    fields = form["fields"]
    # there is a cleaner way of doing this - but it will do for now.
    field_info = {
        fi["label"]: fi["value"] for fi in fields if fi["identifier"] in field_labels
    }

    return field_info
