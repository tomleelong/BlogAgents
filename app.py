#!/usr/bin/env python3
import streamlit as st
import os
import re
import contextlib
import json
from urllib.parse import urlparse
from blog_orchestrator import BlogAgentOrchestrator
from sheets_manager import create_sheets_manager
from keyword_research import create_keyword_researcher

@contextlib.contextmanager
def temporary_env_var(key, value):
    """Securely set temporary environment variable with guaranteed cleanup."""
    old_value = os.environ.get(key)
    try:
        os.environ[key] = value
        yield
    finally:
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value

def validate_blog_url(url):
    """Validate and sanitize blog URL input to prevent SSRF attacks."""
    if not url or not url.strip():
        return None
    
    url = url.strip()
    
    # Add https:// if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Basic URL format validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise ValueError("Invalid URL format")
    
    parsed = urlparse(url)
    
    # Block internal/private IP ranges and localhost
    if parsed.hostname:
        hostname = parsed.hostname.lower()
        
        # Block localhost and loopback
        if hostname in ['localhost', '127.0.0.1', '0.0.0.0', '::1']:
            raise ValueError("Access to localhost is not allowed")
        
        # Block private IP ranges
        if (hostname.startswith('10.') or 
            hostname.startswith('172.16.') or hostname.startswith('172.17.') or 
            hostname.startswith('172.18.') or hostname.startswith('172.19.') or
            hostname.startswith('172.2') or hostname.startswith('172.3') or
            hostname.startswith('192.168.') or
            hostname == '169.254.169.254'):  # AWS metadata endpoint
            raise ValueError("Access to private network ranges is not allowed")
    
    return url

# Security constants
MAX_TOPIC_LENGTH = 500
MAX_REQUIREMENTS_LENGTH = 2000
MAX_API_KEY_LENGTH = 200

