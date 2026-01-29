#!/usr/bin/env python3
"""
Safety Products Global - Multi-Brand Blog Content Generator

A specialized blog generation system for Safety Products Global's brand portfolio:
- Slice (sliceproducts.com)
- Klever Innovations (kleverinnovations.net)
- Pacific Handy Cutter (phcsafety.com)
"""
import streamlit as st
import os
import re
import contextlib
import json
from urllib.parse import urlparse
from dotenv import load_dotenv
from blog_orchestrator import BlogAgentOrchestrator
from sheets_manager import create_sheets_manager
from keyword_research import create_keyword_researcher
from brand_config import get_brand_config, get_all_brands, get_effective_style_source, BrandConfig

# Load environment variables (override=True ensures .env takes precedence over system env vars)
load_dotenv(override=True)


def load_google_sheets_credentials():
    """
    Load Google Sheets credentials from environment.

    Supports two methods:
    1. GOOGLE_APPLICATION_CREDENTIALS - path to service account JSON file
    2. GOOGLE_SERVICE_ACCOUNT_JSON - raw JSON string (for deployments)

    Returns:
        tuple: (service_account_json, spreadsheet_id) or (None, None) if not configured
    """
    spreadsheet_id = os.environ.get("GOOGLE_SPREADSHEET_ID", "")

    # Method 1: File path
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds_path:
        # Handle relative paths - make them relative to project directory
        if not os.path.isabs(creds_path):
            project_dir = os.path.dirname(os.path.abspath(__file__))
            creds_path = os.path.join(project_dir, creds_path)

        if os.path.isfile(creds_path):
            try:
                with open(creds_path, 'r') as f:
                    service_account_json = f.read()
                if spreadsheet_id:
                    return service_account_json, spreadsheet_id
            except Exception as e:
                print(f"Error reading credentials file: {e}")

    # Method 2: Raw JSON string
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if service_account_json and spreadsheet_id:
        return service_account_json, spreadsheet_id

    return None, None

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
    import ipaddress
    import socket

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

    if not parsed.hostname:
        raise ValueError("Invalid hostname")

    hostname = parsed.hostname.lower()

    # Block localhost and loopback names
    localhost_names = ['localhost', 'localhost.localdomain']
    if hostname in localhost_names:
        raise ValueError("Access to localhost is not allowed")

    # Block cloud metadata endpoints by hostname
    metadata_hostnames = [
        'metadata.google.internal',
        'metadata.google.com',
        'metadata',
        'instance-data'
    ]
    if hostname in metadata_hostnames:
        raise ValueError("Access to metadata endpoints is not allowed")

    # Resolve hostname to IP and validate
    try:
        addr_info = socket.getaddrinfo(hostname, None)

        for addr in addr_info:
            ip_str = addr[4][0]

            try:
                ip = ipaddress.ip_address(ip_str)

                # Block loopback addresses (127.0.0.0/8, ::1)
                if ip.is_loopback:
                    raise ValueError("Access to loopback addresses is not allowed")

                # Block private networks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7)
                if ip.is_private:
                    raise ValueError("Access to private network ranges is not allowed")

                # Block link-local (169.254.0.0/16, fe80::/10)
                if ip.is_link_local:
                    raise ValueError("Access to link-local addresses is not allowed")

                # Block multicast
                if ip.is_multicast:
                    raise ValueError("Access to multicast addresses is not allowed")

                # Additional IPv4 checks
                if isinstance(ip, ipaddress.IPv4Address):
                    # Block 0.0.0.0/8
                    if ip_str.startswith('0.'):
                        raise ValueError("Invalid IP address")

                    # Explicit cloud metadata check
                    if ip_str == '169.254.169.254':
                        raise ValueError("Access to cloud metadata endpoints is not allowed")

            except ValueError as e:
                # Re-raise validation errors
                raise ValueError(f"Invalid IP address: {e}")

    except socket.gaierror:
        raise ValueError("Cannot resolve hostname")
    except Exception as e:
        raise ValueError(f"DNS resolution error: {e}")

    return url

# Security constants
MAX_TOPIC_LENGTH = 500
MAX_REQUIREMENTS_LENGTH = 2000
MAX_API_KEY_LENGTH = 200
MAX_AUTOPILOT_POSTS = 10


