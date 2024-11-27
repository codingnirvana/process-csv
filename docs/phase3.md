# Phase 3: File Visualization

## Objectives
- Implement PDF preview functionality
- Create CSV data visualization
- Build side-by-side view comparison
- Add search and navigation features

## Steps

### 1. PDF Preview Implementation
```python
import PyPDF2
import base64

def display_pdf(pdf_file):
    """Display PDF file in Streamlit"""
    # Create base64 encoded version of PDF
    base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
    
    # Embed PDF viewer
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
    
    # Add navigation controls
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("⬅️ Previous"):
            st.session_state.pdf_page = max(0, st.session_state.pdf_page - 1)
    with col2:
        st.write(f"Page {st.session_state.pdf_page + 1} of {st.session_state.pdf_pages}")
    with col3:
        if st.button("Next ➡️"):
            st.session_state.pdf_page = min(st.session_state.pdf_pages - 1, st.session_state.pdf_page + 1)
```

### 2. CSV Data Display
```python
def display_csv(csv_data):
    """Display CSV data with interactive features"""
    # Convert CSV string to DataFrame
    df = pd.read_csv(io.StringIO(csv_data))
    
    # Add search functionality
    search_term = st.text_input("Search in CSV data")
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
        df = df[mask]
    
    # Add column filters
    col_to_filter = st.selectbox("Filter by column", ["None"] + list(df.columns))
    if col_to_filter != "None":
        unique_values = df[col_to_filter].unique()
        selected_value = st.selectbox(f"Select {col_to_filter}", ["All"] + list(unique_values))
        if selected_value != "All":
            df = df[df[col_to_filter] == selected_value]
    
    # Display DataFrame with pagination
    rows_per_page = st.number_input("Rows per page", min_value=5, value=10)
    page_number = st.number_input("Page", min_value=1, value=1)
    start_idx = (page_number - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    
    st.dataframe(df.iloc[start_idx:end_idx])
    st.write(f"Showing {len(df)} rows")
```

### 3. Side-by-Side View
```python
def main():
    # ... previous code ...
    
    if uploaded_files:
        # Create two columns for side-by-side view
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("PDF View")
            display_pdf(uploaded_files[0])
        
        with col2:
            st.header("CSV Data")
            if 'csv_data' in st.session_state:
                display_csv(st.session_state.csv_data)
```

### 4. Add Search and Navigation
```python
def add_search_functionality():
    """Add search capabilities to both PDF and CSV views"""
    st.sidebar.header("Search")
    
    # PDF search
    pdf_search = st.sidebar.text_input("Search in PDF")
    if pdf_search and 'pdf_text' in st.session_state:
        results = find_in_pdf(st.session_state.pdf_text, pdf_search)
        if results:
            st.sidebar.write(f"Found {len(results)} matches")
            for page, pos in results:
                if st.sidebar.button(f"Go to match on page {page}"):
                    st.session_state.pdf_page = page - 1
    
    # CSV search
    csv_search = st.sidebar.text_input("Search in CSV")
    if csv_search and 'csv_data' in st.session_state:
        update_csv_view(csv_search)
```

### 5. Testing
- Test PDF navigation
- Verify CSV filtering and search
- Check side-by-side view responsiveness
- Validate search functionality

## Expected Outcome
- Interactive PDF viewer
- Searchable CSV display
- Synchronized side-by-side view
- Smooth navigation and search features
