import os
import time
import google.generativeai as genai
import csv
import tempfile
from dotenv import load_dotenv
import atexit
import signal
import logging
import warnings
from absl import logging as absl_logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress absl logging noise
absl_logging.set_verbosity(absl_logging.ERROR)
warnings.filterwarnings('ignore', category=ResourceWarning)

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API key
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Input and output directories
# Update these paths to point to your PDF and CSV directories
PDF_DIR = "/Users/rajeshm/Downloads/stp_files/"  # Example: "~/Documents/pdfs/"
CSV_DIR = "/Users/rajeshm/Downloads/stp_files/csv_flash/"  # Example: "~/Documents/pdfs/csv/"

# Global model instance
model = None

def cleanup():
    """Cleanup function to handle graceful shutdown"""
    global model
    if model:
        try:
            del model
            logging.info("Cleaned up model instance")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

def get_model():
    """Get or create the Gemini model instance"""
    global model
    if model is None:
        generation_config = {
            "temperature": 0.1,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
    return model

def extract_csv_from_pdf(pdf_path):
    """Uploads a PDF and extracts CSV data using Gemini API."""
    try:
        logging.info(f"Processing PDF: {pdf_path}")
        
        file = genai.upload_file(pdf_path, mime_type="application/pdf")
        logging.info(f"Uploaded file '{file.display_name}' as: {file.uri}")

        # Wait for file to be processed (if necessary)
        while file.state.name == "PROCESSING":
            logging.info("Waiting for file processing...")
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
            logging.info("Successfully extracted CSV data")
            return response.text
        else:
            raise Exception("No response received from the model")
            
    except Exception as e:
        logging.error(f"Error in extract_csv_from_pdf: {str(e)}")
        return None

def save_csv_data(csv_data, csv_path):
    """Saves the extracted CSV data to a file."""
    try:
        logging.info(f"Saving CSV to: {csv_path}")
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            csvfile.write(csv_data)  # Write the CSV string directly
        logging.info("CSV saved successfully")
        return True
    except Exception as e:
        logging.error(f"Error saving CSV to {csv_path}: {e}")
        return False

def process_pdfs(pdf_dir, csv_dir):
    """Processes all PDF files in a directory."""
    logging.info(f"Looking for PDFs in: {pdf_dir}")
    
    if not os.path.exists(pdf_dir):
        logging.error(f"Error: PDF directory does not exist: {pdf_dir}")
        return
        
    if not os.path.exists(csv_dir):
        os.makedirs(csv_dir)

    files = os.listdir(pdf_dir)
    logging.info(f"Found {len(files)} files in directory")
    pdf_files = [f for f in files if f.endswith('.pdf')]
    logging.info(f"Found {len(pdf_files)} PDF files")

    for filename in pdf_files:
        pdf_path = os.path.join(pdf_dir, filename)
        csv_path = os.path.join(csv_dir, filename[:-4] + ".csv")

        logging.info(f"Processing {filename}...")
        try:
            csv_data = extract_csv_from_pdf(pdf_path)

            if csv_data:  # Check if CSV extraction was successful
                save_csv_data(csv_data, csv_path)
                logging.info(f"CSV saved to {csv_path}")
            else:
                logging.error(f"Failed to extract CSV data from {pdf_path}")

        except Exception as e:
            logging.error(f"Error processing {filename}: {e}")


def process_pdf_to_csv(pdf_path):
    """Process a single PDF file and return the result."""
    try:
        # Create a timestamped filename for the CSV
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(pdf_path)
        csv_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.csv"
        csv_path = os.path.join(CSV_DIR, csv_filename)

        # Ensure output directory exists
        if not os.path.exists(CSV_DIR):
            os.makedirs(CSV_DIR)

        # Extract CSV data
        csv_data = extract_csv_from_pdf(pdf_path)
        
        if not csv_data:
            raise Exception("Failed to extract CSV data from PDF")

        # Save CSV data
        save_csv_data(csv_data, csv_path)

        return {
            'csv_data': csv_data,
            'csv_path': csv_path,
            'csv_filename': csv_filename,
            'pdf_path': pdf_path
        }

    except Exception as e:
        logging.error(f"Error in process_pdf_to_csv: {str(e)}")
        raise e


if __name__ == "__main__":
    def signal_handler(signum, frame):
        """Handle interrupt signals"""
        logging.info("Received shutdown signal, cleaning up...")
        cleanup()
        exit(0)

    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    process_pdfs(PDF_DIR, CSV_DIR)
else:
    # When imported as a module, just register cleanup
    atexit.register(cleanup)