def get_available_topics_for_autopilot(session_state, sheets_manager=None):
    """
    Gather available topics for auto-pilot from session state and Google Sheets.

    Args:
        session_state: Streamlit session state
        sheets_manager: Optional SheetsManager instance

    Returns:
        List of topic dicts available for generation
    """
    available_topics = []

    # First, check session-generated topics (unused ones)
    if 'generated_topics' in session_state and session_state.generated_topics:
        for topic in session_state.generated_topics:
            # Check if topic has been marked as used
            if not topic.get('used', False):
                available_topics.append(topic)

    # If sheets enabled, also check for cached topics
    if sheets_manager and len(available_topics) < MAX_AUTOPILOT_POSTS:
        try:
            # Get unused topics from Google Sheets
            cached_topics = sheets_manager.get_unused_topic_ideas(
                limit=MAX_AUTOPILOT_POSTS - len(available_topics)
            )
            if cached_topics:
                # Convert to standard format and avoid duplicates
                existing_titles = {t['title'].lower() for t in available_topics}
                for cached in cached_topics:
                    if cached.get('title', '').lower() not in existing_titles:
                        available_topics.append(cached)
        except Exception as e:
            print(f"Could not fetch cached topics from Sheets: {e}")

    return available_topics[:MAX_AUTOPILOT_POSTS]


def build_requirements_from_topic(topic_dict):
    """
    Convert topic metadata to requirements string for blog generation.

    Args:
        topic_dict: Topic dictionary with angle, keywords, content_type, rationale

    Returns:
        Formatted requirements string
    """
    requirements_parts = []

    if topic_dict.get('angle'):
        requirements_parts.append(f"Angle: {topic_dict['angle']}")

    if topic_dict.get('keywords'):
        keywords = topic_dict['keywords']
        if isinstance(keywords, list):
            keywords = ', '.join(keywords)
        requirements_parts.append(f"Target Keywords: {keywords}")

    if topic_dict.get('content_type'):
        requirements_parts.append(f"Content Type: {topic_dict['content_type']}")

    if topic_dict.get('rationale'):
        requirements_parts.append(f"Rationale: {topic_dict['rationale']}")

    return '\n'.join(requirements_parts)


def initialize_autopilot_state(session_state):
    """Initialize all auto-pilot related session state keys."""
    defaults = {
        'autopilot_active': False,
        'autopilot_stop_requested': False,
        'autopilot_total_posts': 0,
        'autopilot_completed_posts': 0,
        'autopilot_current_topic': None,
        'autopilot_topics_queue': [],
        'autopilot_results': [],
        'autopilot_errors': [],
        'autopilot_cached_style': None,
    }
    for key, default_value in defaults.items():
        if key not in session_state:
            session_state[key] = default_value


def reset_autopilot_state(session_state):
    """Reset auto-pilot state for a new run."""
    session_state.autopilot_active = False
    session_state.autopilot_stop_requested = False
    session_state.autopilot_total_posts = 0
    session_state.autopilot_completed_posts = 0
    session_state.autopilot_current_topic = None
    session_state.autopilot_topics_queue = []
    session_state.autopilot_results = []
    session_state.autopilot_errors = []
    session_state.autopilot_cached_style = None


