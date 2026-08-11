from pathlib import Path
import re

# Where to create the folders
OUTPUT_DIR = Path(".")

addresses = [
    "3 Cutler St",
    "3 Dorset St",
    "4 Pacific St",
    "5 Mohawk St",
    "6 Pacific St",
    "12 Mohawk St",
    "14-16 Jenkins St",
    "49 Rogers St",
    "58 Rogers St",
    "83 Old Harbor St",
    "116 Marine Rd",
    "133 E 5th St",
    "158 K St",
    "160 K St",
    "160 O St",
    "181 H St",
    "275 Old Colony Ave",
    "447 W 4th St",
    "474 E 4th St",
    "480 E 4th St",
    "482 E 4th St",
    "533 E 5th St",
    "550 E 8th St",
    "551 E 7th St",
    "594 E 6th St",
    "609 E 5th St",
    "621 E 2nd St",
    "679 E 7th St",
    "681 E 5th St",
    "804 E 7th St",
    "1824 Columbia Rd",
]

def slugify(address):
    # Lowercase
    slug = address.lower()

    # Remove apostrophes if any
    slug = slug.replace("'", "")

    # Replace spaces with hyphens
    slug = re.sub(r"\s+", "-", slug)

    # Remove anything that's not a-z, 0-9, or hyphen
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)

    return slug.strip("-")

OUTPUT_DIR.mkdir(exist_ok=True)

for address in addresses:
    folder = OUTPUT_DIR / slugify(address)
    folder.mkdir(exist_ok=True)
    print(f"✓ Created: {folder.name}")

print(f"\nDone! Created {len(addresses)} folders.")