# Simple Rename

A lightweight file renaming tool built with Python and PyQt6.

## Features

- Simple and efficient file renaming:
  - Direct editing in spreadsheet-like interface
  - Format column for easy file type identification
  - Automatic extension preservation
  - Smart file name validation
  - Backup creation during renaming
  - Detailed operation feedback
- Clean and intuitive interface:
  - Directory browser
  - File list with editable names
  - Status updates
  - Error handling

# History: Building SimpleRename with Perplexity AI

The development of SimpleRename, a powerful bulk file renaming application with a spreadsheet-like interface, was significantly aided by leveraging the capabilities of Perplexity AI. This AI-assisted development process unfolded as follows:

## Conceptualization and Feature Definition

The journey began with a series of queries to Perplexity AI about essential features for mass file renaming applications. These interactions helped refine the initial concept and establish a comprehensive feature set for SimpleRename. The AI provided insights into user-friendly interfaces, efficient renaming algorithms, and advanced functionalities that would set SimpleRename apart from existing solutions.

## Project Structure and Architecture

Perplexity AI was instrumental in designing a robust project structure. When asked to create a folder and file structure for a Python-based file renaming application, the AI generated a detailed layout. This structure included directories for source code (src), tests, resources, and essential root-level files such as main.py, requirements.txt, and setup.py. The suggested architecture promoted modularity and maintainability, crucial for the project's long-term success.

## Component Implementation

For each major component of SimpleRename, Perplexity AI offered tailored advice:

1. **Spreadsheet Interface**: The AI provided guidance on implementing a grid-like interface using PyQt6, suggesting custom widgets and data models to efficiently display and edit file names.

2. **File Selection**: Perplexity AI outlined methods for integrating file and folder selection, including drag-and-drop functionality, utilizing Python's built-in libraries and PyQt6's file dialog components.

3. **Renaming Engine**: Detailed pseudocode and algorithmic approaches were suggested for creating a flexible renaming engine supporting various rules like prefixing, suffixing, and regular expression-based renaming.

4. **Preview Functionality**: The AI proposed strategies for implementing real-time preview of renaming changes, emphasizing the importance of efficiency and user feedback.

## Advanced Features

Perplexity AI's suggestions were crucial in implementing advanced features:

1. **Undo/Redo Functionality**: The AI outlined a command pattern implementation for tracking and reversing renaming operations.

2. **Configuration Management**: Advice was provided on serializing and deserializing application settings and renaming configurations.

3. **Filtering and Sorting**: The AI suggested efficient algorithms for filtering and sorting large lists of files based on various criteria.

## Testing Strategy

A comprehensive testing strategy was developed with Perplexity AI's assistance. This included:

1. Unit tests for core functionalities like file operations and the renaming engine.
2. Integration tests for the GUI components using PyQt's testing framework.
3. End-to-end tests simulating user workflows.

The AI provided sample test cases and best practices for test-driven development in Python.

## Packaging and Distribution

Finally, Perplexity AI offered guidance on packaging SimpleRename for distribution:

1. Using PyInstaller to create a standalone executable for Windows.
2. Creating an installer with NSIS (Nullsoft Scriptable Install System).
3. Strategies for managing dependencies and ensuring compatibility across different Windows versions.

Throughout the development process, Perplexity AI served as an invaluable resource, providing detailed, context-aware responses to specific implementation challenges. This AI-assisted approach significantly accelerated the development cycle and contributed to the creation of a robust, feature-rich application that effectively addresses the complexities of bulk file renaming.

## Installation

### Prerequisites
- Python 3.8 or higher
- Git
- pip (Python package manager)

You can verify your installations with:
```bash
python --version
git --version
pip --version
```

### From Source
```bash
# Clone the repository
git clone https://github.com/yourusername/simplerename.git
cd simplerename

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .
```

### Using PyInstaller
```bash
# Build standalone executable
python setup.py
pyinstaller simplerename.spec
```
The executable will be available in the `dist` directory.

## Usage

### GUI Application
```bash
# Run the application
simplerename
```

### Basic Operations

1. **Open Directory**: File > Open Directory or Ctrl+O
2. **Select Files**: Click files in the list or use filters
3. **Configure Rename Options**:
   - Add prefix/suffix
   - Set find/replace patterns
   - Configure numbering
4. **Preview**: Changes are previewed before applying
5. **Apply**: Click "Apply" to rename files

### Advanced Features

- **Filters**: Use the filter panel to narrow down file selection
- **Sorting**: Click column headers or use sort menu
- **Configurations**: Save frequently used settings
- **History**: Access rename history for undo/redo

## Testing

### Running Tests
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_file_operations.py

# Run tests matching specific pattern
pytest -k "test_rename"
```

### Test Organization
- `tests/test_file_operations.py`: File system operation tests
- `tests/test_gui_components.py`: GUI component tests
- `tests/test_history_manager.py`: Undo/redo functionality tests
- `tests/test_renaming_engine.py`: File renaming logic tests
- `tests/test_main.py`: Application integration tests

### Writing Tests
1. Create test files in the `tests` directory
2. Use pytest fixtures for common setup
3. Follow the naming convention `test_*.py`
4. Group related tests in classes
5. Use appropriate assertions and error messages
6. Mock external dependencies when necessary

### Contributing Tests
1. Ensure all new features have corresponding tests
2. Maintain test coverage above 80%
3. Use meaningful test names and descriptions
4. Document any complex test setups
5. Add fixtures to `conftest.py` for shared resources

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details
