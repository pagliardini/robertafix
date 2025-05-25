# python-prproj-editor

## Overview
This project provides a tool for batch processing Adobe Premiere Pro project files (.prproj) by allowing users to extract, edit, and repackage the XML content within these files.

## Features
- Create copies of .prproj files
- Change file extensions to .zip for extraction
- Extract XML content for editing
- Replace text within the XML files using a graphical user interface (GUI)
- Recompress the edited files back to .prproj format

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd python-prproj-editor
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
1. Place your .prproj files in a designated folder.
2. Run the application:
   ```
   python src/app.py
   ```
3. Follow the GUI prompts to select files and perform text replacements.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.