def main():
    """Streamlit web app entry point - renders the blog generation interface."""
    st.set_page_config(
        page_title="Blog Agents - AI Content Generator",
        page_icon="✍️",
        layout="wide"
    )

    # Initialize sheets_manager at function level
    sheets_manager = None
    
    # Header with logo (using file path for deployment)  
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        try:
            # Use relative path that works locally and when deployed
            logo_path = os.path.join(os.path.dirname(__file__), "assets", "bertram_labs_logo.svg")
            with open(logo_path, 'r') as f:
                logo_svg = f.read()
            # Add styling to the SVG
            styled_logo = logo_svg.replace('<svg', '<svg style="max-width: 200px; height: auto;"')
            st.markdown(f'<div style="text-align: center; padding: 1rem 0;">{styled_logo}</div>', unsafe_allow_html=True)
        except:
            # Fallback: show text logo if file not found
            st.markdown('<div style="text-align: center; padding: 1rem 0;"><h2 style="color: #2D5DA8; margin: 0; font-family: Inter, sans-serif;">BERTRAM LABS</h2></div>', unsafe_allow_html=True)
        st.markdown('<h1 style="text-align: center; margin-top: 1rem;">✍️ Blog Agents</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; font-size: 1.1rem; margin-bottom: 2rem;"><strong>AI-powered blog content generation with style matching</strong></p>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            max_chars=MAX_API_KEY_LENGTH,
            help="Your OpenAI API key for the Agents SDK"
        )

        # Google Sheets Configuration
        st.subheader("📊 Google Sheets Integration")
        use_sheets = st.checkbox(
            "Enable Google Sheets storage",
            value=False,
            help="Store style guides and content in Google Sheets for persistence"
        )

        if use_sheets:
            # Service Account JSON input
            service_account_json = st.text_area(
                "Service Account JSON",
                height=150,
                help="Paste your Google Service Account JSON credentials",
                placeholder='{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'
            )

            # Spreadsheet ID input
            spreadsheet_id = st.text_input(
                "Spreadsheet ID",
                help="Google Sheets ID from the URL",
                placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
            )

            # Test connection button
            if service_account_json and spreadsheet_id:
                if st.button("🔗 Test Sheets Connection"):
                    try:
                        sheets_manager = create_sheets_manager(service_account_json, spreadsheet_id)
                        if sheets_manager:
                            st.success("✅ Connected to Google Sheets!")
                            st.session_state.sheets_manager = sheets_manager
                        else:
                            st.error("❌ Failed to connect to Google Sheets")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")

                # Use existing connection if available
                if 'sheets_manager' in st.session_state:
                    sheets_manager = st.session_state.sheets_manager
                    # Verify connection is still valid
                    try:
                        if sheets_manager.test_connection():
                            st.info("📊 Using cached Sheets connection")
                        else:
                            st.warning("⚠️ Cached connection invalid, please reconnect")
                            del st.session_state.sheets_manager
                            sheets_manager = None
                    except Exception as e:
                        st.warning(f"⚠️ Connection issue: {str(e)}")
                        del st.session_state.sheets_manager
                        sheets_manager = None
            elif use_sheets:
                st.warning("⚠️ Please provide Service Account JSON and Spreadsheet ID")

        st.markdown("---")

        # Google Ads API for Keyword Research
        st.subheader("🔍 Keyword Research (Optional)")
        use_keyword_research = st.checkbox(
            "Enable Google Ads API",
            value=False,
            help="Get search volume and competition data for topics"
        )

        keyword_researcher = None
        if use_keyword_research:
            with st.expander("⚙️ Google Ads API Configuration"):
                st.markdown("**Required: 3 Simple Inputs**")

                # Developer Token
                developer_token = st.text_input(
                    "Developer Token",
                    type="password",
                    help="Get from: Google Ads → Tools → API Center"
                )

                # Service Account JSON
                service_account_json = st.text_area(
                    "Service Account JSON",
                    height=150,
                    help="Paste your service account JSON file contents",
                    placeholder='{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'
                )

                # Customer ID
                customer_id = st.text_input(
                    "Customer ID",
                    help="Your Google Ads customer ID (without hyphens, e.g., 1234567890)",
                    placeholder="1234567890"
                )

                if all([developer_token, service_account_json, customer_id]):
                    if st.button("🔗 Test Google Ads Connection"):
                        try:
                            config = {
                                'developer_token': developer_token,
                                'service_account_json': service_account_json,
                                'customer_id': customer_id
                            }
                            keyword_researcher = create_keyword_researcher(config)
                            if keyword_researcher and keyword_researcher.google_ads_client:
                                st.success("✅ Connected to Google Ads API!")
                                st.session_state.keyword_researcher = keyword_researcher
                            else:
                                st.error("❌ Failed to connect - check credentials")
                        except Exception as e:
                            st.error(f"❌ Connection failed: {str(e)}")

                    # Use cached connection
                    if 'keyword_researcher' in st.session_state:
                        keyword_researcher = st.session_state.keyword_researcher
                        st.info("🔍 Using cached Google Ads connection")
                else:
                    st.info("💡 [Setup Guide](https://developers.google.com/google-ads/api/docs/first-call/overview)")
        else:
            # Always create researcher for Google Trends (free)
            keyword_researcher = create_keyword_researcher()

        st.markdown("---")

        # Model selection
        model = st.selectbox(
            "OpenAI Model",
            options=[
                "gpt-5",             # GPT-5 main reasoning model
                "gpt-5-mini",        # GPT-5 efficient version
                "gpt-5-nano",        # GPT-5 smallest version
                "gpt-4o",            # GPT-4o flagship model
                "gpt-4o-mini",       # GPT-4o cost-effective
                "chatgpt-4o-latest", # Latest GPT-4o updates
                "gpt-4.1",           # GPT-4.1 flagship
                "gpt-4.1-mini",      # GPT-4.1 cost-effective
            ],
            index=0,
            help="All models support WebSearchTool for style analysis and research. gpt-5 is recommended for best performance."
        )
        
        # Reference blog input
        reference_blog = st.text_input(
            "Reference Blog/RSS Feed",
            value="",
            placeholder="e.g., YourBlog.com or https://yourblog.com/feed/",
            help="Blog URL or RSS feed to analyze for style matching"
        )

        # Specific reference pages input
        reference_pages = st.text_area(
            "📌 Specific Reference Pages (Optional)",
            placeholder="Enter specific blog post URLs to analyze (one per line):\nhttps://example.com/post-1\nhttps://example.com/post-2",
            height=100,
            help="Add specific high-performing posts you want to emulate. These will be analyzed in addition to the main blog."
        )

        if not api_key:
            st.warning("⚠️ Please enter your OpenAI API key to continue")
            st.stop()
            
        # Validate reference blog URL
        if reference_blog:
            try:
                reference_blog = validate_blog_url(reference_blog)
            except ValueError as e:
                st.error(f"🚫 Invalid blog URL: {e}")
                st.stop()
    
    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📝 Content Settings")

        # Topic Generator Section
        st.subheader("💡 Topic Idea Generator")

        # Optional target keywords input
        target_keywords = st.text_input(
            "🎯 Target Keywords (Optional)",
            placeholder="e.g., AI automation, machine learning, productivity",
            help="Enter keywords you want to rank for, separated by commas. These will be prioritized in topic generation."
        )

        # Optional product/page target
        product_target = st.text_area(
            "🛍️ Product/Page Target (Optional)",
            placeholder="e.g., Page URL: https://mystore.com/products/product\nDescription: Brief description of what the page offers and its key benefits...",
            height=100,
            help="Enter a product page, landing page, or service page URL and/or description. Topics will be generated to naturally promote this page."
        )

        if st.button("🎯 Generate Topic Ideas", help="AI-powered topic suggestions based on reference blog"):
            if not reference_blog.strip():
                st.error("⚠️ Please enter a reference blog URL first")
            elif not api_key:
                st.error("⚠️ Please enter your OpenAI API key first")
            else:
                with st.spinner("Generating topic ideas..."):
                    with temporary_env_var("OPENAI_API_KEY", api_key):
                        orchestrator = BlogAgentOrchestrator(model=model)

                        # Generate topics
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        def update_status(message, progress):
                            status_text.text(message)
                            progress_bar.progress(progress)

                        # Get or extract existing blog topics for duplication checking
                        existing_topics = []
                        if sheets_manager:
                            try:
                                status_text.text("📚 Checking for cached blog topics...")
                                cached = sheets_manager.get_cached_blog_topics(reference_blog)

                                if cached:
                                    # Check if cache is fresh (< 7 days)
                                    from datetime import datetime, timedelta
                                    try:
                                        last_updated = datetime.strptime(cached['last_updated'], '%Y-%m-%d %H:%M:%S')
                                        if datetime.now() - last_updated < timedelta(days=7):
                                            existing_topics = cached['topics']
                                            st.info(f"📚 Using cached topics ({len(existing_topics)} titles)")
                                        else:
                                            # Cache is stale, extract fresh topics
                                            status_text.text("📰 Extracting fresh blog topics...")
                                            existing_topics = orchestrator.extract_blog_topics(reference_blog)
                                            if existing_topics:
                                                sheets_manager.save_blog_topics(reference_blog, existing_topics)
                                    except:
                                        # Invalid timestamp, extract fresh
                                        status_text.text("📰 Extracting blog topics...")
                                        existing_topics = orchestrator.extract_blog_topics(reference_blog)
                                        if existing_topics:
                                            sheets_manager.save_blog_topics(reference_blog, existing_topics)
                                else:
                                    # No cache, extract for first time
                                    status_text.text("📰 Extracting blog topics...")
                                    existing_topics = orchestrator.extract_blog_topics(reference_blog)
                                    if existing_topics:
                                        sheets_manager.save_blog_topics(reference_blog, existing_topics)
                            except Exception as e:
                                st.warning(f"⚠️ Could not extract blog topics: {str(e)}")

                        # Combine user keywords with trending keywords
                        all_keywords = []

                        # Add user-provided target keywords (highest priority)
                        if target_keywords.strip():
                            user_keywords = [kw.strip() for kw in target_keywords.split(',') if kw.strip()]
                            all_keywords.extend(user_keywords)

                        # Fetch trending keywords to supplement user keywords
                        if keyword_researcher:
                            try:
                                status_text.text("🔍 Fetching trending keywords...")
                                # Extract a seed keyword from the reference blog domain
                                import re
                                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', reference_blog)
                                if domain_match:
                                    domain = domain_match.group(1).split('.')[0]
                                    trending_keywords = keyword_researcher.get_related_queries(domain)
                                    # Add trending keywords (avoid duplicates)
                                    for kw in trending_keywords:
                                        if kw.lower() not in [k.lower() for k in all_keywords]:
                                            all_keywords.append(kw)
                            except Exception as e:
                                st.warning(f"⚠️ Could not fetch trending keywords: {str(e)}")

                        # Generate topics informed by all keywords, product target, and existing topics
                        topics = orchestrator.generate_topic_ideas(
                            reference_blog,
                            preferences="",
                            status_callback=update_status,
                            trending_keywords=all_keywords if all_keywords else None,
                            product_target=product_target.strip() if product_target.strip() else None,
                            existing_topics=existing_topics if existing_topics else None
                        )

                        # Enrich with detailed keyword data
                        if keyword_researcher and topics:
                            status_text.text("🔍 Enriching with keyword research data...")
                            topics = keyword_researcher.enrich_topics_with_keyword_data(topics)

                        # Store in session state
                        st.session_state.generated_topics = topics
                        status_text.empty()
                        progress_bar.empty()

                        # Save to Google Sheets if enabled
                        if sheets_manager and topics:
                            try:
                                status_text.text("💾 Saving topics to Google Sheets...")
                                sheets_manager.save_topic_ideas(reference_blog, topics)
                                st.success("✅ Topics saved to Google Sheets!")
                            except Exception as e:
                                st.warning(f"⚠️ Could not save topics to Sheets: {str(e)}")


        # Display generated topics
        if 'generated_topics' in st.session_state and st.session_state.generated_topics:
            st.success(f"✅ Generated {len(st.session_state.generated_topics)} topic ideas!")

            for i, topic_idea in enumerate(st.session_state.generated_topics):
                with st.expander(f"💡 {topic_idea['title']}", expanded=False):
                    st.write(f"**Angle:** {topic_idea.get('angle', 'N/A')}")
                    st.write(f"**Keywords:** {', '.join(topic_idea.get('keywords', []))}")
                    st.write(f"**Content Type:** {topic_idea.get('content_type', 'N/A')}")
                    st.write(f"**Rationale:** {topic_idea.get('rationale', 'N/A')}")

                    # Show keyword data if available
                    if 'search_volume' in topic_idea:
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Search Volume", topic_idea.get('search_volume', 'N/A'))
                        with col_b:
                            st.metric("Competition", topic_idea.get('competition', 'N/A'))
                        with col_c:
                            st.metric("Trend", topic_idea.get('trend_status', 'N/A'))

                    if st.button(f"✏️ Use This Topic", key=f"use_topic_{i}"):
                        # Set the topic_input widget directly
                        st.session_state.topic_input = topic_idea['title']

                        # Pre-fill requirements with topic context
                        requirements_text = f"""Angle: {topic_idea.get('angle', 'N/A')}
Target Keywords: {', '.join(topic_idea.get('keywords', []))}
Content Type: {topic_idea.get('content_type', 'N/A')}
Rationale: {topic_idea.get('rationale', 'N/A')}"""
                        st.session_state.requirements_input = requirements_text

                        # Mark topic as used in Google Sheets if enabled
                        if sheets_manager and 'ID' in topic_idea:
                            try:
                                sheets_manager.mark_topic_used(topic_idea['ID'])
                                st.success(f"✅ Topic marked as used in Google Sheets!")
                            except Exception as e:
                                st.warning(f"⚠️ Could not mark topic as used: {str(e)}")

                        st.rerun()

        st.markdown("---")

        # Topic input
        topic = st.text_area(
            "Blog Topic",
            height=100,
            max_chars=MAX_TOPIC_LENGTH,
            placeholder=f"Enter your blog topic (max {MAX_TOPIC_LENGTH} characters)",
            help="The main subject for your blog post",
            key="topic_input"
        )
        
        # Requirements input
        requirements = st.text_area(
            "Additional Requirements",
            height=150,
            max_chars=MAX_REQUIREMENTS_LENGTH,
            placeholder=f"""- Target audience: [your audience]
- Include practical examples
- Keep under [word count] words
- Add call-to-action
- Focus on [specific aspect]

(max {MAX_REQUIREMENTS_LENGTH} characters)""",
            help="Specific requirements for your blog post",
            key="requirements_input"
        )

        # Product/Page target for blog generation
        blog_product_target = st.text_area(
            "🛍️ Product/Page Target (Optional)",
            placeholder="e.g., Page URL: https://mystore.com/products/product\nDescription: Brief description of what the page offers and its key benefits...",
            height=100,
            help="Enter a product page, landing page, or service page URL and/or description. The blog post will naturally promote this page.",
            key="blog_product_target"
        )

        # Generate button
        generate_button = st.button(
            "🚀 Generate Blog Post",
            type="primary",
            disabled=not (api_key and topic.strip() and reference_blog.strip())
        )
    
    with col2:
        st.header("📊 Output")
        
        if generate_button:
            # Server-side validation
            if not topic.strip():
                st.error("❌ Please enter a topic for your blog post")
                return

            if not reference_blog.strip():
                st.error("❌ Please enter a reference blog URL for style matching")
                return

            if len(topic.strip()) > MAX_TOPIC_LENGTH:
                st.error(f"❌ Topic too long. Maximum {MAX_TOPIC_LENGTH} characters allowed.")
                return

            if len(requirements) > MAX_REQUIREMENTS_LENGTH:
                st.error(f"❌ Requirements too long. Maximum {MAX_REQUIREMENTS_LENGTH} characters allowed.")
                return

            if len(api_key) > MAX_API_KEY_LENGTH:
                st.error("❌ Invalid API key format.")
                return

            try:
                # Use secure context manager for API key
                with temporary_env_var("OPENAI_API_KEY", api_key):
                    # Initialize orchestrator with selected model
                    orchestrator = BlogAgentOrchestrator(model=model)

                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Callback function to update status
                    def update_status(message, progress):
                        status_text.text(message)
                        progress_bar.progress(progress)

                    # Parse specific reference pages
                    specific_pages_list = None
                    if reference_pages.strip():
                        # Split by newlines and filter empty lines
                        specific_pages_list = [page.strip() for page in reference_pages.split('\n') if page.strip()]

                    # Check for cached style guide if sheets enabled
                    cached_style = None
                    if sheets_manager:
                        try:
                            update_status("🔍 Checking for cached style guide...", 5)
                            cached_style = sheets_manager.get_cached_style_guide(reference_blog)
                            if cached_style:
                                st.info(f"📋 Using cached style guide for {reference_blog} (last updated: {cached_style['last_updated']})")
                        except Exception as e:
                            st.warning(f"⚠️ Could not access cached style guide: {str(e)}")
                            cached_style = None

                    # Generate blog post with real-time updates
                    results = orchestrator.create_blog_post(
                        topic=topic,
                        reference_blog=reference_blog,
                        requirements=requirements,
                        status_callback=update_status,
                        cached_style_guide=cached_style['style_guide'] if cached_style else None,
                        product_target=blog_product_target.strip() if blog_product_target.strip() else None,
                        specific_pages=specific_pages_list
                    )

                    # Save results to sheets if enabled
                    if sheets_manager and "error" not in results:
                        try:
                            update_status("💾 Saving to Google Sheets...", 95)

                            # Save style guide if it was freshly generated
                            if not cached_style and "style_guide" in results:
                                sheets_manager.save_style_guide(
                                    reference_blog,
                                    results["style_guide"]
                                )

                            # Save generated content
                            sheets_manager.save_generated_content(
                                topic,
                                reference_blog,
                                results
                            )

                            # Update blog source stats
                            sheets_manager.update_blog_source_stats(reference_blog, success=True)

                            st.success("✅ Content saved to Google Sheets!")
                        except Exception as e:
                            st.warning(f"⚠️ Could not save to Google Sheets: {str(e)}")
                            # Continue without failing the entire operation
                
                # Display results
                if "error" in results:
                    st.error(f"❌ Error: {results['error']}")
                else:
                    # Tabs for different outputs
                    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                        "📄 Final Post",
                        "🎨 Style Guide",
                        "🔍 Research & Analysis", 
                        "✍️ Writer Draft",
                        "📊 Initial SEO Analysis",
                        "🔗 With Links",
                        "📊 Final SEO Analysis"
                    ])
                    
                    with tab1:
                        st.markdown("### Final Blog Post")
                        
                        # Display formatted content
                        with st.container():
                            st.markdown("#### Preview")
                            # Show formatted markdown preview
                            st.markdown(results["final"])
                        
                        # Raw content for editing
                        with st.expander("📝 Edit Raw Content", expanded=False):
                            edited_content = st.text_area(
                                "Edit the blog post content:",
                                value=results["final"],
                                height=400,
                                help="You can edit the content here before downloading",
                                key="final_edit_area"
                            )
                        
                        # Default to original content for downloads
                        final_content = edited_content if st.session_state.get("final_edit_area") else results["final"]
                        
                        # Download options
                        st.markdown("#### Download Options")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.download_button(
                                label="📄 Download as Text",
                                data=final_content,
                                file_name=f"blog_post_{topic[:30].replace(' ', '_').lower()}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                        
                        with col2:
                            st.download_button(
                                label="📝 Download as Markdown", 
                                data=final_content,
                                file_name=f"blog_post_{topic[:30].replace(' ', '_').lower()}.md",
                                mime="text/markdown",
                                use_container_width=True
                            )
                        
                        with col3:
                            # Convert markdown to HTML for download
                            try:
                                import markdown
                                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{topic}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 20px; font-style: italic; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
{markdown.markdown(final_content)}
</body>
</html>"""
                                st.download_button(
                                    label="🌐 Download as HTML",
                                    data=html_content,
                                    file_name=f"blog_post_{topic[:30].replace(' ', '_').lower()}.html",
                                    mime="text/html",
                                    use_container_width=True
                                )
                            except ImportError:
                                st.info("HTML export requires markdown package")
                    
                    with tab2:
                        st.markdown("### Extracted Style Guide")
                        st.markdown(f"*Style analysis from: {reference_blog}*")
                        st.text_area(
                            "Style Guide",
                            value=results["style_guide"],
                            height=400,
                            disabled=False,
                            help="You can copy text from this field"
                        )
                    
                    with tab3:
                        st.markdown("### Research & Analysis")
                        st.markdown("*Comprehensive research on the topic*")
                        if "research" in results:
                            st.text_area(
                                "Research Results",
                                value=results["research"],
                                height=400,
                                disabled=False,
                                key="research_area",
                                help="Detailed research findings and insights"
                            )
                        else:
                            st.info("Research results not available")
                    
                    with tab4:
                        st.markdown("### Writer Draft")
                        st.markdown("*Initial blog post draft before SEO optimization*")
                        if "draft" in results:
                            # Display formatted content
                            with st.container():
                                st.markdown("#### Preview")
                                st.markdown(results["draft"])
                            
                            # Raw content for editing
                            with st.expander("📝 Edit Draft Content", expanded=False):
                                st.text_area(
                                    "Edit the draft content:",
                                    value=results["draft"],
                                    height=400,
                                    key="draft_edit_area",
                                    help="You can edit the draft content here before downloading"
                                )
                            
                            # Download options for draft
                            st.markdown("#### Download Draft")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.download_button(
                                    label="📄 Download Draft as Text",
                                    data=results["draft"],
                                    file_name=f"draft_{topic[:30].replace(' ', '_').lower()}.txt",
                                    mime="text/plain",
                                    use_container_width=True
                                )
                            
                            with col2:
                                st.download_button(
                                    label="📝 Download Draft as Markdown",
                                    data=results["draft"],
                                    file_name=f"draft_{topic[:30].replace(' ', '_').lower()}.md",
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                        else:
                            st.info("Writer draft not available")
                    
                    with tab5:
                        st.markdown("### Initial SEO Analysis")
                        st.markdown("*SEO optimization recommendations for the draft*")
                        if "initial_seo_analysis" in results:
                            st.text_area(
                                "SEO Optimization Recommendations",
                                value=results["initial_seo_analysis"],
                                height=400,
                                disabled=False,
                                key="initial_seo_area",
                                help="SEO recommendations applied during editing"
                            )
                        else:
                            st.info("Initial SEO analysis not available")
                    
                    with tab6:
                        st.markdown("### Content With Internal Links")
                        st.markdown("*Blog post with strategic SEO-optimized internal links*")
                        if "with_links" in results:
                            # Display formatted content with links
                            with st.container():
                                st.markdown("#### Preview with Links")
                                st.markdown(results["with_links"])
                            
                            # Raw content
                            with st.expander("📝 View/Edit Raw Content with Links", expanded=False):
                                st.text_area(
                                    "Content with Internal Links:",
                                    value=results["with_links"],
                                    height=400,
                                    key="links_edit_area",
                                    help="Content with SEO-optimized internal links added"
                                )
                            
                            # Download options
                            st.markdown("#### Download With Links")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.download_button(
                                    label="📄 Download as Text",
                                    data=results["with_links"],
                                    file_name=f"with_links_{topic[:30].replace(' ', '_').lower()}.txt",
                                    mime="text/plain",
                                    use_container_width=True
                                )
                            
                            with col2:
                                st.download_button(
                                    label="📝 Download as Markdown",
                                    data=results["with_links"],
                                    file_name=f"with_links_{topic[:30].replace(' ', '_').lower()}.md",
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                        else:
                            st.info("Internal linking results not available")
                    
                    with tab7:
                        st.markdown("### Final SEO Performance Analysis")
                        st.markdown("*Comprehensive SEO assessment of the completed blog post*")
                        
                        if "seo_analysis" in results:
                            # Parse SEO score if available
                            seo_text = results["seo_analysis"]
                            if "SEO SCORE:" in seo_text:
                                try:
                                    score_line = [line for line in seo_text.split('\n') if 'SEO SCORE:' in line][0]
                                    score = score_line.split(':')[1].strip().split('/')[0]
                                    score_num = int(score)
                                    
                                    # Color-coded score display
                                    if score_num >= 80:
                                        st.success(f"🎯 **SEO Score: {score}/100** - Excellent!")
                                    elif score_num >= 60:
                                        st.warning(f"⚠️ **SEO Score: {score}/100** - Good with room for improvement")
                                    else:
                                        st.error(f"🔴 **SEO Score: {score}/100** - Needs optimization")
                                except:
                                    pass
                            
                            st.text_area(
                                "SEO Analysis & Recommendations",
                                value=results["seo_analysis"],
                                height=450,
                                disabled=False,
                                key="seo_area",
                                help="You can copy text from this field"
                            )
                        else:
                            st.info("SEO analysis not available")
                        
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()

                st.error(f"❌ An error occurred: {str(e)}")
                st.info("💡 Make sure your OpenAI API key is valid and has access to the Agents API")

                # Show detailed error for debugging
                st.subheader("🔍 Debug Information")
                st.code(error_traceback, language="python")

    # Show content history if sheets enabled
    if sheets_manager and st.checkbox("📋 Show Content History", value=False):
        st.header("📋 Content History")

        try:
            history = sheets_manager.get_content_history(limit=10)
            if history:
                for item in history:
                    with st.expander(f"📝 {item['Topic']} ({item['Date_Created']})"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Source Blog", item['Source_Blog'])
                        with col2:
                            st.metric("Word Count", item['Word_Count'])
                        with col3:
                            st.metric("SEO Score", item['SEO_Score'] if item['SEO_Score'] else 'N/A')

                        if st.button(f"📄 View Content", key=f"view_{item['ID']}"):
                            st.markdown("### Generated Content")
                            st.markdown(item['Final_Content'])
            else:
                st.info("No content history found")

            # Blog source statistics
            st.subheader("📊 Blog Source Performance")
            source_stats = sheets_manager.get_blog_source_stats()
            if source_stats:
                for source in source_stats[:5]:  # Show top 5
                    st.write(f"**{source['Domain']}** - Success: {source['Success_Count']}, Last used: {source['Last_Analyzed']}")
            else:
                st.info("No blog source statistics available")
        except Exception as e:
            st.error(f"❌ Could not load content history: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; padding: 2rem 0;'>
        <p>Powered by OpenAI Agents SDK | Built by <a href="https://www.bertramlabs.com" target="_blank" style="color: #2D5DA8; text-decoration: none; font-weight: bold;">Bertram Labs</a></p>
        <p style='font-size: 0.9rem; margin-top: 0.5rem;'>Professional AI Solutions & Custom Development</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()