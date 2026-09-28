# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import argparse
import json
import os
import re
from difflib import get_close_matches
from pathlib import Path

from dotenv import load_dotenv


from request_utils import (
    get_cores,
    select_service_request,
    full_sr,
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
# DEFINE SEARCH
# -----------------------------------------------------------------------------#
def to_text(value) -> str:
    """Normalise a key/value to lower-case text (None -> "", int -> str)"""
    if value is None:
        return ""
    return str(value).lower()


def scalar_values(value) -> list:
    """Scalars to match on: the value itself, or the scalar items of a list"""
    if isinstance(value, dict):
        return []
    if isinstance(value, list):
        return [i for i in value if not isinstance(i, (dict, list))]
    return [value]


def term_in_text(term: str, text: str, fuzzy: bool = False, cutoff: float = 0.6) -> bool:
    """True if term is in text, or (fuzzy) close to a run of words in text

    e.g. 'bacon' or 'bacn' both hit 'there is bacon in my pasta'
    """
    term = term.lower()
    if term in text:
        return True
    if not fuzzy or not text:
        return False
    # compare against runs of words the same length as the term
    words = re.findall(r"[^\W_]+", text)
    n = len(term.split()) or 1
    candidates = [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]
    candidates.append(text)
    return bool(get_close_matches(term, candidates, n=1, cutoff=cutoff))


def find_matches(obj, search_terms: list, fuzzy: bool = False, cutoff: float = 0.6) -> list:
    """Recursively return {key: value} for every key or value matching search_terms"""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            texts = [to_text(k)] + [to_text(i) for i in scalar_values(v)]
            if any(
                term_in_text(term, text, fuzzy, cutoff)
                for term in search_terms
                for text in texts
            ):
                found.append({k: v})
            found.extend(find_matches(v, search_terms, fuzzy, cutoff))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_matches(item, search_terms, fuzzy, cutoff))
    return found


def search_service(
    service_request: list | dict,
    search_terms: list,
    return_element: bool = False,
    fuzzy: bool = False,
    cutoff: float = 0.6,
) -> list:
    """Recursively search service requests for keys or values matching search_terms

    return_element=True returns the top-level elements (dicts) containing a match,
    otherwise returns a list of {key: value} for every match.
    fuzzy=True also accepts near misses against the words in keys/values (0 < cutoff <= 1).
    """
    if isinstance(service_request, dict):
        service_request = [service_request]
    search_element = []
    for sr in service_request:
        found = find_matches(sr, search_terms, fuzzy, cutoff)
        if not found:
            continue
        if return_element:
            search_element.append(sr)
        else:
            search_element.extend(found)
    return search_element


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
        "--search_terms",
        required=True,
        nargs='+',
        help=(
            "Search terms to find on the service request list"
            "Use fuzzy search"
        ),
    )
    parser.add_argument(
            "--return_element",
            action='store_true',
            help=(
                "Return Service request of just field"
            ),
        )
    parser.add_argument(
        "--fuzzy_factor",
        required=False,
        nargs='?',
        type=float,
        const=0.6,
        help=(
            "Find near miss terms - because I know you can't spell Patrick"
        ),
    )
    
    return parser.parse_args()


# -----------------------------------------------------------------------------#
# ENTRY
# -----------------------------------------------------------------------------#
if __name__ == "__main__":
    args = parse_args()
    outfile = args.outfile
    search_terms = args.search_terms
    return_element = args.return_element
    fuzzy_factor = args.fuzzy_factor
    if fuzzy_factor:
        fuzzy = True
    else:
        fuzzy = False
    # need to update this function
    if CORE_ID is None or CORE_ID == "":
        CORE_ID = get_cores(BASE_URL, CORE_LOC, HEADERS, "id")

    if os.path.isfile(f"{outfile}.json"):
        with open(f"{outfile}.json",'r') as f:
            service_requests = json.load(f)
    else:
        service_requests = select_service_request(
            BASE_URL, CORE_LOC, HEADERS, CORE_ID, DATE_RANGE, filters=FILTER_CRITERIA
        )
        service_requests = full_sr(service_requests, HEADERS)
        with open(f"{outfile}.json", 'w') as f:
            json.dump(service_requests,f)

    searched_elements = search_service(
        service_request = service_requests,
        search_terms=search_terms,
        return_element=return_element,
        fuzzy=fuzzy,
        cutoff=fuzzy_factor)

    with open(f"{outfile}_searched.json", 'w') as f:
        json.dump(searched_elements,f)
    print(searched_elements)
    
    
        
    