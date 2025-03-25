_disclaimer:_ more than half of this was generated using Claude Code to give me something to modify and play with.

# Card Tools

A collection of scripts and Python tools for processing card images - detecting rectangles, cropping, rotating, and trimming whitespace from large card images.

## General

### SportsCardsPro UserScripts

These have been used with [tampermonkey](https://www.tampermonkey.net/), should work with others.

#### [SportsCardsPro - Add Card Overlay to Checklist.user.js](https://github.com/jessedp/card-tools/blob/main/UserScripts/SportsCardsPro%20-%20Add%20Card%20Overlay%20to%20Checklist.user.js)

When viewing checklists, this adds a new "Add Card" button that will open the add card page in an iframe in the same window and trim some things off to make it quicker to add cards from the same set.

#### [SportsCardsPro - Add Card Form Helpers.user.js](https://github.com/jessedp/card-tools/blob/main/UserScripts/SportsCardsPro%20-%20Add%20Card%20Form%20Helpers.user.js)

On the add card page, this will collapse the Grading options into a toggleable area (defaults to closed) as well as saving the cost and purchase date when you save. Those values will then be prepopulated for the next hour to facilitate adding cards quicker.

#### [SportsCardsPro - Missing Image - Create List.user.js](https://github.com/jessedp/card-tools/blob/main/UserScripts/SportsCardsPro%20-%20Missing%20Image%20-%20Create%20List.user.js)

When clicking the (new green) "Open Missing Image List" button while viewing a category of your collection, the page will scroll to the end (be patient) and collect a list of every card that is displaying the "no image" placeholder and open the list in a new tab so you can go find them.

#### [SportsCardsPro - Missing Images - Show List.user.js](https://github.com/jessedp/card-tools/blob/main/UserScripts/SportsCardsPro%20-%20Missing%20Images%20-%20Show%20List.user.js)

While viewing a category of your collection, hover over the (new green) "Show Missing Images" button - there are two options, both of which modify the list so only ones displaying the "no image" placeholder are shown.

1. **Visible** - this will remove the "load more" functionality and filter out cards from what's currently loaded/visible. By default when the page loads, that's 50 cards max. This can be useful after adding cards and quicker then going through everything. _The page must currently be reloaded to undo this._

2. **All** - like with "Show User List", this scrolls throught the entire category, then applies the "Visible" filtering above, effectively filtering the entire category.

#### [SportscardsPro - Site Wide.user.js](https://github.com/jessedp/card-tools/blob/main/UserScripts/SportscardsPro%20-%20Site%20Wide.user.js)

Currently does two things:

1. Keeps a list of the last 5 useful on-site pages visited and displaus it along with a link to your collection in the upper right.
2. Applies custom styles

### sportscardpro bookmarklets

You'll probably want to [minify](https://www.uglifyjs.net/) these before [saving them as bookmarklets](https://www.freecodecamp.org/news/what-are-bookmarklets/).

#### only shows rows with missing images

```js
javascript: (function () {
  document.querySelectorAll("tr.offer").forEach(function (row) {
    row.style.display = "none";
  });
  document.querySelectorAll("tr.offer").forEach(function (row) {
    if (
      row.querySelector(
        'img[src="https://www.pricecharting.com/images/no-image-available.png"]'
      )
    ) {
      row.style.display = "";
    } else {
      var nextRow = row.nextElementSibling;
      if (nextRow && nextRow.classList.contains("gap")) {
        nextRow.style.display = "none";
      }
    }
  });
})();
```

#### opens new tab with a text list of missing images in the forn "Set - Card info"

```js
javascript: (function () {
  let t = [],
    r = document.querySelectorAll("tr.offer");
  r.forEach((e) => {
    if (
      e.querySelector(
        'img[src="https://www.pricecharting.com/images/no-image-available.png"]'
      )
    ) {
      let n = e.querySelector("p.title");
      if (n) {
        let i = n.innerHTML
          .replace(/<br\/?>/gi, " - ")
          .replace(/<[^>]*>/g, "")
          .trim()
          .replace(/\s+/g, " ")
          .trim()
          .split(" - ");
        if (i.length === 2) {
          i = i[1] + " - " + i[0];
        }
        t.push(i);
      }
    }
  });
  if (t.length > 0) {
    t = t.sort();
    let e = window.open("", "_blank");
    e.document.write(
      "<title>" +
        t.length +
        ' cards missing images</title><textarea style="width:90%;height:90%;">' +
        t.join("\n") +
        "</textarea>"
    );
    e.document.querySelector("textarea").select();
  } else {
    alert("No matching rows found.");
  }
})();
```

## Installation

### Dependencies

- Python 3.6+
- OpenCV (`opencv-python`)
- NumPy
- ImageMagick (for whitespace trimming)

### Install from Source

```bash
# For a regular installation
pip install .

# or to install in development mode
pip install -e .
```

## Tools

### process-cards

The main combined tool that handles the full workflow:

1. Detecting rectangles in images
2. Cropping and rotating them
3. Trimming whitespace from the cropped images

```bash
process-cards image1.jpg image2.png
```

**Uninstalled command:**

```bash
python process_cards.py <args>
```

#### Command Line Options

- `input_files`: One or more input image files (supports glob patterns like `*.jpg`)
- `-n, --max_rectangles`: Maximum number of rectangles to crop per image (default: 20)
- `-a, --min_area`: Minimum area of rectangles to consider (default: 500000 for large cards)
- `-c, --contours`: Save visualization of detected contours

#### Example

```bash
# Process all JPG files in a directory
process-cards "images/*.jpg"

# Process with contour visualization
process-cards image.jpg -c

# Process with custom settings
process-cards image.jpg -n 10 -a 500000
```

#### Output Directory Structure

All processed images are saved in a timestamped directory:

```
processed/
└── YYYY-MM-DD_HH-MM-SS/
    ├── original_image-cropped-1.png
    ├── original_image-cropped-2.png
    ├── original_image-contours-raw.png (if -c option used)
    ├── original_image-contours-filtered.png (if -c option used)
    ├── debug/                        (if -c option used)
    │   ├── original_image-gray.png
    │   ├── original_image-blurred.png
    │   ├── original_image-edges.png
    │   ├── original_image-dilated_edges.png
    │   ├── original_image-rotated-1.png
    │   └── original_image-cropped-debug-1.png
    └── trimmed/
        ├── original_image-cropped-1-trimmed.png
        └── original_image-cropped-2-trimmed.png
```

#### Uninstlalled

```bash
python process_cards.py <args>
```

### find-recs

Finds, crops, and rotates rectangular card images.

```bash
find-recs path/to/image.jpg
```

Options:

- `-o`, `--output_dir`: Output directory (default: "cropped_rectangles")
- `-n`, `--max_rectangles`: Maximum number of rectangles to crop (default: 20)
- `-a`, `--min_area`: Minimum area of rectangles to consider (default: 1000 in the original script, 500000 recommended for large cards)

#### Uninstlalled

```bash
python find_recs.py <args>
```

### trim-whitespace

Trims whitespace from images using ImageMagick.

```bash
trim-whitespace path/to/image.jpg
```

**Uninstalled command:**

```bash
python trim_whitespace.py <args>
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
process_image("image.jpg", output_dir, max_rectangles=5, min_area=500000, draw_contours=True)
```
