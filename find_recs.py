#!/usr/bin/env python3
import os
import datetime
import argparse

import cv2
import numpy as np


def crop_and_rotate_rectangles(
    image_path, output_dir="processed", max_rectangles=5, min_area=1000
):
    """
    Finds, crops, and rotates the largest rectangles in an image, ensuring the rectangle is correctly oriented.

    Args:
        image_path (str): Path to the input image.
        output_dir (str, optional): Directory to save cropped rectangles. Defaults to "processed".
        max_rectangles (int, optional): Maximum number of rectangles to process. Defaults to 5.
        min_area (int, optional): Minimum area for a rectangle to be considered. Defaults to 1000.
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image from {image_path}")
        return

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    dilated_edges = cv2.dilate(edges, None, iterations=2)

    contours, _ = cv2.findContours(
        dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

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

        # print(f"Aspect ratio: {aspect_ratio}")

        box = cv2.boxPoints(rect)
        box = np.int32(box)
        # print(f"Box: {box}")

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
        cropped_rotated_image = rotated_image[y_min:y_max, x_min:x_max]

        rotate_cropped_rotated_image = cv2.rotate(
            cropped_rotated_image, cv2.ROTATE_90_CLOCKWISE
        )
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = f"cropped-{i + 1}-{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        # cv2.imwrite(output_path, cropped_rotated_image)
        cv2.imwrite(output_path, rotate_cropped_rotated_image)
        print(f"Saved cropped and rotated rectangle {i + 1} to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Find, crop, and rotate the largest rectangles in an image."
    )
    parser.add_argument("image_path", help="Path to the input image.")
    parser.add_argument(
        "-o", "--output_dir", default="processed", help="Output directory."
    )
    parser.add_argument(
        "-n",
        "--max_rectangles",
        type=int,
        default=20,
        help="Maximum number of rectangles to crop.",
    )
    parser.add_argument(
        "-a",
        "--min_area",
        type=int,
        default=1000,
        help="Minimum area of rectangles to consider.",
    )
    args = parser.parse_args()

    crop_and_rotate_rectangles(
        args.image_path, args.output_dir, args.max_rectangles, args.min_area
    )


if __name__ == "__main__":
    main()
