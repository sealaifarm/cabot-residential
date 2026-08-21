import os
from PIL import Image

# Main folder
BASE_FOLDER = "projects"

# Supported image extensions
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp"
}


def get_creation_time(path):
    """
    Get the file creation time.
    On macOS, st_birthtime is used when available.
    Otherwise, st_ctime is used.
    """
    stat = os.stat(path)

    if hasattr(stat, "st_birthtime"):
        return stat.st_birthtime

    return stat.st_ctime


def process_folder(folder_path):
    files = os.listdir(folder_path)

    # If the folder already has properly numbered WebP files,
    # leave the folder completely untouched.
    numbered_webp = [
        file for file in files
        if file.lower().endswith(".webp")
        and os.path.splitext(file)[0].isdigit()
    ]

    if numbered_webp:
        print(f"SKIP: {folder_path}")
        return

    # Find all image files
    image_files = []

    for file in files:
        full_path = os.path.join(folder_path, file)

        if not os.path.isfile(full_path):
            continue

        extension = os.path.splitext(file)[1].lower()

        if extension in IMAGE_EXTENSIONS:
            image_files.append(full_path)

    if not image_files:
        print(f"EMPTY: {folder_path}")
        return

    # Sort by creation/date-added time
    image_files.sort(key=get_creation_time)

    print(f"\nPROCESSING: {folder_path}")

    # ---------------------------------------------------------
    # IMPORTANT:
    # Rename existing source files temporarily first.
    #
    # This prevents problems like:
    # image.webp -> 01.webp
    # while 01.webp already exists.
    # ---------------------------------------------------------

    temp_files = []

    for index, image_path in enumerate(image_files, start=1):

        extension = os.path.splitext(image_path)[1].lower()

        temp_name = f"__temp_{index:04d}{extension}"
        temp_path = os.path.join(folder_path, temp_name)

        os.rename(image_path, temp_path)

        temp_files.append(temp_path)

    # ---------------------------------------------------------
    # Convert / rename everything to 01.webp, 02.webp, etc.
    # ---------------------------------------------------------

    for index, temp_path in enumerate(temp_files, start=1):

        output_name = f"{index:02d}.webp"
        output_path = os.path.join(folder_path, output_name)

        try:
            with Image.open(temp_path) as image:

                # Preserve transparency when possible
                if image.mode in ("RGBA", "LA", "P"):
                    image = image.convert("RGBA")
                else:
                    image = image.convert("RGB")

                image.save(
                    output_path,
                    "WEBP",
                    quality=90,
                    method=6
                )

            print(
                f"  {os.path.basename(temp_path)} -> {output_name}"
            )

            # Remove temporary source file
            os.remove(temp_path)

        except Exception as e:
            print(f"  ERROR: {temp_path}")
            print(f"  {e}")


def main():

    if not os.path.exists(BASE_FOLDER):
        print(f"ERROR: Folder '{BASE_FOLDER}' does not exist.")
        return

    # Only process direct subfolders inside projects/
    for folder_name in sorted(os.listdir(BASE_FOLDER)):

        folder_path = os.path.join(BASE_FOLDER, folder_name)

        if os.path.isdir(folder_path):
            process_folder(folder_path)

    print("\nDone!")


if __name__ == "__main__":
    main()