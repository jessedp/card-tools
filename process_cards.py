#!/usr/bin/env python3
import os
import datetime
import argparse
import glob
import subprocess
import math
import json
import re
import hashlib

import cv2
import numpy as np

from analyze_card import analyze_trading_card
from scripts.trim_whitespace import trim_image


def find_rectangles_with_morphology(
    gray_image,
    min_area,
    existing_rectangles,
    draw_debug=False,
    debug_dir=None,
    image_name=None,
):
    """
    Fast method to find cards with broken edges using stronger morphological operations.

    Args:
        gray_image: Grayscale image
        min_area: Minimum area to consider a valid rectangle
        existing_rectangles: List of already detected rectangles to avoid duplicates
        draw_debug: Whether to save debug images
        debug_dir: Directory to save debug images if draw_debug is True
        image_name: Base name for debug images

    Returns:
        List of (area, box) tuples for additional rectangles found
    """
    # Create a stronger dilated image specifically for broken edges
    # Threshold to get a binary image
    _, binary = cv2.threshold(
        gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    # Create a larger kernel for morphological operations to bridge larger gaps
    kernel = np.ones((9, 9), np.uint8)

    # Apply closing operation to connect broken edges (much faster than the previous approach)
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    if draw_debug and debug_dir is not None and image_name is not None:
        cv2.imwrite(os.path.join(debug_dir, f"{image_name}-strong-closed.png"), closed)

    # Find contours on the strongly processed image
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter for rectangles with the same criteria as the main function
    rectangles_found = []
    existing_boxes = [box for _, box in existing_rectangles]

    for contour in contours:
        # Skip small contours
        if cv2.contourArea(contour) < min_area * 0.8:  # Allow slightly smaller areas
            continue

        # Get minimum area rectangle
        rect = cv2.minAreaRect(contour)

        # Check aspect ratio
        width, height = rect[1]
        aspect_ratio = (
            min(width, height) / max(width, height) if max(width, height) > 0 else 0
        )

        # Card aspect ratio check - same as main detection but slightly more relaxed
        if not (0.63 <= aspect_ratio <= 0.77):
            continue

        box = cv2.boxPoints(rect)
        box = np.int32(box)

        # Check if this is a duplicate of an existing rectangle
        is_duplicate = False
        for existing_box in existing_boxes:
            if boxes_overlap(box, existing_box):
                is_duplicate = True
                break

        if not is_duplicate:
            area = cv2.contourArea(box)
            rectangles_found.append((area, box))

    return rectangles_found


def find_rectangles_with_contour_merging(
    gray_image,
    edges,
    min_area,
    existing_rectangles,
    draw_debug=False,
    debug_dir=None,
    image_name=None,
):
    """
    Find rectangles by detecting potential rectangle fragments and intelligently merging them.
    Particularly good for cards with white edges where the middle section is completely missing.

    Args:
        gray_image: Grayscale image
        edges: Canny edges from the main algorithm
        min_area: Minimum area to consider
        existing_rectangles: List of already detected rectangles
        draw_debug: Whether to save debug images
        debug_dir: Directory to save debug images
        image_name: Base name for debug images

    Returns:
        List of additional rectangles found
    """
    # Use adaptive thresholding to better segment text from background
    adaptive_thresh = cv2.adaptiveThreshold(
        gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5
    )

    # Dilate to connect close components
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(adaptive_thresh, kernel, iterations=1)

    if draw_debug and debug_dir is not None and image_name is not None:
        cv2.imwrite(
            os.path.join(debug_dir, f"{image_name}-adaptive.png"), adaptive_thresh
        )
        cv2.imwrite(
            os.path.join(debug_dir, f"{image_name}-adaptive-dilated.png"), dilated
        )

    # Find all contours - even small ones - using LIST to catch nested contours
    contours, hierarchy = cv2.findContours(
        dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )

    # Start contour merging process
    # First, identify all potential rectangle parts (line segments, corners, etc.)
    potential_parts = []

    for contour in contours:
        area = cv2.contourArea(contour)

        # Skip too small contours
        if area < 100:  # Very small threshold to capture edges and text
            continue

        # Simplify the contour to find potential straight segments
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Get bounding box for later grouping
        x, y, w, h = cv2.boundingRect(contour)

        # Keep track of the approximated contour and its bounding box
        potential_parts.append((approx, (x, y, w, h), area))

    # If debug mode, draw all potential parts
    if draw_debug and debug_dir is not None and image_name is not None:
        parts_image = np.zeros(
            (gray_image.shape[0], gray_image.shape[1], 3), dtype=np.uint8
        )
        for part, _, _ in potential_parts:
            color = (0, 0, 255)  # Blue
            cv2.drawContours(parts_image, [part], 0, color, 2)
        cv2.imwrite(
            os.path.join(debug_dir, f"{image_name}-potential-parts.png"), parts_image
        )

    # Group contours that might belong to the same card
    # We'll use a grid-based approach to find contours that align in card-like patterns
    height, width = gray_image.shape

    # Create grid cells (divide image into a grid)
    grid_size = 50  # Size of each grid cell
    rows = height // grid_size + 1
    cols = width // grid_size + 1
    grid = [[[] for _ in range(cols)] for _ in range(rows)]

    # Assign contours to grid cells they overlap with
    for part_idx, (part, (x, y, w, h), _) in enumerate(potential_parts):
        # Calculate grid cells this contour overlaps with
        start_row = max(0, y // grid_size)
        end_row = min(rows - 1, (y + h) // grid_size)
        start_col = max(0, x // grid_size)
        end_col = min(cols - 1, (x + w) // grid_size)

        # Add this contour to all overlapping cells
        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                grid[r][c].append(part_idx)

    # Find dense regions of contours that might form cards
    card_regions = []
    processed_cells = set()

    for r in range(rows):
        for c in range(cols):
            if (r, c) in processed_cells or len(grid[r][c]) < 3:
                continue

            # Start a new region
            region = set(grid[r][c])
            region_cells = {(r, c)}

            # Expand region to neighboring cells with contours
            frontier = [(r, c)]
            while frontier:
                curr_r, curr_c = frontier.pop(0)

                # Check all 8 neighboring cells
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = curr_r + dr, curr_c + dc

                        if (
                            0 <= nr < rows
                            and 0 <= nc < cols
                            and (nr, nc) not in region_cells
                            and len(grid[nr][nc]) > 0
                        ):

                            region.update(grid[nr][nc])
                            region_cells.add((nr, nc))
                            frontier.append((nr, nc))

            # Mark all cells in this region as processed
            processed_cells.update(region_cells)

            # Only keep regions with enough contours to potentially form a card
            if len(region) >= 5:
                card_regions.append(region)

    # For each region, create a combined contour and check if it forms a valid card
    rectangles_found = []
    existing_boxes = [box for _, box in existing_rectangles]

    for region_idx, region in enumerate(card_regions):
        # Create a mask for all contours in this region
        mask = np.zeros_like(gray_image, dtype=np.uint8)

        for part_idx in region:
            contour = potential_parts[part_idx][0]
            cv2.drawContours(mask, [contour], 0, 255, -1)

        # Dilate to connect nearby components
        region_mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)

        if draw_debug and debug_dir is not None and image_name is not None:
            cv2.imwrite(
                os.path.join(debug_dir, f"{image_name}-region-{region_idx}.png"),
                region_mask,
            )

        # Find contours in the combined mask
        region_contours, _ = cv2.findContours(
            region_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Check each contour to see if it forms a valid card
        for contour in region_contours:
            area = cv2.contourArea(contour)

            # Skip small contours
            if area < min_area * 0.7:
                continue

            # Get minimum area rectangle
            rect = cv2.minAreaRect(contour)

            # Check aspect ratio
            width, height = rect[1]
            aspect_ratio = (
                min(width, height) / max(width, height) if max(width, height) > 0 else 0
            )

            # Use a more relaxed aspect ratio constraint
            if not (0.60 <= aspect_ratio <= 0.80):
                continue

            box = cv2.boxPoints(rect)
            box = np.int32(box)

            # Check if this is a duplicate of an existing rectangle
            is_duplicate = False
            for existing_box in existing_boxes:
                if boxes_overlap(box, existing_box):
                    is_duplicate = True
                    break

            if not is_duplicate:
                rect_area = cv2.contourArea(box)
                rectangles_found.append((rect_area, box))

    return rectangles_found


def boxes_overlap(box1, box2):
    """
    Simple and fast method to check if two boxes overlap significantly.

    Args:
        box1, box2: Boxes as numpy arrays of 4 points each

    Returns:
        True if boxes overlap significantly, False otherwise
    """
    # Convert boxes to cv2 rotated rectangles
    rect1 = cv2.minAreaRect(box1)
    rect2 = cv2.minAreaRect(box2)

    # Get the rectangles as ((center_x, center_y), (width, height), angle)
    center1, size1, _ = rect1
    center2, size2, _ = rect2

    # Calculate the distance between centers
    dx = abs(center1[0] - center2[0])
    dy = abs(center1[1] - center2[1])

    # Calculate half dimensions
    width1, height1 = size1[0] / 2, size1[1] / 2
    width2, height2 = size2[0] / 2, size2[1] / 2

    # If centers are close relative to dimensions, they likely overlap
    return dx < (width1 + width2) * 0.7 and dy < (height1 + height2) * 0.7


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
        min_area (int, optional): Minimum area for a rectangle to be considered. Defaults to 500000 for large cards.
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

    # More balanced preprocessing for better large rectangle detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Moderate blurring - enough to reduce noise but not lose important details
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Use original edge detection approach that worked better
    edges = cv2.Canny(blurred, 50, 150)
    dilated_edges = cv2.dilate(edges, None, iterations=7)  # Keep strong dilation

    # Find contours with this approach
    contours, _ = cv2.findContours(
        dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # Save intermediate processing images for debugging if requested
    if draw_contours:
        debug_dir = os.path.join(output_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)

        cv2.imwrite(os.path.join(debug_dir, f"{name}-gray.png"), gray)
        cv2.imwrite(os.path.join(debug_dir, f"{name}-blurred.png"), blurred)
        cv2.imwrite(os.path.join(debug_dir, f"{name}-edges.png"), edges)
        cv2.imwrite(os.path.join(debug_dir, f"{name}-dilated_edges.png"), dilated_edges)

    # Save raw contours visualization if requested
    if draw_contours:
        # Create a copy of the original image to draw on
        all_contours_image = image.copy()

        # Draw all contours in red
        cv2.drawContours(all_contours_image, contours, -1, (0, 0, 255), 2)

        # Save the all contours visualization
        all_contours_filename = f"{name}-contours-raw{ext}"
        all_contours_path = os.path.join(output_dir, all_contours_filename)
        cv2.imwrite(all_contours_path, all_contours_image)
        print(f"Saved raw contours visualization to: {all_contours_path}")

    # Filter contours and find rectangular shapes
    rectangles = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        # Get the minimum area rectangle for this contour
        rect = cv2.minAreaRect(contour)

        # Calculate aspect ratio (make sure to handle division by zero)
        width, height = rect[1]
        aspect_ratio = (
            min(width, height) / max(width, height) if min(width, height) > 0 else 0
        )

        # Use a more relaxed aspect ratio constraint (0.65-0.75) for large rectangles
        # Standard playing cards have an aspect ratio around 0.7 (2.5" x 3.5")
        if 0.65 <= aspect_ratio <= 0.75:
            box = cv2.boxPoints(rect)
            box = np.int32(box)

            if len(box) == 4:
                area = cv2.contourArea(box)
                rectangles.append((area, box))

    # Sort rectangles by area (largest first)
    rectangles.sort(key=lambda x: x[0], reverse=True)

    # Try to find additional rectangles with different methods if we found fewer than expected
    if len(rectangles) < max_rectangles:
        # First try with stronger morphological operations
        extra_rectangles = find_rectangles_with_morphology(
            gray,
            min_area,
            rectangles,
            draw_contours,
            debug_dir if draw_contours else None,
            name,
        )
        if extra_rectangles:
            rectangles.extend(extra_rectangles)
            # Re-sort after adding new rectangles
            rectangles.sort(key=lambda x: x[0], reverse=True)

        # If still missing rectangles, try with contour approximation and merging
        if len(rectangles) < max_rectangles:
            # Get raw contours without much filtering
            merged_rectangles = find_rectangles_with_contour_merging(
                gray,
                edges,
                min_area,
                rectangles,
                draw_contours,
                debug_dir if draw_contours else None,
                name,
            )
            if merged_rectangles:
                rectangles.extend(merged_rectangles)
                # Re-sort after adding new rectangles
                rectangles.sort(key=lambda x: x[0], reverse=True)

    # Report how many rectangles we found
    print(f"Found {len(rectangles)} rectangular contours with min_area {min_area}")

    # Save visualization of filtered contours
    if draw_contours:
        # Create a copy of the original image
        filtered_contours_image = image.copy()

        # Draw the filtered rectangles in green
        for _, box in rectangles:
            cv2.drawContours(filtered_contours_image, [box], 0, (0, 255, 0), 3)

        # Save the filtered contours visualization
        filtered_contours_filename = f"{name}-contours-filtered{ext}"
        filtered_contours_path = os.path.join(output_dir, filtered_contours_filename)
        cv2.imwrite(filtered_contours_path, filtered_contours_image)
        print(f"Saved filtered contours visualization to: {filtered_contours_path}")

    # Process each rectangle up to the maximum number
    for i, (_, box) in enumerate(rectangles[:max_rectangles]):
        rect = np.float32(box)  # Use the box as the rectangle

        # Get the minimum area rectangle that fits the points
        min_rect = cv2.minAreaRect(rect)
        (center_x, center_y), (width, height), angle = min_rect
        center = (int(center_x), int(center_y))

        # Determine if we need to adjust the angle for proper orientation
        if width < height:
            angle += 90

        # Create a larger image with padding to ensure no part is lost after rotation
        # Calculate the diagonal of the rectangle as the minimum padding needed
        diagonal = int(math.sqrt(width**2 + height**2)) + 20  # Add some extra padding

        # Create a padded version of the original image
        h, w = image.shape[:2]
        padded_image = cv2.copyMakeBorder(
            image,
            diagonal,
            diagonal,
            diagonal,
            diagonal,
            cv2.BORDER_CONSTANT,
            value=[0, 0, 0],
        )

        # Adjust the center point for the padded image
        padded_center = (center[0] + diagonal, center[1] + diagonal)

        # Create rotation matrix for the padded image
        rotation_matrix = cv2.getRotationMatrix2D(padded_center, angle, 1.0)

        # Rotate the padded image
        padded_width, padded_height = padded_image.shape[1], padded_image.shape[0]
        rotated_padded_image = cv2.warpAffine(
            padded_image, rotation_matrix, (padded_width, padded_height)
        )

        # Save the rotated padded image for debugging
        if draw_contours:
            debug_rotated_filename = f"{name}-rotated-{i+1}{ext}"
            debug_rotated_path = os.path.join(debug_dir, debug_rotated_filename)
            cv2.imwrite(debug_rotated_path, rotated_padded_image)

        # Adjust the box points for the padded image
        padded_box = rect.copy()
        padded_box[:, 0] += diagonal  # Adjust x coordinates
        padded_box[:, 1] += diagonal  # Adjust y coordinates

        # Apply the rotation to the padded box points
        rotated_box = cv2.transform(np.array([padded_box]), rotation_matrix)[0]

        # Get the bounding rectangle of the rotated box
        x_min, y_min = np.min(rotated_box, axis=0).astype(int)
        x_max, y_max = np.max(rotated_box, axis=0).astype(int)

        # Ensure the bounds are within the image
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(padded_width, x_max)
        y_max = min(padded_height, y_max)

        # Check if the crop region is valid
        if x_min >= x_max or y_min >= y_max:
            print(f"Warning: Invalid crop region for rectangle {i+1}, skipping.")
            continue

        # Crop the rotated rectangle
        cropped_image = rotated_padded_image[y_min:y_max, x_min:x_max]

        # Save the initial cropped image for debugging
        if draw_contours:
            debug_cropped_filename = f"{name}-cropped-debug-{i+1}{ext}"
            debug_cropped_path = os.path.join(debug_dir, debug_cropped_filename)
            cv2.imwrite(debug_cropped_path, cropped_image)

        # Rotate the final image to have the card in portrait orientation
        final_image = cv2.rotate(cropped_image, cv2.ROTATE_90_CLOCKWISE)

        # Save the final cropped and rotated image
        output_filename = f"{name}-cropped-{i+1}{ext}"
        output_path = os.path.join(output_dir, output_filename)

        # Verify the image is valid before writing
        if final_image.size > 0:
            cv2.imwrite(output_path, final_image)
            cropped_image_paths.append(output_path)
            print(f"Saved cropped and rotated rectangle {i+1} to {output_path}")
        else:
            print(f"Warning: Invalid rotated image for rectangle {i+1}, skipping.")

    return cropped_image_paths


def process_image(
    image_path, output_dir, max_rectangles=5, min_area=500000, draw_contours=False
):
    """
    Process a single image: crop rectangles and trim whitespace.

    Args:
        image_path (str): Path to the input image.
        output_dir (str): Directory to save processed images.
        max_rectangles (int, optional): Maximum number of rectangles to process. Defaults to 5.
        min_area (int, optional): Minimum area for a rectangle to be considered. Defaults to 500000 for large cards.
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
    trimmed_paths = []
    for cropped_path in cropped_paths:
        trimmed_dir = os.path.join(output_dir, "trimmed")
        trimmed_path = trim_image(cropped_path, trimmed_dir)
        if trimmed_path:
            trimmed_paths.append(trimmed_path)

    # Step 3: OCR card
    for trimmed_path in trimmed_paths:
        try:
            # Analyze the card using OCR
            ocr_result = analyze_trading_card(trimmed_path)

            # Parse the JSON response
            ocr_data = json.loads(ocr_result)

            # Check if player_name exists and rename file if so
            final_image_path = trimmed_path
            if ocr_data.get("player_name"):
                # Make player name file system safe - replace spaces with underscores and remove invalid chars
                safe_player_name = re.sub(r'[<>:"/\\|?*]', '_', ocr_data["player_name"])
                safe_player_name = safe_player_name.replace(' ', '_').strip()

                # Create new filename with player name
                dir_name = os.path.dirname(trimmed_path)
                original_filename = os.path.basename(trimmed_path)
                name, ext = os.path.splitext(original_filename)
                new_filename = f"{safe_player_name}-{original_filename}"
                final_image_path = os.path.join(dir_name, new_filename)

                # Rename the file
                os.rename(trimmed_path, final_image_path)
                print(f"Renamed {trimmed_path} to {final_image_path}")

            # Calculate MD5 hash of the final image file
            with open(final_image_path, 'rb') as img_file:
                img_hash = hashlib.md5(img_file.read()).hexdigest()

            # Save JSON data using MD5 hash as filename
            json_filename = os.path.join(os.path.dirname(final_image_path), f"{img_hash}.json")
            with open(json_filename, 'w') as json_file:
                json.dump(ocr_data, json_file, indent=2)
            print(f"Saved OCR data to {json_filename}")

        except Exception as e:
            print(f"Error during OCR analysis of {trimmed_path}: {e}")


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
        help="Minimum area of rectangles to consider (default: 500000 for large cards).",
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
    trimmed_dir = os.path.join(output_dir, "trimmed")
    subprocess.run(["/usr/bin/xdg-open", trimmed_dir], check=True)


if __name__ == "__main__":
    try:
        main()
        exit(0)
    except KeyboardInterrupt:
        print("...cancelling")
        exit(0)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
