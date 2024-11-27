# PDF to CSV Converter with Gemini AI

A powerful web application that converts PDF tables to CSV format using Google's Gemini AI, with integrated Google Drive support for seamless file management.

## Features

- **AI-Powered Extraction**: Uses Gemini AI to intelligently extract tabular data from PDFs
- **Google Drive Integration**: Upload, process, and download files directly from Google Drive
- **Web Interface**: Clean, intuitive Streamlit-based user interface
- **Flexible Configuration**: Support for both web app and command-line usage
- **Secure Authentication**: OAuth 2.0 integration with Google Drive

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

3. Set up environment variables in `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

## Usage

### Web Application

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. Configure your Gemini API key in the settings

4. Connect to Google Drive when prompted

5. Select input/output folders and process your PDFs

### Command Line Interface

Process a single PDF file:
```bash
python process_csv.py input.pdf --api_key your_api_key
```

Options:
- `pdf_path`: Path to input PDF file (required)
- `--api_key`: Gemini API key (optional if set in environment)
- `--model`: Gemini model name (default: gemini-1.5-flash)

The output CSV will be created in the same directory as the input PDF.

## Project Structure

- `app.py`: Main web application
- `process_csv.py`: Core PDF processing logic
- `settings.py`: Settings management
- `browser_storage.py`: Local storage handling
- `gdrive_handler.py`: Google Drive integration

## Dependencies

- streamlit
- google-generativeai
- google-auth-oauthlib
- google-api-python-client
- python-dotenv
- streamlit-local-storage
- PyPDF2
- pandas
- absl-py

## Development

1. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Unix
venv\Scripts\activate     # Windows
```

2. Install development dependencies:
```bash
pip install -r requirements.txt
```

## Production Deployment

1. Set up Google OAuth:
   - Configure OAuth consent screen
   - Get verification from Google
   - Update production redirect URIs

2. Configure environment:
   - Set `PRODUCTION=true`
   - Set `APP_URL` to your domain
   - Configure SSL/HTTPS
   - Set up proper API keys

## License

[Your chosen license]

## Contributing

[Your contribution guidelines]
