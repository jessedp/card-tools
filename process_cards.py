#!/usr/bin/env python3
import os
import datetime
import argparse
import glob
import subprocess

import cv2
import numpy as np


def create_output_directory():
    """Creates and returns a timestamped output directory with a trimmed subdirectory."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join("processed", timestamp)
    trimmed_dir = os.path.join(output_dir, "trimmed")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(trimmed_dir, exist_ok=True)
    return output_dir


def crop_and_rotate_rectangles(
    image_path, output_dir, max_rectangles=5, min_area=500000, draw_contours=False
):
    """
    Finds, crops, and rotates the largest rectangles in an image, ensuring the rectangle is correctly oriented.
    Returns a list of paths to the cropped images.

    Args:
        image_path (str): Path to the input image.
        output_dir (str): Directory to save cropped rectangles.
        max_rectangles (int, optional): Maximum number of rectangles to process. Defaults to 5.
        min_area (int, optional): Minimum area for a rectangle to be considered. Defaults to 1000.
        draw_contours (bool, optional): Whether to save an image showing the detected contours. Defaults to False.

    Returns:
        list: Paths to the saved cropped images.
    """
    cropped_image_paths = []
    original_filename = os.path.basename(image_path)
    name, ext = os.path.splitext(original_filename)

    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image from {image_path}")
        return cropped_image_paths

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
    dilated_edges = cv2.dilate(edges, None, iterations=8)

    # cv2.RETR_TREE
    # cv2.RETR_EXTERNAL
    contours, _ = cv2.findContours(
        dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )

    # Save contours visualization if requested
    if draw_contours:
        # Create a copy of the original image to draw on
        contour_image = image.copy()

        # Draw all contours in red
        cv2.drawContours(contour_image, contours, -1, (0, 0, 255), 2)

        # Draw detected rectangles in green
        for contour in contours:

            if cv2.contourArea(contour) >= min_area:
                rect = cv2.minAreaRect(contour)
                width, height = rect[1]
                aspect_ratio = (
                    min(width, height) / max(width, height)
                    if min(width, height) > 0
                    else 0
                )

                if 0.71 <= aspect_ratio <= 0.72:
                    box = cv2.boxPoints(rect)
                    box = np.int32(box)
                    cv2.drawContours(contour_image, [box], 0, (0, 255, 0), 3)

        # Save the contour visualization
        contours_filename = f"{name}-contours{ext}"
        contours_path = os.path.join(output_dir, contours_filename)
        cv2.imwrite(contours_path, contour_image)
        print(f"Saved contours visualization to: {contours_path}")

    rectangles = []
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        rect = cv2.minAreaRect(contour)

        # Calculate aspect ratio (make sure to handle division by zero)
        width, height = rect[1]
        aspect_ratio = (
            min(width, height) / max(width, height) if min(width, height) > 0 else 0
        )
        if aspect_ratio < 0.71 or aspect_ratio > 0.72:
            continue

        box = cv2.boxPoints(rect)
        box = np.int32(box)

        if len(box) == 4:
            area = cv2.contourArea(box)
            rectangles.append((area, box))

    rectangles.sort(key=lambda x: x[0], reverse=True)

    for i, (_, box) in enumerate(rectangles[:max_rectangles]):
        rect = box.astype(np.float32)

        # Get the rectangle center, width, height, and angle
        (x, y), (w, h), angle = cv2.minAreaRect(rect)
        center = (int(x), int(y))

        # Adjust angle for correct orientation
        if w < h:
            angle += 90

        # Create rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Rotate the full image
        rotated_image = cv2.warpAffine(
            image, rotation_matrix, (image.shape[1], image.shape[0])
        )

        # Crop the rotated image to the rectangle's bounding box
        box_int = np.int32(
            cv2.transform(np.array([rect]), rotation_matrix)[0]
        )  # Rotate the box points
        x_min, y_min = np.min(box_int, axis=0)
        x_max, y_max = np.max(box_int, axis=0)

        # Add checks to prevent out-of-bounds indices
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(rotated_image.shape[1], x_max)
        y_max = min(rotated_image.shape[0], y_max)

        # Check if the crop region is valid
        if x_min >= x_max or y_min >= y_max:
            print(f"Warning: Invalid crop region for rectangle {i+1}, skipping.")
            continue

        cropped_rotated_image = rotated_image[y_min:y_max, x_min:x_max]

        # Check if the cropped image is valid
        if cropped_rotated_image.size == 0:
            print(f"Warning: Empty cropped image for rectangle {i+1}, skipping.")
            continue

        rotate_cropped_rotated_image = cv2.rotate(
            cropped_rotated_image, cv2.ROTATE_90_CLOCKWISE
        )

        output_filename = f"{name}-cropped-{i+1}{ext}"
        output_path = os.path.join(output_dir, output_filename)

        # Verify the image is valid before writing
        if rotate_cropped_rotated_image.size > 0:
            cv2.imwrite(output_path, rotate_cropped_rotated_image)
            cropped_image_paths.append(output_path)
            print(f"Saved cropped and rotated rectangle {i+1} to {output_path}")
        else:
            print(f"Warning: Invalid rotated image for rectangle {i+1}, skipping.")

    return cropped_image_paths


def trim_image(image_path, output_dir):
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

        # Format should be ORIGINAL_FILE-cropped-X-trimmed.originalformat
        if "-cropped-" in name:
            output_filename = f"{name}-trimmed{ext}"
        else:
            output_filename = f"{name}-trimmed{ext}"

        # Save to the trimmed subdirectory
        trimmed_dir = os.path.join(output_dir, "trimmed")
        output_path = os.path.join(trimmed_dir, output_filename)

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

    return None


def process_image(
    image_path, output_dir, max_rectangles=5, min_area=500000, draw_contours=False
):
    """
    Process a single image: crop rectangles and trim whitespace.

    Args:
        image_path (str): Path to the input image.
        output_dir (str): Directory to save processed images.
        max_rectangles (int, optional): Maximum number of rectangles to process. Defaults to 5.
        min_area (int, optional): Minimum area for a rectangle to be considered. Defaults to 1000.
        draw_contours (bool, optional): Whether to save an image showing the detected contours. Defaults to False.
    """
    if not os.path.isfile(image_path):
        print(f"Warning: '{image_path}' is not a regular file, skipping.")
        return

    # Step 1: Crop and rotate rectangles
    cropped_paths = crop_and_rotate_rectangles(
        image_path, output_dir, max_rectangles, min_area, draw_contours
    )

    # Step 2: Trim whitespace from all cropped images
    for cropped_path in cropped_paths:
        trim_image(cropped_path, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Process images: find rectangles, crop, rotate, and trim whitespace."
    )
    parser.add_argument("input_files", nargs="+", help="One or more input image files.")
    parser.add_argument(
        "-n",
        "--max_rectangles",
        type=int,
        default=20,
        help="Maximum number of rectangles to crop per image.",
    )
    parser.add_argument(
        "-a",
        "--min_area",
        type=int,
        default=500000,
        help="Minimum area of rectangles to consider.",
    )
    parser.add_argument(
        "-c",
        "--contours",
        action="store_true",
        help="Save visualization of detected contours.",
    )
    args = parser.parse_args()

    # Create timestamped output directory
    output_dir = create_output_directory()
    print(f"Processing images, saving results to: {output_dir}")

    # Process each input file
    for input_pattern in args.input_files:
        # Handle glob patterns
        if "*" in input_pattern or "?" in input_pattern or "[" in input_pattern:
            for input_file in glob.glob(input_pattern):
                process_image(
                    input_file,
                    output_dir,
                    args.max_rectangles,
                    args.min_area,
                    args.contours,
                )
        else:
            # Handle regular files
            process_image(
                input_pattern,
                output_dir,
                args.max_rectangles,
                args.min_area,
                args.contours,
            )


if __name__ == "__main__":
    main()
