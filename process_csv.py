import os
import base64
import google.generativeai as genai
from dotenv import load_dotenv
import csv
import time
from tqdm import tqdm
from PyPDF2 import PdfReader, PdfWriter
import io
import datetime
import random
import argparse
import atexit
import signal
import traceback

# Suppress gRPC warning
os.environ['GRPC_PYTHON_LOG_LEVEL'] = 'error'

# Load environment variables from .env file
load_dotenv()

# Initialize the Gemini API with your API key
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Global model instance
model = None

def cleanup(signum=None, frame=None):
    """Clean up resources before exit."""
    try:
        # Clear the current line (in case we're in a progress bar)
        print('\r' + ' ' * 80 + '\r', end='', flush=True)
    except:
        pass
    finally:
        if signum is not None:
            exit(0)

# Register cleanup handlers
atexit.register(cleanup)
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def get_model():
    """Get or create the Gemini model instance"""
    global model
    if model is None:
        generation_config = {
            "temperature": 0.1,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
            "top_p": 0.1,
            "top_k": 16
        }
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
    return model

def handle_rate_limit(e, page_num=None):
    """Handle rate limit errors with exponential backoff"""
    if "rate limit exceeded" in str(e).lower():
        wait_time = random.randint(60, 120)  # Random wait between 1-2 minutes
        if page_num is not None:
            print(f"\nRate limit hit on page {page_num + 1}. Waiting {wait_time} seconds...")
        else:
            print(f"\nRate limit hit. Waiting {wait_time} seconds...")
        time.sleep(wait_time)
        return True
    return False

def get_extraction_prompt(file_type="", page_info=""):
    """Get the appropriate prompt for data extraction."""
    base_prompt = """Extract ALL tabular data from this {file_type}{page_info} and format it as CSV. Additionally, identify the collection date and station code if present.
    
    Important Instructions:
    1. FIRST, extract key metadata and return on the FIRST line in this format:
       #METADATA:YYYY-MM;XXX
       where:
       - YYYY-MM is the collection date (optional, e.g., 2020-08)
       - XXX is the station code (optional)
       Example: #METADATA:2020-08;123
       Note: Leave empty fields blank but keep the semicolon
       Examples: 
       - Just date: #METADATA:2020-08;
       - Just station: #METADATA:;123
       - No metadata: #METADATA:;
       
    2. Then identify the main data table in the document
    3. Extract EVERY row from the identified table
    4. Include the COMPLETE header row exactly as shown
    5. Keep ALL columns present in the table
    6. Preserve ALL numerical values exactly as they appear
    7. Format dates consistently with the source
    8. Format as proper CSV with commas between fields
    9. Each row must be on a new line
    10. Do not summarize, calculate, or modify any data
    11. If there are multiple tables, focus on the largest/main table
    12. Preserve units in column headers (e.g., "Value in mg/L")
    
    Critical Column Alignment Rules:
    1. Count the TOTAL number of columns in the header row
    2. Each data row MUST have exactly the same number of columns as the header
    3. Values MUST align with their correct column headers
    4. If a column is empty in a row:
       - Add an empty field (i.e., two commas together)
       - Do NOT shift values from other columns to fill the gap
    5. For merged cells or spanning columns:
       - Repeat the value across its span width
       - Maintain alignment with headers above
    
    Value Handling Rules:
    1. For missing or empty values:
       - Use empty field (two commas: ,,)
    2. For unclear or unreadable values:
       - Use "???" for completely unreadable values
       - Use "?" for unclear digits (e.g., "12?.?5")
    3. For merged or spanning cells:
       - Repeat the value in all relevant columns
    
    Example Output Format:
    #METADATA:2020-08;123
    Header1,Header2,Header3,Header4,Header5
    value1,,value3,value4,value5
    value1,value2,,,value5
    
    Extract the data following these rules exactly."""
    
    return base_prompt.format(
        file_type=file_type,
        page_info=f" (page {page_info})" if page_info else ""
    )

def generate_output_filename(input_file, metadata=None, page_num=None):
    """Generate output filename based on input file and page number."""
    # Get the base name without extension
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # Start with the base name
    parts = [base_name]
    
    # Add page number if it's a multi-page document
    if page_num is not None:
        parts.append(f"page{page_num + 1}")
    
    # Join all parts with underscores and add .csv extension
    return f"{'_'.join(parts)}.csv"

