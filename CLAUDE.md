# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **data analysis web application** that generates statistical reports from Excel files using LLM-powered analysis. It operates in dual modes:
- **WebUI Mode**: Gradio-based chatbot interface (`src/gradio_app.py`)
- **API Mode**: FastAPI REST API (`src/main.py`)

The application is designed for **offline enterprise deployment** using internal Ollama or vLLM models only.

## Development Commands

### Installation
```bash
# Using provided scripts (recommended)
./install.sh        # Linux/macOS
install.bat         # Windows

# Manual installation
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running the Application
```bash
# Start WebUI (Gradio chatbot)
python src/gradio_app.py
# Default: http://0.0.0.0:5600

# Start API server
uvicorn src.main:app --host 0.0.0.0 --port 8001
# API docs: http://127.0.0.1:8001/docs
```

### Configuration
- Copy `api/config.azure.json.example` to `api/config.azure.json`
- Configure your Ollama/vLLM provider endpoints in the Providers section
- Set default model in `Router.default` field

## Architecture

### Core Processing Flow

1. **Input Processing** (`src/file_ingest.py`, `src/excel_parser.py`)
   - Excel files are parsed for structure (date columns, numeric indicators)
   - Optional Word/TXT documents provide supplementary context
   - Two structure recognition modes: LLM-based (default) or heuristic rules

2. **Prompt Analysis** (`src/llm_client.py`)
   - LLM parses user requirements to extract indicators and time windows
   - Indicator disambiguation when multiple similar columns exist
   - Time window resolution (relative dates like "最近一年" → actual date ranges)

3. **Data Analysis** (`src/analysis.py`)
   - Date filtering based on resolved time windows
   - Statistical computation (mean, min, max, percentiles, trends)
   - Time-series chart generation

4. **Report Generation** (`src/report_docx.py`)
   - Creates Word documents with embedded charts and statistics
   - Supports multi-round analysis by appending to existing reports
   - Generates comprehensive summaries across conversation rounds

### Key Modules

| Module | Responsibility |
|--------|---------------|
| `src/excel_parser.py` | Excel structure parsing, column detection, unit extraction |
| `src/llm_client.py` | LLM integration, prompt engineering, specialized parsing functions |
| `src/indicator_resolver.py` | Metric resolution, fuzzy matching, alias handling |
| `src/analysis.py` | Statistical analysis, time window resolution, chart generation |
| `src/report_docx.py` | Word document generation, multi-round append operations |
| `src/file_ingest.py` | File upload handling, context building from documents |
| `src/settings.py` | Configuration management, environment variable overrides |
| `src/gradio_app.py` | WebUI state management, chat interface logic |
| `src/main.py` | FastAPI endpoints, request/response models |

### LLM Integration

The application uses a **modular LLM client** (`src/llm_client.py`) that supports:
- OpenAI-compatible APIs (Ollama, vLLM)
- Multiple specialized prompts for different tasks:
  - Excel structure analysis
  - User prompt parsing (indicators + time windows)
  - Indicator disambiguation (similarity matching)
  - Statistical summarization
  - Comprehensive conversation summarization
- Configurable context windows with automatic limits
- Fallback URL construction for different endpoint formats

### Configuration System

**Priority Order**:
1. Environment variables (`DATA_ANALYSIS_CONFIG_PATH`, `DATA_ANALYSIS_OUTPUT_DIR`, `GRADIO_SERVER_PORT`)
2. Configuration file (`api/config.azure.json`)
3. Default values

**Key Configuration Fields**:
- `Providers[].name`: "ollama" or "vllm"
- `Providers[].api_base_url`: OpenAI-compatible endpoint
- `Providers[].api_key`: Authentication key
- `Providers[].models`: Available model names
- `Router.default`: "provider,model" format (e.g., "ollama,qwen2.5:14b")
- Context window settings:
  - `RAW_FILE_CONTEXT_LIMIT_CHARS`: Manual override for context size
  - `MODEL_CONTEXT_WINDOW_CHARS`: Base context window size
  - `RAW_FILE_CONTEXT_RATIO`: Ratio for automatic context limit (default 0.35)

### Multi-Round Conversation Support

WebUI maintains persistent `SessionState` across interactions:
- Shared report file (`session_report.docx`) accumulates all analysis rounds
- Conversation history feeds into comprehensive summary generation
- Users can revise summaries iteratively
- Context from previous rounds informs subsequent analysis

## API Endpoints

- `GET /healthz` - Health check
- `GET /config/runtime` - Runtime configuration and tunable parameters
- `POST /analyze/match` - Indicator disambiguation (returns candidates for user selection)
- `POST /analyze` - Execute analysis and generate report

### API Parameter Formats

**Important**: The `/analyze/match` endpoint uses form data parameters (FastAPI `Form()`), not JSON body.

```bash
# /analyze/match - Send as form data
curl -X POST "http://127.0.0.1:8001/analyze/match" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "excel_path=/path/to/data.xlsx" \
  -d "user_prompt=分析最近一年产量趋势" \
  -d "sheet_name=Sheet1" \
  -d "use_llm_structure=true"

# /analyze - Send as JSON
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "excel_path": "/path/to/data.xlsx",
    "user_prompt": "分析最近一年产量趋势",
    "sheet_name": "Sheet1",
    "use_llm_structure": true,
    "selected_indicator_names": ["产量", "销量"]
  }'
```

Python example:
```python
import requests

# /analyze/match - Use data= for form data
match_resp = requests.post(
    "http://127.0.0.1:8001/analyze/match",
    data={
        "excel_path": "/path/to/data.xlsx",
        "user_prompt": "分析最近一年产量趋势",
        "sheet_name": "Sheet1",
        "use_llm_structure": True,
    },
    timeout=60,
)

# /analyze - Use json= for JSON body
analyze_resp = requests.post(
    "http://127.0.0.1:8001/analyze",
    json={
        "excel_path": "/path/to/data.xlsx",
        "user_prompt": "分析最近一年产量趋势",
        "sheet_name": "Sheet1",
        "use_llm_structure": True,
        "selected_indicator_names": ["产量"],
    },
    timeout=600,
)
```

See `src/main.py` for request/response models and detailed usage.

## Important Notes

- The project is designed for **Chinese language content** (though supports English)
- Supports semiconductor industry data patterns (wafer/lot/die location columns)
- Chart placeholders in reports can be made editable via `src/docx_chart.py`
- Time window parsing handles both relative ("最近一年") and absolute dates
- Indicator matching uses fuzzy matching with disambiguation for similar column names
- All file uploads are parsed with configurable context limits to prevent LLM overflow
