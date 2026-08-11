from pathlib import Path
import json
import re

# Put this script in the same folder as:
#
#   projects.json
#   map.json
#
# It creates:
#
#   master_projects.json


BASE = Path(__file__).resolve().parent

PROJECTS_FILE = BASE / "projects.json"
MAP_FILE = BASE / "map.json"
OUTPUT_FILE = BASE / "master_projects.json"


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path.name}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_status(value):
    if value is None:
        return None

    status = str(value).strip().lower()

    status_map = {
        "completed": "completed",
        "complete": "completed",
        "finished": "completed",

        "in progress": "in-progress",
        "in-progress": "in-progress",
        "ongoing": "in-progress",
        "under construction": "in-progress",

        "upcoming": "upcoming",
        "planned": "upcoming",
    }

    return status_map.get(status, status)


def normalize_number(value):
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        return value

    try:
        number = float(str(value).replace(",", "").strip())

        if number.is_integer():
            return int(number)

        return number

    except ValueError:
        return value


def normalize_living_area(value):
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        return int(value) if float(value).is_integer() else value

    text = str(value).lower().strip()

    # Remove things like "sqft", "sq ft", "sq. ft."
    text = re.sub(r"\s*(sq\.?\s*ft\.?|sqft)\s*$", "", text)

    text = text.replace(",", "").strip()

    try:
        number = float(text)

        if number.is_integer():
            return int(number)

        return number

    except ValueError:
        return value


def clean_photos(value):
    """
    Keep the existing photo order.

    IMPORTANT:
    photos[0] is the featured/thumbnail image.

    There is intentionally NO separate thumbnail field.
    """

    if not isinstance(value, list):
        return []

    return [
        str(photo)
        for photo in value
        if photo is not None and str(photo).strip()
    ]


# ---------------------------------------------------------
# LOAD EXISTING DATA
# ---------------------------------------------------------

projects = load_json(PROJECTS_FILE)
map_data = load_json(MAP_FILE)


if not isinstance(projects, list):
    raise ValueError("projects.json must contain a JSON array.")

if not isinstance(map_data, list):
    raise ValueError("map.json must contain a JSON array.")


# ---------------------------------------------------------
# INDEX MAP DATA BY PROJECT ID
# ---------------------------------------------------------

map_by_id = {
    item["id"]: item
    for item in map_data
    if isinstance(item, dict) and "id" in item
}


# ---------------------------------------------------------
# CREATE MASTER PROJECTS
# ---------------------------------------------------------

master = []

for project in projects:

    if not isinstance(project, dict):
        continue

    project_id = project.get("id")

    if not project_id:
        print("Warning: skipping project without an ID.")
        continue

    address = project.get("address") or {}
    specs = project.get("specs") or {}

    item = {
        "id": project_id,

        "title": project.get("title", ""),

        "status": normalize_status(
            project.get("status")
        ),

        "address": {
            "street": address.get("street", ""),
            "city": address.get("city", ""),
            "state": address.get("state", ""),
            "zip": address.get("zip", "")
        },

        "overview": project.get("overview", ""),

        "specs": {
            "type": specs.get("type"),

            # Rename completedYear → year
            "year": specs.get(
                "year",
                specs.get("completedYear")
            ),

            "residences": normalize_number(
                specs.get("residences")
            ),

            "bedrooms": normalize_number(
                specs.get("bedrooms")
            ),

            "bathrooms": normalize_number(
                specs.get("bathrooms")
            ),

            "livingArea": normalize_living_area(
                specs.get("livingArea")
            )
        },

        # No thumbnail field.
        # The first photo is the featured image.
        "photos": clean_photos(
            project.get("photos")
        )
    }


    # -----------------------------------------------------
    # ADD LOCATION
    # -----------------------------------------------------

    map_item = map_by_id.get(project_id)

    if map_item:
        lat = map_item.get("lat")
        lng = map_item.get("lng")

        if lat is not None and lng is not None:
            item["location"] = {
                "lat": normalize_number(lat),
                "lng": normalize_number(lng)
            }


    master.append(item)


# ---------------------------------------------------------
# WRITE MASTER JSON
# ---------------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        master,
        f,
        indent=2,
        ensure_ascii=False
    )

    f.write("\n")


# ---------------------------------------------------------
# REPORT
# ---------------------------------------------------------

project_ids = {
    project.get("id")
    for project in projects
    if isinstance(project, dict) and project.get("id")
}


map_ids = {
    item.get("id")
    for item in map_data
    if isinstance(item, dict) and item.get("id")
}


unmatched_map = sorted(map_ids - project_ids)


projects_without_location = [
    project["id"]
    for project in master
    if "location" not in project
]


projects_without_photos = [
    project["id"]
    for project in master
    if not project.get("photos")
]


print()
print("========================================")
print(" MASTER JSON CREATED")
print("========================================")
print(f"File:     {OUTPUT_FILE.name}")
print(f"Projects: {len(master)}")
print()
print("Structure:")
print("  ✓ One object per development")
print("  ✓ Address inside each project")
print("  ✓ Location inside each project")
print("  ✓ Specs inside each project")
print("  ✓ No thumbnail field")
print("  ✓ photos[0] = featured image")
print("  ✓ developments.json is NOT used")
print("  ✓ completedYear → year")
print("  ✓ livingArea converted to a number")
print("  ✓ Numeric fields normalized")
print("  ✓ Status values normalized")
print()


if unmatched_map:
    print("MAP ENTRIES WITHOUT MATCHING PROJECT:")
    for project_id in unmatched_map:
        print(f"  - {project_id}")
    print()


if projects_without_location:
    print("PROJECTS WITHOUT LOCATION:")
    for project_id in projects_without_location:
        print(f"  - {project_id}")
    print()


if projects_without_photos:
    print("PROJECTS WITHOUT PHOTOS:")
    for project_id in projects_without_photos:
        print(f"  - {project_id}")
    print()


print("Done.")