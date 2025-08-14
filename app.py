#!/usr/bin/env python3
import streamlit as st
import os
import re
import contextlib
from urllib.parse import urlparse
from blog_orchestrator import BlogAgentOrchestrator

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
        
        # Topic input
        topic = st.text_area(
            "Blog Topic",
            height=100,
            max_chars=MAX_TOPIC_LENGTH,
            placeholder=f"Enter your blog topic (max {MAX_TOPIC_LENGTH} characters)",
            help="The main subject for your blog post"
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
            help="Specific requirements for your blog post"
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
                    
                    # Generate blog post with real-time updates
                    results = orchestrator.create_blog_post(
                        topic=topic,
                        reference_blog=reference_blog,
                        requirements=requirements,
                        status_callback=update_status
                    )
                
                # Display results
                if "error" in results:
                    st.error(f"❌ Error: {results['error']}")
                else:
                    # Show duplication warning if needed
                    if "duplication_status" in results:
                        if results["duplication_status"] == "HIGH_RISK":
                            st.error("🚨 **HIGH RISK**: Similar content already exists on this blog!")
                        elif results["duplication_status"] == "WARNING":
                            st.warning("⚠️ **WARNING**: Some similar content found on this blog.")
                        else:
                            st.success("✅ **CLEAR**: No duplicate content detected.")
                    # Tabs for different outputs
                    tab1, tab2, tab3, tab4 = st.tabs(["📄 Final Post", "🎨 Style Guide", "🔍 Research & Analysis", "📊 SEO Analysis"])
                    
                    with tab1:
                        st.markdown("### Final Blog Post")
                        st.text_area(
                            "Generated Blog Post",
                            value=results["final"],
                            height=500,
                            disabled=False,
                            help="You can copy or edit the final blog post"
                        )
                        
                        # Download button
                        st.download_button(
                            label="📥 Download as Text",
                            data=results["final"],
                            file_name=f"blog_post_{topic[:30].replace(' ', '_')}.txt",
                            mime="text/plain"
                        )
                    
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
                        
                        # Duplication check section
                        st.subheader("Content Duplication Check")
                        if "duplication_check" in results:
                            with st.expander("View Duplication Analysis", expanded=False):
                                st.text_area(
                                    "Duplication Analysis Results",
                                    value=results["duplication_check"],
                                    height=250,
                                    disabled=False,
                                    key="duplication_area",
                                    help="You can copy text from this field"
                                )
                        else:
                            st.info("Duplication check data not available")
                        
                        # Research section
                        st.subheader("Topic Research")
                        st.text_area(
                            "Research Results",
                            value=results["research"],
                            height=350,
                            disabled=False,
                            key="research_area",
                            help="You can copy text from this field"
                        )
                    
                    with tab4:
                        st.markdown("### SEO Performance Analysis")
                        
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
                st.error(f"❌ An error occurred. Please check your inputs and try again.")
                st.info("💡 Make sure your OpenAI API key is valid and has access to the Agents API")
    
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