import json
import requests
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = "projects.json"
OUTPUT_FILE = "projects_sorted.json"

IMAGES_ROOT = Path("images/projects")

GOOGLE_MAPS_API_KEY = "AIzaSyDY4l90Bq5eb1RgZCVoEA0JXURKvcYwZuU"

MAX_IMAGES = 999


# ============================================================
# FLATTEN PROJECT LIST
# ============================================================

def flatten_projects(data):
    """
    Recursively flatten nested lists.

    This allows projects.json to contain:

    [
        {...},
        [{...}, {...}],
        {...}
    ]

    and turns it into:

    [
        {...},
        {...},
        {...}
    ]
    """

    projects = []

    if isinstance(data, list):

        for item in data:
            projects.extend(flatten_projects(item))

    elif isinstance(data, dict):

        projects.append(data)

    return projects


# ============================================================
# GOOGLE MAPS GEOCODING
# ============================================================

def geocode_address(project):

    address = project.get("address", {})

    street = address.get("street", "")
    city = address.get("city", "")
    state = address.get("state", "")
    zip_code = address.get("zip", "")

    full_address = f"{street}, {city}, {state} {zip_code}, USA"

    print(f"  Geocoding: {full_address}")

    url = "https://maps.googleapis.com/maps/api/geocode/json"

    params = {
        "address": full_address,
        "key": GOOGLE_MAPS_API_KEY
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as e:

        print(f"  ERROR: Google Maps request failed: {e}")

        return None, None

    status = data.get("status")

    if status != "OK":

        print(f"  ERROR: Google Maps status: {status}")

        if data.get("error_message"):
            print(f"  {data['error_message']}")

        return None, None

    results = data.get("results", [])

    if not results:

        print("  ERROR: No location found.")

        return None, None

    location = results[0]["geometry"]["location"]

    return (
        location["lat"],
        location["lng"]
    )


# ============================================================
# FIND PHOTOS
# ============================================================

def get_photos(project_id):

    folder = IMAGES_ROOT / project_id

    if not folder.exists():

        print(f"  WARNING: Folder does not exist: {folder}")

        return []

    photos = []

    for number in range(1, MAX_IMAGES + 1):

        filename = f"{number:02d}.webp"

        file_path = folder / filename

        if not file_path.exists():

            break

        photos.append(
            f"images/projects/{project_id}/{filename}"
        )

    return photos


# ============================================================
# UPDATE PHOTOS
# ============================================================

def update_photos(project):

    project_id = project.get("id")

    if not project_id:

        print("  WARNING: Project has no ID.")

        project["photos"] = []

        return

    photos = get_photos(project_id)

    project["photos"] = photos

    print(f"  Photos: {len(photos)}")


# ============================================================
# UPDATE LOCATION
# ============================================================

def update_location(project):

    if "location" not in project:

        project["location"] = {
            "lat": None,
            "lng": None
        }

    location = project["location"]

    if not isinstance(location, dict):

        location = {
            "lat": None,
            "lng": None
        }

        project["location"] = location

    lat = location.get("lat")
    lng = location.get("lng")

    # Both coordinates already exist
    if lat is not None and lng is not None:

        print(
            f"  Location already exists: "
            f"{lat}, {lng}"
        )

        return

    # Need to geocode
    new_lat, new_lng = geocode_address(project)

    if new_lat is not None and new_lng is not None:

        location["lat"] = new_lat
        location["lng"] = new_lng

        print(
            f"  Location: "
            f"{new_lat}, {new_lng}"
        )

    else:

        print(
            "  WARNING: "
            "Could not find location."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("==============================================")
    print("        PROJECT JSON ORGANIZER")
    print("==============================================")
    print()

    # --------------------------------------------------------
    # CHECK INPUT FILE
    # --------------------------------------------------------

    if not Path(INPUT_FILE).exists():

        print(
            f"ERROR: {INPUT_FILE} "
            "was not found."
        )

        return

    # --------------------------------------------------------
    # LOAD JSON
    # --------------------------------------------------------

    try:

        with open(
            INPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            raw_data = json.load(f)

    except json.JSONDecodeError as e:

        print(
            "ERROR: projects.json "
            "contains invalid JSON."
        )

        print(e)

        return

    # --------------------------------------------------------
    # FLATTEN NESTED LISTS
    # --------------------------------------------------------

    projects = flatten_projects(raw_data)

    print(
        f"Projects found after flattening: "
        f"{len(projects)}"
    )

    # --------------------------------------------------------
    # REMOVE ITEMS WITHOUT IDs
    # --------------------------------------------------------

    valid_projects = []

    skipped = 0

    for project in projects:

        if not isinstance(project, dict):

            skipped += 1

            continue

        if not project.get("id"):

            print(
                "WARNING: Found project "
                "without an ID. Skipping."
            )

            skipped += 1

            continue

        valid_projects.append(project)

    projects = valid_projects

    if skipped:

        print(
            f"Skipped {skipped} invalid items."
        )

    print(
        f"Valid projects: "
        f"{len(projects)}"
    )

    print()

    # --------------------------------------------------------
    # SORT ALPHABETICALLY
    # --------------------------------------------------------

    projects.sort(
        key=lambda project:
            str(project.get("id", "")).lower()
    )

    print("Projects sorted alphabetically.")
    print()

    # --------------------------------------------------------
    # PROCESS PROJECTS
    # --------------------------------------------------------

    for index, project in enumerate(
        projects,
        start=1
    ):

        project_id = project.get(
            "id",
            "UNKNOWN"
        )

        print("----------------------------------------------")

        print(
            f"{index}/{len(projects)}: "
            f"{project_id}"
        )

        print("----------------------------------------------")

        # Photos
        update_photos(project)

        # Location
        update_location(project)

        print()

    # --------------------------------------------------------
    # SAVE OUTPUT
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            projects,
            f,
            indent=2,
            ensure_ascii=False
        )

        f.write("\n")

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print("==============================================")
    print("DONE")
    print("==============================================")

    print()

    print(
        f"Created: {OUTPUT_FILE}"
    )

    print(
        f"Projects written: "
        f"{len(projects)}"
    )

    print()

    print(
        "Projects sorted alphabetically."
    )

    print(
        "Photos updated from images/projects/<id>/."
    )

    print(
        "Missing coordinates filled using Google Maps."
    )


if __name__ == "__main__":
    main()