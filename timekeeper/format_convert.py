# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import os

# -----------------------------------------------------------------------------#
# SET GLOBAL VARS
# NOTE: this will need to be changed to have more fexibility. I don't like this
# The probelem is that it assume that the list are in the same order with
# the same elements. Which might not always be the case.
# -----------------------------------------------------------------------------#
REQUEST_INFO = [
    "What_is_the_background_of_your_project_and_the_aim_with_the_analysis_",
    "What_type_of_samples_do_you_have__species__blood_or_tissue__pellet_or_gel__etc__",
    "how_many_samples_would_you_analyze_",
]
PROTOCOL_INFO = ["BACKGROUND_OF_PROJECT_", "TYPE_OF_SAMPLES", "Number_of_samples_"]

SHORTHAND_DESC = ["Background", "Type of sample", "Number of Samples"]

# -----------------------------------------------------------------------------#
# DEF FUNCTIONS
# -----------------------------------------------------------------------------#


def request_type_title(request_type):
    match request_type:
        case "new":
            return "# New Service Requests \n"
        case "assigned":
            return "# Assigned Requets \n"
        case _:
            raise ValueError("Unknown request type")
    return 0


def convert_to_md(sr: dict, sd: dict, request_type: str):
    # This is also stupid since we will add other types later
    title = request_type_title(request_type)
    subtitle = (
        "## " + " - ".join([f"**{key}**: {val}" for key, val in sr.items()]) + "\n"
    )
    # This happens if there is nothing in the description
    # I just add a simple "No Description" str
    if type(sd) is dict:
        body = "*" + "*".join(
            [f" **{k1}**: {v2} \n" for k1, v2 in zip(SHORTHAND_DESC, list(sd.values()))]
        )
    else:
        body = sd
    md_format = [title, subtitle, body]
    return md_format


def convert_sr_to_md(
    service_request: list,
    service_description: list,
    request_type: str,
    outfile: str = "file_out",
):
    mode = "a" if os.path.exists(f"{outfile}.md") else "w"
    print(f"{'Appending to' if mode == 'a' else 'Creating'} md: {outfile}.md")
    with open(f"{outfile}.md", mode) as f:
        for sr, sd in zip(service_request, service_description):
            md_local = convert_to_md(sr, sd, request_type)
            f.writelines(md_local)
    return 0
