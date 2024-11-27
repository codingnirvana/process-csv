import os
import google.generativeai as genai
import atexit
import signal
import logging
import warnings
from absl import logging as absl_logging
import streamlit as st
import csv
import tempfile
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress absl logging noise
absl_logging.set_verbosity(absl_logging.ERROR)
warnings.filterwarnings('ignore', category=ResourceWarning)

# Global model instance
model = None

def cleanup():
    """Cleanup function to be called on exit"""
    global model
    if model:
        try:
            del model
            logging.info("Cleaned up model instance")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

def get_settings():
    """Get user settings"""
    try:
        return {
            'gemini_api_key': 'your_api_key_here',
            'model': 'gemini-1.5-flash'
        }
        
    except Exception as e:
        logging.error(f"Error getting settings: {str(e)}")
        raise ValueError(f"Failed to get settings: {str(e)}")

def get_model():
    """Get or create the Gemini model instance"""
    global model
    if model is None:
        try:
            # Check if settings exist
            settings = get_settings()
            
            # Check for API key
            if not settings.get('api_key'):
                raise ValueError("Gemini API key not configured. Please check settings.")
            
            # Configure the model
            genai.configure(api_key=settings['api_key'])
            
            generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            }
            
            model = genai.GenerativeModel(
                settings.get('model', 'gemini-1.5-flash'),
                generation_config=generation_config
            )
            logging.info(f"Successfully configured Gemini model with {settings.get('model')}")
            
        except ValueError as ve:
            # Re-raise ValueError with clear message
            raise ValueError(str(ve))
        except Exception as e:
            logging.error(f"Error configuring Gemini model: {str(e)}")
            raise ValueError(f"Failed to configure Gemini model: {str(e)}")
    return model

def extract_csv_from_pdf(pdf_path):
    """Uploads a PDF and extracts CSV data using Gemini API."""
    try:
        # Get model with better error handling
        try:
            model = get_model()
        except ValueError as e:
            st.error(str(e))
            return None
            
        # Read the PDF file
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        # Create the prompt
        prompt = """Extract data from this PDF into CSV format. 
        Follow these rules:
        1. First row should be column headers
        2. Use comma as delimiter
        3. Each data point should be in its own column
        4. Preserve all numerical values exactly as they appear
        5. Include all tables and structured data
        6. Skip any headers, footers, or non-tabular content
        """
        
        # Process with Gemini
        response = model.generate_content(
            [prompt, {"mime_type": "application/pdf", "data": pdf_data}]
        )
        
        if response.text:
            return response.text
        else:
            logging.error("No CSV data extracted from PDF")
            return None
            
    except Exception as e:
        logging.error(f"Error in extract_csv_from_pdf: {str(e)}")
        st.error(f"Error processing PDF: {str(e)}")
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
        csv_path = os.path.join("/Users/rajeshm/Downloads/stp_files/csv_flash/", csv_filename)

        # Ensure output directory exists
        if not os.path.exists("/Users/rajeshm/Downloads/stp_files/csv_flash/"):
            os.makedirs("/Users/rajeshm/Downloads/stp_files/csv_flash/")

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
    
    process_pdfs("/Users/rajeshm/Downloads/stp_files/", "/Users/rajeshm/Downloads/stp_files/csv_flash/")
else:
    # When imported as a module, just register cleanup
    atexit.register(cleanup)
