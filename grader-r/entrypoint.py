#!/usr/bin/env python3

import base64
import json
import mimetypes
import pathlib
import subprocess
import sys
import urllib.parse


def encode_image(fp: pathlib.Path, label: str) -> None | dict[str, str]:
    """Encodes an image file to base64 and adds a label.

    Args:
        fp (pathlib.Path): The path to the image file.
        label (str): The label to give to the image.

    Returns:
        dict: A dictionary containing the label and the base64 encoded image.
        None: If the file does not exist, is not an image, or the MIME type could not be determined.
    """
    if not fp.exists():
        print(f"[entrypoint.py] Image '{fp}' does not exist. Skipping.")
        return None

    mime = mimetypes.guess_type(fp)[0]

    if mime is None:
        print(f"[entrypoint.py] Could not determine MIME type for '{fp}'. Skipping.")
        return None

    if not mime.startswith("image/"):
        print(f"[entrypoint.py] File '{fp}' is not an image. Skipping.")
        return None

    return {
        "label": label,
        "url": f"data:{mime};base64,{urllib.parse.quote(base64.b64encode(fp.read_bytes()))}"
    }

def main():

    JOB_DIR = pathlib.Path("/grade")

    print(f"[entrypoint.py] Treating '{JOB_DIR}' AS JOB_DIR")

    # Load data file

    _data_file = JOB_DIR / "data/data.json"

    DATA = json.loads(_data_file.read_bytes())

    if not isinstance(DATA, dict):
        print(f"[entrypoint.py] DATA (read from '{_data_file}') is not a dictionary. Aborting.")
        sys.exit(1)

    tests_list: list[dict] = DATA["submitted_answers"].pop("_extra_parts", [])

    _autograder_files = DATA.get("params", {}).get("_autograder_files", [])

    for file in _autograder_files:

        path = JOB_DIR / file["path"]

        path.write_text(base64.b64decode(file["contents"]).decode())

    subprocess.run("/r_autograder/run.sh", stdout=sys.stdout, stderr=sys.stderr, check=False)  # noqa: S603

    print("[entrypoint.py] Starting image addition to the results.")

    # Load results file

    _results_file = JOB_DIR / "results/results.json"

    RESULTS = json.loads(_results_file.read_bytes())

    if not isinstance(RESULTS, dict):
        print(f"[entrypoint.py] RESULTS (read from '{_results_file}') is not a dictionary. Aborting.")
        sys.exit(1)

    succeeded = RESULTS.get("succeeded", False)
    if not succeeded:  # If the tests did not succeed, we do not add images (this does not mean that a test wasn't passed, it means the grading job failed)
        print("[entrypoint.py] Job did not succeed. Not Adding Images.")
        sys.exit(0)

    # Get data on images to attach to the results

    images = DATA.get("params", {}).get("_images", None)

    if not isinstance(images, list):
        print("[entrypoint.py] key 'params._images' is missing or is not a list. Aborting.")
        sys.exit(1)

    ## Each Entry In _extra_parts MUST have the following keys:
    ## - name: The name of the part.
    ## - points: The points awarded for the part.
    ## - max_points: The maximum points for the part.
    ## Each Entry In _extra_parts MAY have the following keys:
    ## - description: A description of the part.
    ## - message: A message to display to the student.
    ## - output: The output of the part.
    ## These entries should be generated in server.py's parse() function, as element grading and internal [grade(data)]
    ## are not used when an external autograder is used currently.

    
    tests_list.extend(RESULTS.get("tests", []))

    RESULTS["tests"] = tests_list

    points = sum([test["points"] for test in RESULTS["tests"]])
    max_points = sum([test["max_points"] for test in RESULTS["tests"]])

    RESULTS["score"] = points / max_points

    tests: dict[str, int] = {test["name"]: i for i, test in enumerate(RESULTS["tests"])}

    for image in images:

        label = image.get("label", None)
        if label is None:
            print(f"[entrypoint.py] Image '{image}' does not have a label. Skipping.")
            continue

        filename = image.get("filename", None)
        if filename is None:
            print(f"[entrypoint.py] Image '{image}' does not have a path. Skipping.")
            continue

        img = encode_image(JOB_DIR.joinpath("images", filename), label)

        part = image.get("part", None)

        if part is None or part == "main":

            if "images" not in RESULTS:
                RESULTS["images"] = []

            RESULTS["images"].append(img)
            continue

        if part not in tests:
            print(f"[entrypoint.py] Part '{part}' not found in tests. Skipping.")
            continue

        i = tests[part]

        if "images" not in RESULTS["tests"][i]:
            RESULTS["tests"][i]["images"] = []

        RESULTS["tests"][i]["images"].append(img)

    _results_file.write_text(json.dumps(RESULTS))

    sys.exit(0)

if __name__ == "__main__":
    main()