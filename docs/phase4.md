# Phase 4: File Management and Export

## Objectives
- Implement file organization system
- Add batch processing capabilities
- Create export options
- Add file history tracking

## Steps

### 1. File Organization
```python
class FileManager:
    def __init__(self, base_dir="output"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.history_file = self.base_dir / "processing_history.json"
        self.load_history()
    
    def load_history(self):
        """Load processing history from JSON file"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = []
    
    def save_history(self):
        """Save processing history to JSON file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def add_to_history(self, file_info):
        """Add processed file information to history"""
        self.history.append({
            'filename': file_info['filename'],
            'processed_at': datetime.now().isoformat(),
            'status': file_info['status'],
            'output_path': str(file_info['output_path']),
            'model_used': file_info['model_used']
        })
        self.save_history()
```

### 2. Batch Processing
```python
def process_batch(files, file_manager, progress_placeholder):
    """Process multiple files with progress tracking"""
    total_files = len(files)
    
    for idx, file in enumerate(files, 1):
        progress_placeholder.progress(idx / total_files)
        
        try:
            # Process individual file
            result = process_single_file(file)
            
            # Update history
            file_manager.add_to_history({
                'filename': file.name,
                'status': 'success' if result else 'failed',
                'output_path': result['output_path'] if result else None,
                'model_used': st.session_state.model_type
            })
            
        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")
```

### 3. Export Options
```python
def create_export_options(processed_files):
    """Create export interface for processed files"""
    st.sidebar.header("Export Options")
    
    # Single file export
    if len(processed_files) == 1:
        if st.sidebar.button("Download CSV"):
            file_path = processed_files[0]['output_path']
            with open(file_path, 'r') as f:
                csv_data = f.read()
            st.download_button(
                "Download CSV file",
                csv_data,
                file_name=processed_files[0]['filename'].replace('.pdf', '.csv'),
                mime='text/csv'
            )
    
    # Batch export
    else:
        if st.sidebar.button("Download All as ZIP"):
            with zipfile.ZipFile("processed_files.zip", 'w') as zipf:
                for file_info in processed_files:
                    zipf.write(file_info['output_path'])
            
            with open("processed_files.zip", 'rb') as f:
                st.download_button(
                    "Download ZIP file",
                    f.read(),
                    file_name="processed_files.zip",
                    mime='application/zip'
                )
```

### 4. History Display
```python
def display_history(file_manager):
    """Display processing history with filtering options"""
    st.header("Processing History")
    
    # Filter options
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "Success", "Failed"]
    )
    
    date_range = st.date_input(
        "Filter by date range",
        value=(datetime.now() - timedelta(days=7), datetime.now())
    )
    
    # Filter history
    filtered_history = filter_history(
        file_manager.history,
        status_filter,
        date_range
    )
    
    # Display as table
    if filtered_history:
        df = pd.DataFrame(filtered_history)
        st.dataframe(df)
        
        # Export history
        if st.button("Export History to CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                "Download History CSV",
                csv,
                "processing_history.csv",
                "text/csv"
            )
```

### 5. Testing
- Test batch processing with multiple files
- Verify history tracking and filtering
- Check export functionality
- Validate file organization

## Expected Outcome
- Organized file management system
- Efficient batch processing
- Multiple export options
- Searchable processing history
