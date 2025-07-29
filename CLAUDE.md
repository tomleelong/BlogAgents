# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

```bash
# Create and activate virtual environment
python3 -m venv openai-agents-env
source openai-agents-env/bin/activate  # macOS/Linux
# openai-agents-env\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env to add OPENAI_API_KEY
```

## Running the Application

```bash
# Run the main blog orchestrator
python blog_orchestrator?.py

# The application will:
# 1. Analyze style from reference blog
# 2. Research the given topic
# 3. Write content matching the style
# 4. Edit and polish the final output
```

## Architecture Overview

This is a multi-agent blog content generation system using the OpenAI Agents SDK. The core architecture follows an orchestrated pipeline pattern:

### BlogAgentOrchestrator Class
Central coordinator that manages four specialized agents in a sequential workflow:

1. **Style Analyzer Agent**: Uses WebSearchTool to fetch and analyze content from reference blogs/RSS feeds, extracting writing patterns, tone, structure, and voice characteristics
2. **Research Agent**: Conducts web research on the given topic using WebSearchTool to gather facts, statistics, and current information
3. **Writer Agent**: Generates blog content that matches the analyzed style while incorporating the research data
4. **Editor Agent**: Reviews and polishes the content while preserving the matched style characteristics

### Agent Configuration
- All agents use `Runner.run_sync()` for synchronous execution
- Style Analyzer and Research agents have WebSearchTool for web content access
- Error handling implemented with try/catch blocks around agent operations
- Results passed between agents via dictionary data structure

### Key Methods
- `create_blog_post()`: Main workflow method that orchestrates the full pipeline
- `analyze_blog_style()`: Standalone method for extracting style from any blog/RSS feed
- `create_style_matched_post()`: Alias method for backward compatibility

### Data Flow
The system passes structured data between agents:
```
Topic + Reference Blog → Style Analysis → Research → Style-Matched Writing → Edited Content
```

Each step produces intermediate results stored in a results dictionary, allowing for debugging and inspection of the pipeline stages.

## Environment Variables Required

- `OPENAI_API_KEY`: Required for OpenAI Agents SDK
- `OPENAI_ORG_ID`: Optional organization ID for billing

## Dependencies

Core dependencies managed in requirements.txt:
- `openai-agents`: OpenAI Agents SDK for multi-agent orchestration
- `python-dotenv`: Environment variable management
- `requests`, `feedparser`, `beautifulsoup4`: Web content fetching (legacy, not actively used)