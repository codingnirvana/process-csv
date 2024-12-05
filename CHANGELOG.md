# Changelog

## [2024-11-05] Bug Fixes and Improvements

### Directory Structure Changes
- Simplified output organization
  - Creates a 'csv' folder within the input directory
  - All generated CSV files are stored in this folder
  - No need to specify separate output directory
  - Example: If processing `/data/pdfs`, CSVs will be in `/data/pdfs/csv`

### PDF Processing Improvements
- Fixed multi-page PDF handling
  - Each PDF is now split into individual pages
  - Output files are named as `Month_Year.csv` (e.g., `Mar_2024.csv`)
  - Multiple files for the same month are handled correctly
  - Test: Process any multi-page PDF to verify page splitting

### Metadata Format
- Metadata is preserved in CSV output as header rows:
  ```
  #METADATA:2024-03;STN123
  Date,Value1,Value2,Value3
  2024-03-01,10,20,30
  ```
- Extracts and preserves:
  - Station Code (from "Station Code:" or "Stn Code:")
  - Date of Collection (YYYY-MM format)
- Test: Check first row of CSV files for metadata in correct format

### Table Extraction Enhancement
- Improved table detection and extraction
  - Now focuses only on tabular data, ignoring other content
  - Test: Process PDFs with mixed content (tables and text) to verify only tables are extracted

### Known Limitations ⚠️
- Empty Column Handling (Work in Progress)
  - Issue: Empty columns may not be preserved when text is present
  - Current workaround: Manual verification of column alignment required
  - Status: Investigation ongoing for a permanent solution
  - Impact: May require manual correction for files with mixed empty/filled columns

### File Format Support
- Improved JPEG file handling
  - Added support for various JPEG quality levels
  - Test: Process sample JPEG files to verify correct extraction

### Error Handling
- Added robust retry mechanism
  - Automatically retries failed files
  - Shows clear error messages
  - Test: Process a large batch of files to verify retry functionality

### Output Formatting
- Fixed CSV output formatting
  - Removed '```csv' markers from output files
  - Cleaned up empty columns
  - Test: Open generated CSV files to verify clean formatting

### Changed
- Simplified file naming to use only input filename and page numbers
- Changed output directory structure to create 'csv' subdirectory within input directory
- Simplified progress messages and reduced logging verbosity

### Added
- Skip processing of existing CSV files
- Added file existence checks for both single files and PDF pages
- Added gRPC warning suppression
- Added clear progress indicators (✓ for success, ✗ for failure)

To test these changes:
1. Process a multi-page PDF with tables and text
2. Verify metadata row is present and correctly formatted
3. Note: Pay special attention to column alignment in tables with empty columns
4. Test JPEG file processing
5. Verify retry mechanism on failed files
6. Check CSV files for clean formatting
7. Verify CSVs are created in the 'csv' subfolder
