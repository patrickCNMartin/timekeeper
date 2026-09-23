# Utility functions
import re
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta


def trim_response(response: dict, id: str, metadata: bool = False):
    """Extract actual info from response Dict or return iLab meta data"""
    if metadata:
        return response["ilab_response"]["ilab_metadata"]
    else:
        return response["ilab_response"].get(id, {})


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
