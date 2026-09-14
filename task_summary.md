# Task Summary: File Read/Write Function

## Overview
Implemented a generalized function to handle both reading from and writing to various file formats, added it to the tools directory, and updated the project's documentation.

## Actions Taken
1. **Created `tools/file_io.py`**:
   - Developed `read_or_write_file(file_path: str, mode: str = 'r', data: any = None, file_type: str = None)`
   - Integrated logic to handle `txt`, `json`, and `csv` formats automatically based on file extensions.
   - Handled robust checking for missing files when reading, and requirement for data when writing.

2. **Updated `README.md`**:
   - Edited the file catalog tree to showcase `tools/file_io.py` under the `tools/` directory.
   - Updated the Architectural Subsystems table to highlight "file I/O operations" as one of the determinisic tools in `tools/`.

## Location
- The script can be found at `tools/file_io.py`.
- Documentation updates are present in `README.md`.
