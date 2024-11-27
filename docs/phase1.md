# Phase 1: Basic Streamlit Setup and File Upload

## Objectives
- Set up basic Streamlit application
- Integrate with existing process_csv.py functions
- Create settings sidebar
- Implement file upload and processing

## Steps

### 1. Update Dependencies
Add to `requirements.txt`:
```
streamlit>=1.30.0
pandas>=2.0.0
```

### 2. Create Basic App Structure
Create `app.py`:

```python
import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
import os
from process_csv import extract_csv_from_pdf, save_csv_data

def process_single_file(uploaded_file, progress_bar, status_text):
    """Process a single PDF file using existing functions"""
    try:
        # Create a temporary file to store the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            pdf_path = tmp_file.name

        # Update status
        status_text.text("Extracting CSV data...")
        progress_bar.progress(25)

        # Extract CSV data using existing function
        csv_data = extract_csv_from_pdf(pdf_path)
        if not csv_data:
            raise Exception("Failed to extract CSV data")

        progress_bar.progress(75)
        status_text.text("Saving CSV data...")

        # Create output path
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        csv_path = output_dir / f"{uploaded_file.name[:-4]}.csv"

        # Save CSV data using existing function
        save_csv_data(csv_data, str(csv_path))

        progress_bar.progress(100)
        status_text.text("Processing complete!")

        return {
            'csv_data': csv_data,
            'csv_path': csv_path
        }

    except Exception as e:
        raise Exception(f"Error processing {uploaded_file.name}: {str(e)}")

    finally:
        # Clean up temporary file
        if 'pdf_path' in locals():
            os.unlink(pdf_path)

def main():
    st.set_page_config(
        page_title="PDF to CSV Converter",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("PDF to CSV Converter")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        model_type = st.selectbox(
            "Select Model",
            ["gemini-1.5-flash", "gemini-1.5-pro"],
            help="Flash: Faster & cheaper. Pro: More accurate but costly"
        )
        
        output_dir = st.text_input(
            "Output Directory",
            value="output",
            help="Directory where CSV files will be saved"
        )
    
    # Main content
    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type="pdf",
        accept_multiple_files=True
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.write(f"Processing: {uploaded_file.name}")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                result = process_single_file(uploaded_file, progress_bar, status_text)
                st.success(f"Successfully processed {uploaded_file.name}")
                
                # Store CSV data in session state for visualization
                if result:
                    st.session_state[f"csv_data_{uploaded_file.name}"] = result['csv_data']
                    
                    # Preview CSV data
                    with st.expander("Preview CSV Data"):
                        df = pd.read_csv(result['csv_path'])
                        st.dataframe(df)
                        
                        # Add download button
                        st.download_button(
                            "Download CSV",
                            result['csv_data'],
                            file_name=f"{uploaded_file.name[:-4]}.csv",
                            mime="text/csv"
                        )
                
            except Exception as e:
                st.error(str(e))
            
            finally:
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()

if __name__ == "__main__":
    main()
```

### 3. Run the App
```bash
streamlit run app.py
```

### 4. Testing
- Test file upload with different PDF sizes
- Verify model selection affects processing
- Check CSV output and preview
- Validate error handling

## Expected Outcome
- Working Streamlit interface
- Integration with existing PDF processing functions
- CSV preview and download functionality
- Basic error handling and progress tracking