def main():
    """Streamlit web app entry point - renders the blog generation interface."""
    st.set_page_config(
        page_title="Safety Products Global - Blog Generator",
        page_icon="✍️",
        layout="wide"
    )

    # Initialize auto-pilot session state
    initialize_autopilot_state(st.session_state)

    # Initialize sheets_manager at function level
    sheets_manager = None

    # Get API key from environment (simplified for dedicated system)
    api_key = os.environ.get("OPENAI_API_KEY", "")

    # Header with brand-aware styling
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown('<h1 style="text-align: center; margin-top: 1rem;">✍️ Safety Products Global</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; font-size: 1.1rem; margin-bottom: 2rem;"><strong>Multi-Brand Blog Content Generator</strong></p>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        # Brand Selection (TOP PRIORITY)
        st.header("🏢 Brand Selection")
        brands = get_all_brands()
        selected_brand_name = st.selectbox(
            "Select Brand",
            options=[b.name for b in brands],
            format_func=lambda x: get_brand_config(x).display_name,
            help="Choose which brand you're creating content for"
        )
        brand_config = get_brand_config(selected_brand_name)

        # Store brand in session state
        st.session_state.current_brand = selected_brand_name

        # Display brand info
        st.markdown(f"**Domain:** {brand_config.primary_domain}")
        if brand_config.blog_url:
            st.markdown(f"**Blog:** [View Blog]({brand_config.blog_url})")
        else:
            st.info(f"No blog yet - using {brand_config.style_source_url} for style")

        # Apply brand-specific color styling
        st.markdown(f"""
        <style>
            .stApp {{ --primary-color: {brand_config.primary_color}; }}
            div[data-testid="stSidebarHeader"] {{ border-bottom: 3px solid {brand_config.primary_color}; }}
        </style>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.header("⚙️ Configuration")

        # API Key - check environment first, allow override
        if api_key:
            st.success("✅ API Key loaded from environment")
        else:
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                max_chars=MAX_API_KEY_LENGTH,
                help="Your OpenAI API key (or set OPENAI_API_KEY in .env)"
            )

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
            help="gpt-5 is recommended for best performance."
        )

        st.markdown("---")

        # Google Sheets Configuration
        st.subheader("📊 Google Sheets Integration")

        # Check for environment credentials
        env_creds, env_spreadsheet_id = load_google_sheets_credentials()
        has_env_config = bool(env_creds and env_spreadsheet_id)

        use_sheets = st.checkbox(
            "Enable Google Sheets storage",
            value=has_env_config,
            help="Store style guides and content in Google Sheets for persistence"
        )

        if use_sheets:
            if has_env_config:
                # Use credentials from environment
                st.success("✅ Sheets credentials loaded from environment")
                service_account_json = env_creds
                spreadsheet_id = env_spreadsheet_id

                # Auto-connect if not already connected
                if 'sheets_manager' not in st.session_state:
                    try:
                        sheets_manager = create_sheets_manager(service_account_json, spreadsheet_id)
                        if sheets_manager:
                            st.session_state.sheets_manager = sheets_manager
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")

                if 'sheets_manager' in st.session_state:
                    sheets_manager = st.session_state.sheets_manager
                    st.info("📊 Connected to Google Sheets")
            else:
                # Manual input fallback
                service_account_json = st.text_area(
                    "Service Account JSON",
                    height=150,
                    help="Paste your Google Service Account JSON credentials",
                    placeholder='{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'
                )

                spreadsheet_id = st.text_input(
                    "Spreadsheet ID",
                    help="Google Sheets ID from the URL",
                    placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
                )

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

                    if 'sheets_manager' in st.session_state:
                        sheets_manager = st.session_state.sheets_manager
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
                else:
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

        # Reference blog - auto-populated from brand config
        st.subheader("📝 Style Source")
        reference_blog = get_effective_style_source(brand_config)
        st.info(f"Style source: {reference_blog}")

        # Optional: allow override for advanced users
        with st.expander("Advanced: Custom Reference"):
            custom_ref = st.text_input(
                "Override reference blog (optional)",
                placeholder="Leave empty to use brand default"
            )
            if custom_ref:
                try:
                    reference_blog = validate_blog_url(custom_ref)
                    st.success(f"Using custom reference: {reference_blog}")
                except ValueError as e:
                    st.error(f"Invalid URL: {e}")

        # Specific reference pages input
        reference_pages = st.text_area(
            "📌 Specific Reference Pages (Optional)",
            placeholder="Enter specific blog post URLs to analyze (one per line):",
            height=80,
            help="Add specific high-performing posts you want to emulate."
        )

        if not api_key:
            st.warning("⚠️ Please set OPENAI_API_KEY in your .env file")
            st.stop()

        # Validate reference blog URL
        if reference_blog:
            try:
                reference_blog = validate_blog_url(reference_blog)
            except ValueError as e:
                st.error(f"🚫 Invalid blog URL: {e}")
                st.stop()

    # ============================================================
    # AUTO-PILOT EXECUTION LOOP
    # ============================================================
    if st.session_state.autopilot_active:
        # Check for stop request
        if st.session_state.autopilot_stop_requested:
            st.session_state.autopilot_active = False
            st.session_state.autopilot_stop_requested = False
            st.success("⏹️ Auto-pilot stopped by user request")
        # Check if we need to auto-generate topics first
        elif st.session_state.get('autopilot_needs_topics', False):
            with st.spinner("💡 Auto-generating topics for auto-pilot..."):
                with temporary_env_var("OPENAI_API_KEY", api_key):
                    orchestrator = BlogAgentOrchestrator(model=model, brand_config=brand_config)

                    # Generate topics using the topic generator
                    topics = orchestrator.generate_topic_ideas(
                        reference_blog,
                        preferences="",
                        status_callback=None,
                        trending_keywords=None,
                        product_target=None,
                        existing_topics=None
                    )

                    if topics:
                        # Queue the generated topics
                        st.session_state.autopilot_topics_queue = topics[:st.session_state.autopilot_total_posts]
                        st.session_state.generated_topics = topics  # Also store for display
                        st.session_state.autopilot_needs_topics = False
                        st.success(f"✅ Generated {len(topics)} topics for auto-pilot")
                        st.rerun()
                    else:
                        st.error("❌ Failed to generate topics. Please generate topics manually first.")
                        st.session_state.autopilot_active = False
                        st.session_state.autopilot_needs_topics = False

        # Check if all posts are completed
        elif st.session_state.autopilot_completed_posts >= st.session_state.autopilot_total_posts:
            st.session_state.autopilot_active = False
            st.balloons()
            st.success(f"🎉 Auto-pilot completed! Generated {st.session_state.autopilot_completed_posts} posts.")

        # Check if there are topics in the queue to process
        elif st.session_state.autopilot_topics_queue:
            # Get next topic from queue
            current_topic_dict = st.session_state.autopilot_topics_queue.pop(0)
            topic_title = current_topic_dict.get('title', 'Untitled Topic')
            st.session_state.autopilot_current_topic = topic_title

            # Build requirements from topic metadata
            topic_requirements = build_requirements_from_topic(current_topic_dict)

            # Get product target if available
            autopilot_product_target = st.session_state.get('topic_gen_product_target', '')

            # Create progress display
            post_num = st.session_state.autopilot_completed_posts + 1
            total_posts = st.session_state.autopilot_total_posts

            progress_container = st.container()
            with progress_container:
                st.markdown(f"### 🔄 Auto-Pilot: Post {post_num}/{total_posts}")
                st.markdown(f"**Topic:** {topic_title}")
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_autopilot_status(message, progress):
                    status_text.text(f"🔄 Post {post_num}/{total_posts}: {message}")
                    progress_bar.progress(progress)

            try:
                with temporary_env_var("OPENAI_API_KEY", api_key):
                    orchestrator = BlogAgentOrchestrator(model=model, brand_config=brand_config)

                    # Use cached style guide if available, otherwise analyze once and cache
                    cached_style = st.session_state.autopilot_cached_style

                    # Check for style guide from sheets if not cached yet
                    if not cached_style and sheets_manager:
                        try:
                            sheets_cached = sheets_manager.get_cached_style_guide(reference_blog)
                            if sheets_cached:
                                cached_style = sheets_cached['style_guide']
                                st.session_state.autopilot_cached_style = cached_style
                        except Exception:
                            pass

                    # Generate the blog post
                    results = orchestrator.create_blog_post(
                        topic=topic_title,
                        reference_blog=reference_blog,
                        requirements=topic_requirements,
                        status_callback=update_autopilot_status,
                        cached_style_guide=cached_style,
                        product_target=autopilot_product_target if autopilot_product_target else None,
                        specific_pages=None
                    )

                    # Cache the style guide for subsequent posts
                    if not st.session_state.autopilot_cached_style and 'style_guide' in results:
                        st.session_state.autopilot_cached_style = results['style_guide']

                    # Process results
                    if 'error' in results:
                        # Record error
                        st.session_state.autopilot_errors.append({
                            'topic': topic_title,
                            'error': results['error']
                        })
                        st.session_state.autopilot_results.append({
                            'topic': topic_title,
                            'success': False,
                            'error': results['error']
                        })
                    else:
                        # Record success
                        st.session_state.autopilot_results.append({
                            'topic': topic_title,
                            'success': True,
                            'results': results
                        })

                        # Save to Google Sheets if enabled
                        if sheets_manager:
                            try:
                                # Save style guide if this is the first post
                                if post_num == 1 and 'style_guide' in results:
                                    sheets_manager.save_style_guide(reference_blog, results['style_guide'])

                                # Save generated content
                                sheets_manager.save_generated_content(
                                    topic_title,
                                    reference_blog,
                                    results
                                )

                                # Update blog source stats
                                sheets_manager.update_blog_source_stats(reference_blog, success=True)

                                # Mark topic as used
                                if 'ID' in current_topic_dict:
                                    sheets_manager.mark_topic_used(current_topic_dict['ID'])
                            except Exception as e:
                                print(f"Could not save to Sheets: {e}")

                        # Mark topic as used in session state
                        current_topic_dict['used'] = True

                    # Update completion count
                    st.session_state.autopilot_completed_posts += 1
                    st.session_state.autopilot_current_topic = None

            except Exception as e:
                # Record error
                st.session_state.autopilot_errors.append({
                    'topic': topic_title,
                    'error': str(e)
                })
                st.session_state.autopilot_results.append({
                    'topic': topic_title,
                    'success': False,
                    'error': str(e)
                })
                st.session_state.autopilot_completed_posts += 1
                st.session_state.autopilot_current_topic = None

            # Trigger next iteration
            st.rerun()

        else:
            # No more topics in queue
            st.session_state.autopilot_active = False
            st.warning("⚠️ Auto-pilot stopped: No more topics in queue")

    # ============================================================
    # MAIN CONTENT AREA
    # ============================================================

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        # Brand Dashboard (if sheets enabled)
        if sheets_manager:
            st.subheader(f"📊 {brand_config.display_name} Dashboard")
            try:
                stats = sheets_manager.get_brand_stats()
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("Total Posts", stats['total_posts'])
                with col_b:
                    st.metric("Avg SEO Score", f"{stats['avg_seo_score']}/100" if stats['avg_seo_score'] else "N/A")
                with col_c:
                    st.metric("Topics in Queue", stats['topics_generated'] - stats['topics_used'])
                with col_d:
                    st.metric("Last Generated", stats['last_generated'])
            except Exception:
                pass  # Skip dashboard if stats unavailable

        st.header(f"📝 Content for {brand_config.display_name}")

        # Topic Generator Section
        st.subheader("💡 Topic Idea Generator")

        # Pre-populated keywords from brand config
        default_keywords = ", ".join(brand_config.primary_keywords[:5]) if brand_config.primary_keywords else ""
        target_keywords = st.text_input(
            "🎯 Target Keywords",
            value=default_keywords,
            help="Keywords to prioritize in topic generation. Pre-filled from brand config."
        )

        # Product/page target - dropdown from brand's key products or custom input
        st.markdown("**🛍️ Product/Page Target**")
        if brand_config.key_products:
            product_options = ["None - No specific product"] + [p.name for p in brand_config.key_products]
            selected_product_idx = st.selectbox(
                "Select a product to promote",
                options=range(len(product_options)),
                format_func=lambda i: product_options[i]
            )
            if selected_product_idx > 0:
                selected_product = brand_config.key_products[selected_product_idx - 1]
                product_target = f"Product: {selected_product.name}\nURL: {selected_product.url}\nDescription: {selected_product.description}"
                st.info(f"Promoting: {selected_product.name}")
            else:
                product_target = st.text_area(
                    "Custom product target (optional)",
                    placeholder="Enter product URL and description...",
                    height=80
                )
        else:
            product_target = st.text_area(
                "Product/Page Target (Optional)",
                placeholder="e.g., Page URL: https://example.com/product\nDescription: Brief description...",
                height=80,
                help="Enter a product page to naturally promote in the content."
            )

        if st.button("🎯 Generate Topic Ideas", help=f"AI-powered topic suggestions for {brand_config.display_name}"):
            if not reference_blog.strip():
                st.error("⚠️ No reference blog configured")
            elif not api_key:
                st.error("⚠️ Please set OPENAI_API_KEY in your .env file")
            else:
                with st.spinner(f"Generating topic ideas for {brand_config.display_name}..."):
                    with temporary_env_var("OPENAI_API_KEY", api_key):
                        orchestrator = BlogAgentOrchestrator(model=model, brand_config=brand_config)

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
                        st.session_state.topic_gen_product_target = product_target.strip() if product_target.strip() else ""
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

                        # Transfer product target from topic generator to blog generator
                        if 'topic_gen_product_target' in st.session_state:
                            st.session_state.blog_product_target = st.session_state.topic_gen_product_target

                        # Mark topic as used in Google Sheets if enabled
                        if sheets_manager and 'ID' in topic_idea:
                            try:
                                sheets_manager.mark_topic_used(topic_idea['ID'])
                                st.success(f"✅ Topic marked as used in Google Sheets!")
                            except Exception as e:
                                st.warning(f"⚠️ Could not mark topic as used: {str(e)}")

                        st.rerun()

        st.markdown("---")

        # Auto-Pilot Mode Section
        st.subheader("🚀 Auto-Pilot Mode")
        st.caption("Generate multiple blog posts automatically without intervention")

        # Get available topics for preview
        available_topics = get_available_topics_for_autopilot(st.session_state, sheets_manager)
        topics_available_count = len(available_topics)

        # Show topic availability status
        if topics_available_count > 0:
            st.success(f"✅ {topics_available_count} topics available for auto-pilot")
        else:
            st.info("💡 No topics available - will auto-generate topics when started")

        # Number of posts slider
        max_posts = min(topics_available_count, MAX_AUTOPILOT_POSTS) if topics_available_count > 0 else MAX_AUTOPILOT_POSTS
        num_posts = st.slider(
            "Number of posts to generate",
            min_value=1,
            max_value=max_posts if max_posts > 0 else MAX_AUTOPILOT_POSTS,
            value=min(3, max_posts) if max_posts > 0 else 3,
            help=f"Maximum {MAX_AUTOPILOT_POSTS} posts per auto-pilot run"
        )

        # Topics preview expander
        if topics_available_count > 0:
            with st.expander(f"📋 Preview queued topics ({min(num_posts, topics_available_count)} of {topics_available_count})"):
                for i, topic_item in enumerate(available_topics[:num_posts]):
                    st.markdown(f"**{i+1}.** {topic_item.get('title', 'Untitled')}")
                    if topic_item.get('angle'):
                        st.caption(f"   Angle: {topic_item['angle']}")

        # Auto-pilot control buttons
        col_start, col_stop = st.columns(2)

        with col_start:
            start_disabled = st.session_state.autopilot_active
            if st.button(
                "▶️ Start Auto-Pilot",
                type="primary",
                disabled=start_disabled or not api_key,
                help="Start generating blog posts automatically"
            ):
                # Initialize auto-pilot
                if topics_available_count == 0:
                    # Need to auto-generate topics first
                    st.session_state.autopilot_needs_topics = True
                else:
                    # Queue up topics
                    st.session_state.autopilot_topics_queue = available_topics[:num_posts].copy()

                st.session_state.autopilot_active = True
                st.session_state.autopilot_stop_requested = False
                st.session_state.autopilot_total_posts = num_posts
                st.session_state.autopilot_completed_posts = 0
                st.session_state.autopilot_results = []
                st.session_state.autopilot_errors = []
                st.session_state.autopilot_cached_style = None
                st.rerun()

        with col_stop:
            stop_disabled = not st.session_state.autopilot_active
            if st.button(
                "⏹️ Stop Auto-Pilot",
                disabled=stop_disabled,
                help="Stop after current post completes"
            ):
                st.session_state.autopilot_stop_requested = True
                st.warning("⏹️ Stop requested - will stop after current post completes")

        # Show auto-pilot progress when active
        if st.session_state.autopilot_active:
            st.markdown("---")
            st.markdown("### 🔄 Auto-Pilot Progress")

            # Overall progress bar
            progress_pct = st.session_state.autopilot_completed_posts / st.session_state.autopilot_total_posts
            st.progress(progress_pct)
            st.markdown(f"**{st.session_state.autopilot_completed_posts}/{st.session_state.autopilot_total_posts}** posts completed")

            # Current topic being processed
            if st.session_state.autopilot_current_topic:
                st.info(f"🔄 Currently processing: **{st.session_state.autopilot_current_topic}**")

            # Completed posts list
            if st.session_state.autopilot_results:
                with st.expander(f"✅ Completed posts ({len(st.session_state.autopilot_results)})", expanded=False):
                    for i, result in enumerate(st.session_state.autopilot_results):
                        status_icon = "✅" if result.get('success') else "❌"
                        st.markdown(f"{status_icon} **{i+1}.** {result.get('topic', 'Unknown')}")

            # Error list
            if st.session_state.autopilot_errors:
                with st.expander(f"❌ Errors ({len(st.session_state.autopilot_errors)})", expanded=True):
                    for error in st.session_state.autopilot_errors:
                        st.error(f"**{error.get('topic', 'Unknown')}**: {error.get('error', 'Unknown error')}")

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
                    # Initialize orchestrator with selected model and brand config
                    orchestrator = BlogAgentOrchestrator(model=model, brand_config=brand_config)

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

    # Auto-Pilot Results Section
    if st.session_state.autopilot_results:
        st.markdown("---")
        st.header("🚀 Auto-Pilot Results")

        # Summary metrics
        total_results = len(st.session_state.autopilot_results)
        successful = sum(1 for r in st.session_state.autopilot_results if r.get('success'))
        failed = total_results - successful

        col_metric1, col_metric2, col_metric3 = st.columns(3)
        with col_metric1:
            st.metric("Total Generated", total_results)
        with col_metric2:
            st.metric("Successful", successful, delta=None)
        with col_metric3:
            st.metric("Failed", failed, delta=None, delta_color="inverse" if failed > 0 else "off")

        # Expandable results for each post
        for i, result in enumerate(st.session_state.autopilot_results):
            topic_name = result.get('topic', f'Post {i+1}')
            status_icon = "✅" if result.get('success') else "❌"

            with st.expander(f"{status_icon} {topic_name}", expanded=False):
                if result.get('success') and 'results' in result:
                    post_results = result['results']

                    # Show tabs for this post's content
                    ap_tab1, ap_tab2, ap_tab3 = st.tabs(["📄 Final Post", "🎨 Style Guide", "📊 SEO Analysis"])

                    with ap_tab1:
                        if 'final' in post_results:
                            st.markdown(post_results['final'])

                            # Download buttons
                            dl_col1, dl_col2 = st.columns(2)
                            with dl_col1:
                                st.download_button(
                                    label="📄 Download as Text",
                                    data=post_results['final'],
                                    file_name=f"autopilot_{topic_name[:30].replace(' ', '_').lower()}.txt",
                                    mime="text/plain",
                                    key=f"ap_dl_txt_{i}",
                                    use_container_width=True
                                )
                            with dl_col2:
                                st.download_button(
                                    label="📝 Download as Markdown",
                                    data=post_results['final'],
                                    file_name=f"autopilot_{topic_name[:30].replace(' ', '_').lower()}.md",
                                    mime="text/markdown",
                                    key=f"ap_dl_md_{i}",
                                    use_container_width=True
                                )
                        else:
                            st.info("Final content not available")

                    with ap_tab2:
                        if 'style_guide' in post_results:
                            st.text_area(
                                "Style Guide",
                                value=post_results['style_guide'],
                                height=300,
                                disabled=False,
                                key=f"ap_style_{i}"
                            )
                        else:
                            st.info("Style guide not available")

                    with ap_tab3:
                        if 'seo_analysis' in post_results:
                            st.text_area(
                                "SEO Analysis",
                                value=post_results['seo_analysis'],
                                height=300,
                                disabled=False,
                                key=f"ap_seo_{i}"
                            )
                        else:
                            st.info("SEO analysis not available")
                else:
                    st.error(f"Error: {result.get('error', 'Unknown error')}")

        # Clear results button
        if st.button("🗑️ Clear Auto-Pilot Results", help="Remove all auto-pilot results from this session"):
            st.session_state.autopilot_results = []
            st.session_state.autopilot_errors = []
            st.rerun()

    # Footer
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: gray; padding: 2rem 0;'>
        <p><strong>Safety Products Global</strong> - Multi-Brand Content Generation</p>
        <p style='font-size: 0.9rem; margin-top: 0.5rem;'>Slice | Klever Innovations | Pacific Handy Cutter</p>
        <p style='font-size: 0.8rem; margin-top: 0.5rem;'>Powered by OpenAI Agents SDK | Built by Bertram Labs</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()