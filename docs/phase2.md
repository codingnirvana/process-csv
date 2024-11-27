# Phase 2: Progress Tracking and Processing

## Objectives
- Implement progress tracking for file processing
- Add background processing capabilities
- Create detailed error handling
- Add processing logs

## Steps

### 1. Add Progress Tracking
Update `app.py` to include progress bars:

```python
def process_file(uploaded_file, progress_bar, status_text):
    try:
        # Save uploaded file temporarily
        temp_path = Path("temp") / uploaded_file.name
        temp_path.parent.mkdir(exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Process file with progress updates
        for i in range(100):
            time.sleep(0.1)  # Simulate processing
            progress_bar.progress(i + 1)
            status_text.text(f"Processing step {i+1}/100")
            
        return True
        
    except Exception as e:
        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        return False
    finally:
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

def main():
    # ... previous code ...
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.write(f"Processing: {uploaded_file.name}")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            if process_file(uploaded_file, progress_bar, status_text):
                st.success(f"Successfully processed {uploaded_file.name}")
            
            # Clear progress bar and status
            progress_bar.empty()
            status_text.empty()
```

### 2. Add Processing Logs
```python
def setup_logging():
    # Create a StringIO object to capture log output
    log_stream = io.StringIO()
    
    # Configure logging to write to StringIO
    logging.basicConfig(
        stream=log_stream,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_stream

def main():
    # ... previous code ...
    
    # Add log display area
    with st.expander("Processing Logs", expanded=False):
        log_stream = setup_logging()
        log_placeholder = st.empty()
        
        # Update logs periodically
        def update_logs():
            while True:
                log_placeholder.code(log_stream.getvalue())
                time.sleep(1)
```

### 3. Error Handling
Add comprehensive error handling:
```python
def handle_error(error, context):
    """Handle different types of errors with appropriate messages"""
    if isinstance(error, FileNotFoundError):
        st.error(f"File not found: {context}")
    elif isinstance(error, PermissionError):
        st.error(f"Permission denied: {context}")
    elif isinstance(error, Exception):
        st.error(f"An error occurred while {context}: {str(error)}")
    
    logging.error(f"Error in {context}: {str(error)}")
```

### 4. Testing
- Test with multiple simultaneous uploads
- Verify progress tracking accuracy
- Check error handling for various scenarios
- Validate log output

## Expected Outcome
- Real-time progress tracking
- Detailed processing logs
- Robust error handling
- Smooth multi-file processing
