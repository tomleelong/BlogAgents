# Blog Agents 🤖✍️

AI-powered blog content generation with intelligent style matching and multi-agent orchestration.

## Overview

Blog Agents is a sophisticated content generation system that uses multiple AI agents to create high-quality blog posts that match the style and voice of any reference blog or publication. Built with the OpenAI Agents SDK, it provides a comprehensive workflow from style analysis to final SEO optimization.

## Features

### 🎨 **Intelligent Style Matching**
- Analyzes reference blogs to extract writing patterns, tone, and voice
- Supports specific reference pages for focused style analysis
- Matches headline structure, paragraph flow, and vocabulary
- Preserves authentic voice while creating original content

### 💡 **AI-Powered Topic Generation**
- Generate topic ideas based on reference blog style
- Target specific keywords for SEO optimization
- Include product/page targets for content promotion
- Automatic duplication detection against existing content
- Google Trends integration for trending keywords
- Google Ads API integration for search volume and competition data

### 🔍 **Comprehensive Research & Analysis**
- Web search integration for up-to-date information
- Content duplication detection to ensure originality
- Multi-perspective research with source validation
- SEO-optimized internal linking
- Comprehensive SEO performance analysis

### 🤖 **Multi-Agent Architecture**
- **Style Analyzer**: Extracts writing patterns from reference content
- **Content Checker**: Identifies potential duplicates and suggests differentiation
- **Research Specialist**: Gathers relevant facts, statistics, and insights
- **Content Writer**: Creates engaging, well-structured blog posts
- **Internal Linker**: Adds strategic internal links for SEO
- **Content Editor**: Polishes grammar, flow, and readability
- **SEO Analyzer**: Provides actionable SEO recommendations

### 📊 **Data Persistence & Tracking**
- Google Sheets integration for content history
- Automatic topic caching to prevent duplicates
- Track used vs. unused topic ideas
- Performance analytics by reference blog

### 🚀 **Auto-Pilot Mode**
- Generate multiple blog posts automatically without intervention
- Queue up to 10 posts per auto-pilot run
- Auto-generates topics if none available
- Caches style guide for efficiency (analyzed once, reused for all posts)
- Progress tracking with completion status
- Error handling with continuation to next post on failure

### 🖥️ **Modern Interface**
- Clean Streamlit web interface
- Real-time progress tracking
- Tabbed output for easy content review (Final Post, Style Guide, Research, SEO Analysis)
- Multiple download formats (Markdown, HTML, Word Document, JSON)
- Content history viewer

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key with Agents SDK access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tomleelong/BlogAgents.git
   cd BlogAgents
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv openai-agents-env
   source openai-agents-env/bin/activate  # macOS/Linux
   # openai-agents-env\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env to add your OPENAI_API_KEY
   ```

### Usage

#### Web Interface (Recommended)
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`

#### Command Line
```bash
python blog_orchestrator.py
```

## Supported Models

All models support WebSearchTool for style analysis and research:

### GPT-5 Series
- **gpt-5.2**: Latest flagship model with best performance (recommended)
- **gpt-5**: Main reasoning model with advanced capabilities
- **gpt-5-mini**: Efficient version with balanced performance
- **gpt-5-nano**: Fastest version for quick generation

## Workflow

### Topic Generation (Optional)
1. **Keyword Research**: Fetches trending keywords via Google Trends
2. **Topic Ideas**: AI generates topic ideas with target keywords and angles
3. **Enrichment**: Adds search volume, competition, and trend data
4. **Duplication Check**: Compares against existing blog topics from RSS feed
5. **Selection**: Choose a topic and transfer to blog generator

### Blog Post Generation
1. **Style Analysis**: Analyzes reference blog for writing patterns (optionally from specific pages)
2. **Duplication Check**: Searches for existing content on the topic
3. **Research**: Gathers comprehensive information and insights
4. **Content Creation**: Writes blog post matching the analyzed style with product/page targeting
5. **Internal Linking**: Adds strategic internal links for SEO
6. **Editing**: Polishes content while preserving style and links
7. **SEO Analysis**: Provides optimization recommendations

## Configuration

### Environment Variables

#### Required
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

#### Optional
```bash
# OpenAI Organization
OPENAI_ORG_ID=your_org_id_here

# Google Sheets Integration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Google Ads API (for keyword research)
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_client_id
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_CUSTOMER_ID=your_customer_id
```

Note: Google Trends keyword research works without Google Ads API, but provides trend-based estimates instead of actual search volume data.

### Security Features
- Input validation and sanitization
- URL validation with SSRF protection
- Rate limiting and timeout controls
- Secure API key handling

## Output

The system generates:
- **Final Blog Post**: Polished, style-matched content with internal links
- **Style Guide**: Extracted writing patterns and guidelines
- **Research Data**: Comprehensive topic research and insights
- **Writer Draft**: Initial content before SEO optimization
- **Content With Links**: Blog post with strategic internal linking
- **SEO Analysis**: Comprehensive performance analysis and recommendations

### Download Formats
- Markdown (.md)
- HTML (.html)
- Microsoft Word (.docx)
- JSON (complete results data)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue on GitHub or contact [Bertram Labs](https://www.bertramlabs.com).

---

**Built with ❤️ by [Bertram Labs](https://www.bertramlabs.com)**

*Professional AI Solutions & Custom Development*