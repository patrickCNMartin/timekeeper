# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import argparse
import json
import os
import requests

from datetime import datetime, timedelta, timezone
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
# Read-only: everything below is a GET
SR_URL = f"{BASE_URL}/{CORE_ID}/service_requests"
MAX_PAGES = 50
DAYS = 14


def fetch(label: str, **params) -> list | None:
    """Every page of service requests for these query params; None if the API refuses them"""
    all_requests, seen, page = [], set(), 1
    print(f"\n[{label}] params={params}")
    while page <= MAX_PAGES:
        response = requests.get(f"{SR_URL}.json", headers=HEADERS, params={"page": page, **params})
        if not response.ok:
            print(f"    HTTP {response.status_code}: {response.text[:200]}")
            return None
        body = response.json()
        batch = trim_response(body, "service_requests")
        if page == 1:
            print(f"    metadata: {body['ilab_response'].get('ilab_metadata')}")
        ids = {sr["id"] for sr in batch}
        # Stop on an empty page, or if the API starts repeating itself
        if not batch or ids <= seen:
            break
        print(f"    page {page}: {len(batch)} requests")
        seen |= ids
        all_requests.extend(batch)
        page += 1
    print(f"    total: {len(all_requests)}")
    return all_requests


def submitted(service_request: dict) -> datetime | None:
    value = service_request.get("submitted_at")
    return datetime.fromisoformat(value).astimezone(timezone.utc) if value else None


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

    now = datetime.now(timezone.utc)
    cut = now - timedelta(days=DAYS)
    tomorrow = now + timedelta(days=1)
    doc_format = "%Y-%m-%dT%H:%MZ"  # as in the API doc example
    print(f"now (UTC) = {now:%Y-%m-%d %H:%M}   {DAYS} days ago = {cut:%Y-%m-%d %H:%M}")

    # Same question (last 14 days) asked in different ways; ALL is the ground truth
    experiments = {
        "ALL": {},
        "ALL+pp": {"per_page": 30},
        "TK": {"per_page": 30, **DATE_RANGE},  # exactly what timekeeper.py sends
        "TK14": {"from_date": cut.isoformat(timespec="milliseconds"),
                 "to_date": tomorrow.isoformat(timespec="milliseconds")},
        "DOC": {"from_date": cut.strftime(doc_format), "to_date": tomorrow.strftime(doc_format)},
        "DOCfrom": {"from_date": cut.strftime(doc_format)},
        "DAY": {"from_date": cut.strftime("%Y-%m-%d")},
    }
    results = {label: fetch(label, **params) for label, params in experiments.items()}

    everything = results["ALL"] or []
    by_id = {sr["id"]: sr for sr in everything}
    expected = {i for i, sr in by_id.items() if submitted(sr) and submitted(sr) >= cut}
    print(f"\n=== requests with submitted_at in the last {DAYS} days (from ALL): {len(expected)} ===")
    print(f"    requests in ALL without submitted_at: {sum(1 for sr in everything if not submitted(sr))}")

    labels = [label for label in experiments if label not in ("ALL", "ALL+pp")]
    got = {label: {sr["id"] for sr in results[label]} if results[label] is not None else None for label in labels}
    for label in labels:
        if got[label] is None:
            print(f"  {label:8s} refused by the API")
            continue
        print(f"  {label:8s} returned {len(got[label]):3d} | missing {sorted(expected - got[label])}"
              f" | unexpected {sorted(got[label] - expected)}")

    # Everything from the last 30 days, newest first, with who returned it
    print(f"\n{'id':>8} {'submitted_at (UTC)':19} {'days':>5}  " + " ".join(f"{label:7s}" for label in labels) + " state / service")
    recent = [sr for sr in everything if submitted(sr) and submitted(sr) >= now - timedelta(days=30)]
    for sr in sorted(recent, key=submitted, reverse=True):
        age = (now - submitted(sr)).total_seconds() / 86400
        marks = " ".join(f"{'-' if got[label] is None else 'x' if sr['id'] in got[label] else '.':7s}" for label in labels)
        print(f"{sr['id']:>8} {submitted(sr):%Y-%m-%d %H:%M}    {age:5.1f}  {marks} {sr['state']} / {sr['service_name']}")

    # Which date is the window keyed on? Some requests carry a submitted_at that
    # does not match when they were created (their id sits among later requests)
    probes = {
        "around submitted_at of 858962": {"from_date": "2021-05-01T00:00Z", "to_date": "2021-07-01T00:00Z"},
        "around id-neighbours of 858962": {"from_date": "2025-04-15T00:00Z", "to_date": "2025-06-01T00:00Z"},
        "around submitted_at of 918187": {"from_date": "2026-01-25T00:00Z", "to_date": "2026-02-05T00:00Z"},
        "around id-neighbours of 918187": {"from_date": "2026-02-19T00:00Z", "to_date": "2026-03-05T00:00Z"},
    }
    for label, params in probes.items():
        found = fetch(label, **params) or []
        for sr in found:
            print(f"    -> {sr['id']} submitted_at={submitted(sr):%Y-%m-%d %H:%M} {sr['state']}")
    print("\nALL, ids in the order returned:", [sr["id"] for sr in everything])

    # Does a single request expose more dates (created_at, updated_at) than the list does?
    if everything:
        newest = max((sr for sr in everything if submitted(sr)), key=submitted)
        response = requests.get(f"{SR_URL}/{newest['id']}.json", headers=HEADERS)
        print(f"\nsingle request {newest['id']}: HTTP {response.status_code}")
        if response.ok:
            inner = response.json()["ilab_response"]
            for key, value in inner.items():
                if isinstance(value, dict):
                    print(f"  '{key}' keys: {sorted(value)}")
                    print("  date-like:", {k: v for k, v in value.items() if k.endswith(("_at", "_on"))})

    if outfile:
        with open(outfile, 'w') as f:
            json.dump(results, f)
