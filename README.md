# PDF and Image to CSV Converter

A Python script that extracts tabular data from PDF and image files using Google's Gemini API, converting them into clean CSV files.

## Features

- Processes both PDF and image files (PDF, JPG, JPEG)
- Handles multi-page PDF documents
- Creates individual CSV files for each page/image
- Skips already processed files to avoid duplicates
- Shows progress bar with page-level tracking
- Handles rate limiting with automatic retries
- Creates organized output in a 'csv' subdirectory

## Requirements

- Python 3.7+
- Google Gemini API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd process-csv
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Gemini API key:
```bash
GEMINI_API_KEY=your_api_key_here
```

## Usage

Run the script by providing the input directory containing your PDF and image files:

```bash
python process_csv.py /path/to/input/directory
```

The script will:
1. Create a 'csv' subdirectory in your input directory
2. Process all PDF and JPG files in the input directory
3. Generate CSV files in the 'csv' subdirectory
4. Skip any files that have already been processed

### Output Format

- For single-page files: `filename.csv`
- For multi-page PDFs: `filename_page1.csv`, `filename_page2.csv`, etc.

## Error Handling

- Automatically retries on rate limit errors
- Skips corrupted or unreadable files
- Provides clear error messages and progress updates

## Limitations

- Requires Gemini API access
- Subject to API rate limits
- Processing time depends on file size and complexity

## Tips

- Keep PDF files under 10MB for best results
- Ensure clear, readable tables in source documents
- Monitor API usage to stay within rate limits
