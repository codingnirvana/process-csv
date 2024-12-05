# PDF and Image to CSV Converter

This script processes PDF documents and JPG images containing tabular data and converts them into CSV format using the Google Gemini API.

## Features

- Processes both PDF documents and JPG/JPEG images
- Extracts tabular data and converts it to CSV format
- Supports batch processing of multiple files
- Shows progress bar for processing status
- Skips already processed files
- Handles errors gracefully

## Prerequisites

- Python 3.x
- Google Gemini API key

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd process-csv
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the project root with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run the script with input and output directory paths:

```bash
python process_csv.py /path/to/input/directory /path/to/output/directory
```

For example:
```bash
python process_csv.py ~/Documents/input_files ~/Documents/output_csv
```

### Input Files
- Place your PDF and JPG files in the input directory
- Supported file formats: `.pdf`, `.jpg`, `.jpeg`
- Files should contain tabular data

### Output
- CSV files will be created in the output directory
- Each CSV file will be named based on the input file's name
- Existing CSV files will not be overwritten

## Error Handling

The script includes error handling for:
- Invalid file formats
- API errors
- File reading/writing errors
- Missing directories

## Dependencies

- google-generativeai: For processing files using Gemini API
- python-dotenv: For loading environment variables
- tqdm: For progress bar visualization
- requests: For API communication

## Notes

- The script adds a 1-second delay between processing files to avoid API rate limiting
- Make sure your input files are readable and contain clear tabular data
- Large files may take longer to process

## Troubleshooting

If you encounter errors:
1. Check if your API key is correctly set in the `.env` file
2. Ensure input files are not corrupted
3. Verify you have sufficient permissions for input/output directories
4. Check your internet connection for API access
