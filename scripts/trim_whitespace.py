#!/usr/bin/env python3
import os
import subprocess
import argparse
import glob


def trim_image(image_path, output_dir="."):
    """
    Trims whitespace from a single image using ImageMagick's convert.

    Args:
        image_path (str): Path to the input image.
        output_dir (str): Directory to save the trimmed image.

    Returns:
        str: Path to the saved trimmed image.
    """
    try:
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}-trimmed{ext}"

        output_path = os.path.join(output_dir, output_filename)

        subprocess.run(
            ["convert", image_path, "-fuzz", "35%", "-trim", output_path], check=True
        )
        print(f"Trimmed image saved to: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        print(f"Error: ImageMagick command failed for '{image_path}': {e}")
    except FileNotFoundError:
        print(f"Error: ImageMagick 'convert' command not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def process_input(input_arg):
    """Processes either a glob pattern or a list of files."""

    if "*" in input_arg or "?" in input_arg or "[" in input_arg:
        # It's likely a glob pattern
        for input_file in glob.glob(input_arg):
            if os.path.isfile(input_file):
                trim_image(input_file)
            else:
                print(f"Warning: '{input_file}' is not a regular file, skipping.")
    else:
        # It's likely a single file or a list of files
        if os.path.isfile(input_arg):
            trim_image(input_arg)
        else:
            print(f"Warning: '{input_arg}' is not a regular file, skipping.")


def main():
    parser = argparse.ArgumentParser(
        description="Trim whitespace from images using ImageMagick."
    )
    parser.add_argument("input_arg", help="Glob pattern or file path(s).")
    parser.add_argument(
        "remaining",
        nargs=argparse.REMAINDER,
        help="Remaining files from shell glob expansion",
    )

    args = parser.parse_args()

    process_input(args.input_arg)
    if args.remaining:
        for file in args.remaining:
            process_input(file)

if __name__ == "__main__":
    main()
