import os
import google.generativeai as genai
import logging
import warnings
from absl import logging as absl_logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress absl logging noise
absl_logging.set_verbosity(absl_logging.ERROR)
warnings.filterwarnings('ignore', category=ResourceWarning)

def extract_csv_from_pdf(pdf_path, api_key, model_name='gemini-1.5-flash'):
    """Extracts CSV data from a PDF file using Gemini API."""
    try:
        if not api_key:
            raise ValueError("Gemini API key not configured")
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            }
        )
            
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
        return None

def save_csv_data(csv_data, csv_path):
    """Saves the extracted CSV data to a file."""
    try:
        logging.info(f"Saving CSV to: {csv_path}")
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            csvfile.write(csv_data)
        logging.info("CSV saved successfully")
        return True
    except Exception as e:
        logging.error(f"Error saving CSV to {csv_path}: {e}")
        return False

def process_pdf_to_csv(pdf_path, api_key, model_name='gemini-1.5-flash'):
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
        csv_data = extract_csv_from_pdf(pdf_path, api_key, model_name)
        
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
    api_key = os.getenv('GEMINI_API_KEY', '')
    model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    pdf_path = "/Users/rajeshm/Downloads/stp_files/your_pdf_file.pdf"
    process_pdf_to_csv(pdf_path, api_key, model_name)