def save_csv_data(csv_data, output_dir, input_file, metadata=None, page_num=None):
    """Save CSV data to a file with proper naming."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        output_filename = generate_output_filename(input_file, page_num=page_num)
        output_path = os.path.join(output_dir, output_filename)
        
        # Skip if file already exists
        if os.path.exists(output_path):
            print(f"Skipping existing file: {output_filename}")
            return True
        
        # Save the CSV data
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_data)
        
        print(f"Created: {output_filename}")
        return True
        
    except Exception as e:
        print(f"Error saving CSV: {e}")
        return False

def extract_csv_from_pdf_page(page_content, page_num, max_retries=3):
    """Extract CSV data from a single PDF page with retry logic."""
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Get model instance
            model = get_model()

            # Create parts for the model
            parts = [
                {
                    "inline_data": {
                        "mime_type": "application/pdf",
                        "data": base64.b64encode(page_content).decode()
                    }
                },
                get_extraction_prompt("PDF", f"{page_num + 1}")
            ]

            # Generate response
            response = model.generate_content(parts, stream=False)
            
            if response and response.text:
                csv_data = response.text.strip()
                
                # Remove markdown code block markers if present
                csv_data = csv_data.replace('```csv\\n', '')
                csv_data = csv_data.replace('```\\n', '')
                csv_data = csv_data.replace('```csv', '')
                csv_data = csv_data.replace('```', '')
                csv_data = csv_data.strip()
                
                return csv_data
            else:
                print(f"\nNo text response received for page {page_num + 1}")
                if response:
                    print(f"Response object exists but has no text: {response}")
                
        except Exception as e:
            if handle_rate_limit(e, page_num):
                retry_count += 1
                if retry_count < max_retries:
                    continue
                else:
                    print(f"\nMax retries ({max_retries}) reached for page {page_num + 1}")
            else:
                print(f"\nError processing page {page_num + 1}: {str(e)}")
                import traceback
                print(traceback.format_exc())
            
        return None

def extract_csv_from_file(file_path, output_dir, main_pbar):
    """Uploads a file (PDF or JPG) and extracts CSV data using Gemini API."""
    try:
        # Get file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # Check if output file already exists for single-page files
        if file_ext in ['.jpg', '.jpeg']:
            output_filename = generate_output_filename(file_path)
            if os.path.exists(os.path.join(output_dir, output_filename)):
                print(f"Skipping existing file: {output_filename}")
                main_pbar.update(1)
                return [os.path.join(output_dir, output_filename)]
        
        # Handle PDF files
        if file_ext == '.pdf':
            csv_files_created = []
            pdf_reader = PdfReader(file_path)
            
            # Check if all pages already exist
            all_pages_exist = True
            for page_num in range(len(pdf_reader.pages)):
                output_filename = generate_output_filename(file_path, page_num=page_num)
                if not os.path.exists(os.path.join(output_dir, output_filename)):
                    all_pages_exist = False
                    break
            
            if all_pages_exist:
                print(f"Skipping existing PDF: {os.path.basename(file_path)}")
                main_pbar.update(len(pdf_reader.pages))
                return [os.path.join(output_dir, generate_output_filename(file_path, page_num=i)) 
                        for i in range(len(pdf_reader.pages))]
            
            # Process PDF pages
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                
                # Convert PDF page to bytes
                writer = PdfWriter()
                writer.add_page(page)
                page_bytes = io.BytesIO()
                writer.write(page_bytes)
                page_content = page_bytes.getvalue()
                
                # Extract CSV data from the page
                csv_data = extract_csv_from_pdf_page(page_content, page_num)
                
                if csv_data:
                    # Save the CSV data
                    if save_csv_data(csv_data, output_dir, file_path, page_num=page_num):
                        csv_files_created.append(os.path.join(output_dir, generate_output_filename(file_path, page_num=page_num)))
                
                # Update progress
                main_pbar.update(1)
            
            return csv_files_created

        else:  # JPG
            # Process single image file
            with open(file_path, "rb") as image_file:
                image_data = image_file.read()
                
            # Create parts for the model
            parts = [
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_data).decode()
                    }
                },
                get_extraction_prompt("JPG")
            ]
            
            try:
                # Get model instance
                model = get_model()
                
                # Generate response
                response = model.generate_content(parts, stream=False)
                
                if response and response.text:
                    main_pbar.update(1)
                    # Save the CSV data
                    if save_csv_data(response.text.strip(), output_dir, file_path):
                        return [os.path.join(output_dir, generate_output_filename(file_path))]
                    return []
                else:
                    print(f"\nNo text response received for {file_path}")
                    main_pbar.update(1)
                    return []
                    
            except Exception as api_error:
                print(f"\nAPI Error for {file_path}: {str(api_error)}")
                if hasattr(api_error, 'status_code'):
                    print(f"Status Code: {api_error.status_code}")
                main_pbar.update(1)
                return []

    except Exception as e:
        print(f"\nError processing file {file_path}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        main_pbar.update(1)
        return []

def process_files(input_dir):
    """Processes all PDF and JPG files in a directory."""
    # Create CSV directory within input directory
    output_dir = os.path.join(input_dir, 'csv')
    os.makedirs(output_dir, exist_ok=True)

    # Get list of PDF and JPG files
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.pdf', '.jpg', '.jpeg'))]
    
    if not files:
        print("No PDF or JPG files found in the directory.")
        return

    # Calculate total pages for progress bar
    total_pages = 0
    file_pages = {}
    for file_name in files:
        file_path = os.path.join(input_dir, file_name)
        if file_name.lower().endswith('.pdf'):
            try:
                pdf_reader = PdfReader(file_path)
                pages = len(pdf_reader.pages)
                file_pages[file_name] = pages
                total_pages += pages
            except Exception as e:
                print(f"\nError reading PDF {file_name}: {str(e)}")
                file_pages[file_name] = 0
        else:
            # Count each image as one page
            file_pages[file_name] = 1
            total_pages += 1

    print(f"\nProcessing {len(files)} files ({total_pages} pages total)")
    
    # Create main progress bar for overall progress
    with tqdm(total=total_pages, desc="Overall Progress", unit="page") as main_pbar:
        # Process each file
        for file_name in files:
            file_path = os.path.join(input_dir, file_name)
            csv_files = extract_csv_from_file(file_path, output_dir, main_pbar)
            
            if csv_files:
                print(f"✓ {file_name} -> {len(csv_files)} CSV files")
            else:
                print(f"✗ Failed: {file_name}")
                # Update progress bar even if processing failed
                if file_name not in file_pages:
                    main_pbar.update(1)
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)

def main():
    """Main function to handle command line arguments and process files."""
    parser = argparse.ArgumentParser(description='Process PDF and JPG files to extract CSV data.')
    parser.add_argument('input_dir', help='Directory containing PDF and JPG files to process')
    
    args = parser.parse_args()
    
    # Verify input directory exists
    if not os.path.isdir(args.input_dir):
        print(f"Error: Directory '{args.input_dir}' does not exist.")
        return
    
    # Process the files
    process_files(args.input_dir)

if __name__ == "__main__":
    main()
