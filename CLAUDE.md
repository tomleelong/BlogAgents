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

### Web App (Streamlit)
```bash
# Run the web interface
streamlit run app.py

# Opens browser at http://localhost:8501
# Features:
# - User-friendly interface for API key input
# - Reference blog/RSS feed selection
# - Topic idea generator with keyword and product targeting
# - Google Sheets integration for content tracking
# - Keyword research with Google Trends and Google Ads API
# - Specific reference pages for style analysis
# - Real-time progress tracking
# - Tabbed output (Final Post, Style Guide, Research, SEO Analysis)
# - Download functionality (Markdown, HTML, Word, JSON)
# - Auto-Pilot mode for batch generation of multiple posts
```

### Command Line
```bash
# Run the main blog orchestrator directly
python blog_orchestrator.py

# The application will:
# 1. Analyze style from reference blog
# 2. Research the given topic
# 3. Write content matching the style
# 4. Edit and polish the final output
```

## Architecture Overview

This is a multi-agent blog content generation system using the OpenAI Agents SDK. The core architecture follows an orchestrated pipeline pattern:

### BlogAgentOrchestrator Class
Central coordinator that manages seven specialized agents in a sequential workflow:

1. **Style Analyzer Agent**: Uses WebSearchTool to fetch and analyze content from reference blogs/RSS feeds (or specific pages), extracting writing patterns, tone, structure, and voice characteristics
2. **Content Checker Agent**: Searches for existing content on the topic to ensure uniqueness and suggest differentiation angles
3. **Research Agent**: Conducts web research on the given topic using WebSearchTool to gather facts, statistics, and current information
4. **Writer Agent**: Generates blog content that matches the analyzed style while incorporating research data and product/page targets
5. **Internal Linker Agent**: Adds strategic internal links to relevant pages for SEO optimization
6. **Editor Agent**: Reviews and polishes the content while preserving style characteristics and internal links
7. **SEO Analyzer Agent**: Provides comprehensive SEO performance analysis and optimization recommendations

### Agent Configuration
- All agents use `Runner.run_sync()` for synchronous execution
- Style Analyzer and Research agents have WebSearchTool for web content access
- Error handling implemented with try/catch blocks around agent operations
- Results passed between agents via dictionary data structure

### Key Methods
- `create_blog_post()`: Main workflow method that orchestrates the full pipeline
- `create_blog_posts_batch()`: Batch generation for auto-pilot mode (analyzes style once, reuses for all posts)
- `analyze_blog_style()`: Standalone method for extracting style from any blog/RSS feed or specific pages
- `generate_topic_ideas()`: AI-powered topic generation with keyword research and duplication checking
- `extract_blog_topics()`: Extract existing topics from RSS feeds for duplication prevention
- `create_style_matched_post()`: Alias method for backward compatibility

### Data Flow
The system passes structured data between agents:
```
Topic + Reference Blog + Product Target → Style Analysis → Duplication Check → Research → Style-Matched Writing → Internal Linking → Editing → SEO Analysis
```

Each step produces intermediate results stored in a results dictionary, allowing for debugging and inspection of the pipeline stages.

### Additional Components

**SheetsManager Class**: Manages Google Sheets integration for data persistence
- Stores generated blog posts with metadata (topic, date, reference blog)
- Caches blog topics from RSS feeds to prevent duplicate content generation
- Tracks topic idea usage and keyword research data
- Provides content history and performance analytics

**KeywordResearcher Class**: Integrates keyword research capabilities
- Google Trends integration via pytrends for trending keywords and related queries
- Google Ads API integration for search volume and competition metrics
- Enriches topic ideas with SEO data (search volume, competition, trend status)
- Provides trend-based estimates when Google Ads API is not configured

## Environment Variables Required

### Required
- `OPENAI_API_KEY`: Required for OpenAI Agents SDK

### Optional
- `OPENAI_ORG_ID`: Optional organization ID for billing
- `GOOGLE_ADS_DEVELOPER_TOKEN`: For Google Ads API keyword data
- `GOOGLE_ADS_CLIENT_ID`: OAuth2 client ID for Google Ads
- `GOOGLE_ADS_CLIENT_SECRET`: OAuth2 client secret for Google Ads
- `GOOGLE_ADS_REFRESH_TOKEN`: OAuth2 refresh token for Google Ads
- `GOOGLE_ADS_CUSTOMER_ID`: Your Google Ads customer account ID
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google Sheets service account JSON file (for Sheets integration)

## Dependencies

Core dependencies managed in requirements.txt:
- `openai-agents==0.3.3`: OpenAI Agents SDK for multi-agent orchestration
- `streamlit==1.50.0`: Web interface framework
- `python-dotenv==1.1.1`: Environment variable management
- `gspread==6.2.1`: Google Sheets API client
- `google-auth==2.41.1`: Google authentication library
- `google-ads==28.0.0`: Google Ads API for keyword research
- `pytrends==4.9.2`: Google Trends unofficial API
- `feedparser==6.0.12`: RSS feed parsing for topic extraction
- `beautifulsoup4==4.14.2`: HTML parsing for web content
- `requests==2.32.5`: HTTP library for web requests

All versions are pinned for reproducibility.