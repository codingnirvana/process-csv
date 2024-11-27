import os
import time
import google.generativeai as genai
import csv
from dotenv import load_dotenv
import atexit
import signal

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API key
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Input and output directories
# Update these paths to point to your PDF and CSV directories
PDF_DIR = "path/to/pdf/directory"  # Example: "~/Documents/pdfs/"
CSV_DIR = "path/to/csv/directory"  # Example: "~/Documents/pdfs/csv/"

# Global model instance
model = None

def cleanup():
    """Cleanup function to handle graceful shutdown"""
    global model
    if model:
        try:
            del model
        except:
            pass

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    cleanup()
    exit(0)

# Register cleanup handlers
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_model():
    """Get or create the Gemini model instance"""
    global model
    if model is None:
        generation_config = {
            "temperature": 0.1,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        model = genai.GenerativeModel(model_name="gemini-1.5-pro", generation_config=generation_config)
    return model

def extract_csv_from_pdf(pdf_path):
    """Uploads a PDF and extracts CSV data using Gemini API."""
    try:
        file = genai.upload_file(pdf_path, mime_type="application/pdf")
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")

        # Wait for file to be processed (if necessary)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(5)  # Check every 5 seconds
            file = genai.get_file(file.name)

        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process: {file.state.name}")

        # Get model instance
        model = get_model()

        # Prompt Gemini to extract the CSV
        prompt = """Please extract the data from this PDF into CSV format. 
        Follow these guidelines:
        1. Extract all tabular data
        2. Maintain column headers
        3. Output in standard CSV format
        4. Preserve all numerical values
        5. Handle any currency or date formats appropriately"""

        response = model.generate_content([file, prompt])
        
        if response.text:
            return response.text
        else:
            raise Exception("No response received from the model")
            
    except Exception as e:
        print(f"Error in extract_csv_from_pdf: {str(e)}")
        return None


def save_csv_data(csv_data, csv_path):
    """Saves the extracted CSV data to a file."""
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            for row in csv.reader(csv_data.splitlines()):  # Handle potential multi-line cells
                writer.writerow(row)
    except Exception as e:
        print(f"Error saving CSV to {csv_path}: {e}")


def process_pdfs(pdf_dir, csv_dir):
    """Processes all PDF files in a directory."""
    print(f"Looking for PDFs in: {pdf_dir}")
    
    if not os.path.exists(pdf_dir):
        print(f"Error: PDF directory does not exist: {pdf_dir}")
        return
        
    if not os.path.exists(csv_dir):
        os.makedirs(csv_dir)

    files = os.listdir(pdf_dir)
    print(f"Found {len(files)} files in directory")
    pdf_files = [f for f in files if f.endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files")

    for filename in pdf_files:
        pdf_path = os.path.join(pdf_dir, filename)
        csv_path = os.path.join(csv_dir, filename[:-4] + ".csv")

        print(f"Processing {filename}...")
        try:
            csv_data = extract_csv_from_pdf(pdf_path)

            if csv_data:  # Check if CSV extraction was successful
                save_csv_data(csv_data, csv_path)
                print(f"CSV saved to {csv_path}")
            else:
                print(f"Failed to extract CSV data from {pdf_path}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")


if __name__ == "__main__":
    process_pdfs(PDF_DIR, CSV_DIR)
