from setuptools import setup, find_packages

setup(
    name="card-tools",
    version="0.1.0",
    description="Tools for processing card images",
    author="Jesse",
    packages=find_packages(),
    py_modules=["find_recs", "trim_whitespace", "process_cards"],
    install_requires=[
        "opencv-python",
        "numpy",
    ],
    entry_points={
        "console_scripts": [
            "find-recs=find_recs:main",
            "trim-whitespace=trim_whitespace:main",
            "process-cards=process_cards:main",
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)