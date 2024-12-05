import os
import google.generativeai as genai
import logging
import warnings
from absl import logging as absl_logging
import argparse
from dotenv import load_dotenv
import time

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

def process_pdf_with_gemini(api_key, model, text_content):
    """Process PDF content using Gemini API with rate limit handling"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model)
        
        prompt = """Extract tables from the following text content and convert them to CSV format. 
        If there are multiple tables, process each one separately.
        Return only the CSV content, with no additional text or formatting.
        If no tables are found, respond with 'NO_TABLES_FOUND'.
        
        Text content:
        {text_content}
        """
        
        response = model.generate_content(prompt.format(text_content=text_content))
        
        if not response.text or response.text.strip() == "":
            return "No valid response from the model"
            
        return response.text.strip()
        
    except Exception as e:
        error_msg = str(e).lower()
        if "rate limit" in error_msg:
            return "RATE_LIMIT_ERROR: The API rate limit has been exceeded. Please try again in about an hour."
        elif "quota exceeded" in error_msg:
            return "QUOTA_ERROR: Your API quota has been exceeded. Please check your usage limits."
        else:
            return f"ERROR: {str(e)}"

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
    """Process a PDF file and save the extracted data as CSV"""
    try:
        # Extract CSV data from PDF
        csv_data = extract_csv_from_pdf(pdf_path, api_key, model_name)
        
        if csv_data:
            # Create output filename based on input PDF name
            pdf_filename = os.path.basename(pdf_path)
            csv_filename = os.path.splitext(pdf_filename)[0] + '.csv'
            
            # Save to the same directory as the input PDF
            output_dir = os.path.dirname(pdf_path)
            csv_path = os.path.join(output_dir, csv_filename)
            
            # Save the CSV data
            save_csv_data(csv_data, csv_path)
            logging.info(f"Successfully saved CSV to: {csv_path}")
            return csv_path
        else:
            logging.warning("No data was extracted from the PDF")
            return None
            
    except Exception as e:
        logging.error(f"Error in process_pdf_to_csv: {str(e)}")
        raise e

if __name__ == "__main__":
    # Load environment variables
    load_dotenv(dotenv_path=".env", override=True)
    
    parser = argparse.ArgumentParser(description='Convert PDF tables to CSV format')
    parser.add_argument('pdf_path', help='Path to the input PDF file')
    parser.add_argument('--api_key', help='Gemini API key (optional, can be set via GEMINI_API_KEY env var)')
    parser.add_argument('--model', default='gemini-1.5-flash', help='Gemini model name (default: gemini-1.5-flash)')
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: Gemini API key not provided. Set it via --api_key or GEMINI_API_KEY environment variable")
        exit(1)
    
    try:
        csv_path = process_pdf_to_csv(
            pdf_path=args.pdf_path,
            api_key=api_key,
            model_name=args.model
        )
        
        if csv_path:
            print(f"Successfully converted {args.pdf_path} to {csv_path}")
        else:
            print("No data was extracted from the PDF")
            exit(1)
    
    except FileNotFoundError:
        print(f"Error: Could not find PDF file: {args.pdf_path}")
        exit(1)
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        exit(1)
