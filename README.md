# Real-Time Incident Data ETL Pipeline

A headless data ingestion pipeline engineered to extract, clean, and summarize high-risk public safety incident data from dynamic legacy CAD (Computer-Aided Dispatch) web interfaces.

## System Architecture
1. **Extraction (ELT Layer):** Built with Python and Playwright to navigate dynamic, stateful ASP.NET multi-dropdown query menus without accessible direct API endpoints. Includes explicit waiting states and fault-tolerant selectors to manage server postbacks.
2. **Transformation & Processing (LLM Integration):** Dispatches raw first-responder dispatch strings to the Gemini 1.5 Flash API via the `google-genai` SDK for automated real-time NLP summarization.
3. **Storage:** Standardizes unstructured operational logs into structured, downstream-ready JSON format.

## Technology Stack
- **Language:** Python 3.14
- **Automation Engine:** Playwright (Sync API)
- **Generative AI Framework:** Google GenAI SDK (Gemini 1.5 Flash)
- **Environment Management:** Python-dotenv

## Administrative Note
This pipeline interacts with a legacy state system subject to frequent DOM modifications and layout adjustments. The codebase prioritizes defensive programmatic selection and modular orchestration to handle interface regressions gracefully.
