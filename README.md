# Card Tools

Utilities for processing card images - detecting rectangles, cropping, rotating, and trimming whitespace.

## Installation

### Dependencies

- Python 3.6+
- OpenCV (`opencv-python`)
- NumPy
- ImageMagick (for whitespace trimming)

### Install from Source

```bash
# Install in development mode
pip install -e .

# Or for a regular installation
pip install .
```

## Tools

### process-cards

The main combined tool that handles the full workflow:

1. Detecting rectangles in images
2. Cropping and rotating them
3. Trimming whitespace from the cropped images

```bash
python process_cards.py image1.jpg image2.png
```

#### Command Line Options

- `input_files`: One or more input image files (supports glob patterns like `*.jpg`)
- `-n, --max_rectangles`: Maximum number of rectangles to crop per image (default: 20)
- `-a, --min_area`: Minimum area of rectangles to consider (default: 1000)
- `-c, --contours`: Save visualization of detected contours

#### Example

```bash
# Process all JPG files in a directory
python process_cards.py "images/*.jpg"

# Process with contour visualization
python process_cards.py image.jpg -c

# Process with custom settings
python process_cards.py image.jpg -n 10 -a 2000
```

#### Output Directory Structure

All processed images are saved in a timestamped directory:

```
processed/
└── YYYY-MM-DD_HH-MM-SS/
    ├── original_image-cropped-1.png
    ├── original_image-cropped-2.png
    ├── original_image-contours.png (if -c option used)
    └── trimmed/
        ├── original_image-cropped-1-trimmed.png
        └── original_image-cropped-2-trimmed.png
```

### find-recs

Finds, crops, and rotates rectangular card images.

```bash
find-recs path/to/image.jpg
```

Options:

- `-o`, `--output_dir`: Output directory (default: "cropped_rectangles")
- `-n`, `--max_rectangles`: Maximum number of rectangles to crop (default: 20)
- `-a`, `--min_area`: Minimum area of rectangles to consider (default: 1000)

### trim-whitespace

Trims whitespace from images using ImageMagick.

```bash
trim-whitespace path/to/image.jpg
```

Note: Requires ImageMagick to be installed. On Ubuntu/Debian, install with:

```bash
sudo apt-get install imagemagick
```

For system-wide OpenCV on Ubuntu/Debian:

```bash
sudo apt install python3-opencv
```

## Python API

```python
# Import individual functions
from find_recs import crop_and_rotate_rectangles
from trim_whitespace import trim_image

# Find and crop rectangles
crop_and_rotate_rectangles("image.jpg", output_dir="output", max_rectangles=5)

# Trim whitespace from an image
trim_image("image.jpg")

# Or use the combined process_cards functionality
from process_cards import process_image, create_output_directory

# Create a timestamped output directory
output_dir = create_output_directory()

# Process an image (detect rectangles, crop, rotate, and trim whitespace)
process_image("image.jpg", output_dir, max_rectangles=5, min_area=1000, draw_contours=True)
```
