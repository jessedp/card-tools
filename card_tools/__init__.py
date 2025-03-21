"""
Card Tools - Utilities for processing card images
"""

# These imports might fail during installation, so wrap them in a try/except
try:
    from find_recs import crop_and_rotate_rectangles
    from trim_whitespace import trim_image, process_input
except ImportError:
    # This allows the package to be installed even if dependencies aren't met yet
    pass

__version__ = "0.1.0"