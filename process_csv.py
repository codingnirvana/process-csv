import os
import time
import google.generativeai as genai
import csv
from dotenv import load_dotenv
import atexit
import signal
import argparse
import base64
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API key
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

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

def extract_csv_from_file(file_path):
    """Uploads a file (PDF or JPG) and extracts CSV data using Gemini API."""
    try:
        # Get file extension
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Set mime type based on file extension
        mime_type = "application/pdf" if file_extension == ".pdf" else "image/jpeg"
        
        # Create the prompt based on file type
        if file_extension == ".pdf":
            prompt = """Extract all tabular data from this PDF. There is a table of parameters with multiple columns. 
            Please extract all the data from the table  and only that table and format it as a CSV. Ignore any other data/tables/text.
            Include headers if present. Each pdf will have date of collection. Use that as the way to create the filename. F
            For example, if the file name is 31-08-2023.pdf, then the CSV file should be named Aug_2023.csv. Format the data in a clean, structured way."""
        else:  # JPG
            prompt = """This image contains tabular data. There is a table of parameters with multiple columns. 
            Please extract all the data from the table and only that table and format it as a CSV. Ignore any other data/tables/text.
            Include headers if present. Each pdf will have date of collection. Use that as the way to create the filename. F
            For example, if the file name is 31-08-2023.pdf, then the CSV file should be named Aug_2023.csv. Format the data in a clean, structured way."""

        # Get model instance
        model = get_model()

        # Create parts for the model
        parts = [
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(open(file_path, "rb").read()).decode()
                }
            },
            prompt
        ]

        # Generate response
        try:
            response = model.generate_content(parts, stream=False)
            
            if response and response.text:
                return response.text.strip()
            else:
                print(f"No text response received for {file_path}")
                return None
                
        except Exception as api_error:
            print(f"API Error for {file_path}: {str(api_error)}")
            if hasattr(api_error, 'status_code'):
                print(f"Status Code: {api_error.status_code}")
            return None

    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        import traceback
        print(traceback.format_exc())
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


def process_files(input_dir, csv_dir):
    """Processes all PDF and JPG files in a directory."""
    # Create CSV directory if it doesn't exist
    os.makedirs(csv_dir, exist_ok=True)

    # Get list of PDF and JPG files
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.pdf', '.jpg', '.jpeg'))]
    
    if not files:
        print(f"No PDF or JPG files found in {input_dir}")
        return

    print(f"Found {len(files)} files to process")
    
    # Process each file with progress bar
    for file_name in tqdm(files, desc="Processing files", unit="file"):
        file_path = os.path.join(input_dir, file_name)
        base_name = os.path.splitext(file_name)[0]
        csv_path = os.path.join(csv_dir, f"{base_name}.csv")
        
        # Skip if CSV already exists
        if os.path.exists(csv_path):
            tqdm.write(f"Skipping {file_name} - CSV already exists")
            continue
            
        tqdm.write(f"Processing {file_name}...")
        
        # Extract CSV data
        csv_data = extract_csv_from_file(file_path)
        
        if csv_data:
            # Save CSV data
            save_csv_data(csv_data, csv_path)
            tqdm.write(f"Successfully processed {file_name}")
        else:
            tqdm.write(f"Failed to process {file_name}")
        
        # Add a small delay to avoid rate limiting
        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process PDF and JPG files to extract CSV data.')
    parser.add_argument('input_dir', help='Directory containing PDF and JPG files')
    parser.add_argument('output_dir', help='Directory where CSV files will be saved')
    
    args = parser.parse_args()
    
    # Convert relative paths to absolute paths
    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        exit(1)
        
    process_files(input_dir, output_dir)
