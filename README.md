# PDF to CSV Converter using Gemini API

This tool converts PDF files containing tabular data into CSV format using Google's Gemini API. It maintains column headers, numerical values, and handles various data formats including currencies and dates.

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
   Get your API key from: https://aistudio.google.com/app/apikey

## Configuration

### Directory Setup
1. Create a directory for your PDF files
2. Create a subdirectory named `csv` within your PDF directory for the output files
3. Update `PDF_DIR` and `CSV_DIR` in `gemini-csv.py` to point to your directories

### Model Selection
The script supports two Gemini models:
- `gemini-1.5-pro`: More accurate but costlier
- `gemini-1.5-flash`: Faster and cheaper but less accurate

To switch models, modify the `model_name` parameter in `get_model()` function.

## Usage

1. Place your PDF files in your configured PDF directory
2. Run the script:
   ```bash
   python gemini-csv.py
   ```
3. The script will:
   - Process all PDF files in the input directory
   - Convert tables to CSV format
   - Save CSV files in the output directory

## Error Handling

- The script includes error handling for file processing and API calls
- Check the console output for any error messages
- Failed conversions will be logged but won't stop the entire process

## Dependencies

- google-generativeai
- python-dotenv
- requests
