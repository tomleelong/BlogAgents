#!/usr/bin/env python3
import streamlit as st
import os
import tempfile
from blog_orchestrator import BlogAgentOrchestrator

def main():
    st.set_page_config(
        page_title="Blog Agents - AI Content Generator",
        page_icon="✍️",
        layout="wide"
    )
    
    st.title("✍️ Blog Agents")
    st.markdown("**AI-powered blog content generation with style matching**")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Your OpenAI API key for the Agents SDK"
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
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📝 Content Settings")
        
        # Topic input
        topic = st.text_area(
            "Blog Topic",
            height=100,
            placeholder="Enter your blog topic (e.g., 'The Future of Remote Work')",
            help="The main subject for your blog post"
        )
        
        # Requirements input
        requirements = st.text_area(
            "Additional Requirements",
            height=150,
            placeholder="""- Target audience: [your audience]
- Include practical examples
- Keep under [word count] words
- Add call-to-action
- Focus on [specific aspect]""",
            help="Specific requirements for your blog post"
        )
        
        # Generate button
        generate_button = st.button(
            "🚀 Generate Blog Post",
            type="primary",
            disabled=not (api_key and topic.strip())
        )
    
    with col2:
        st.header("📊 Output")
        
        if generate_button:
            if not topic.strip():
                st.error("❌ Please enter a topic for your blog post")
                return
            
            # Set API key as environment variable temporarily
            os.environ["OPENAI_API_KEY"] = api_key
            
            try:
                # Initialize orchestrator
                orchestrator = BlogAgentOrchestrator()
                
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
                        st.markdown(results["final"])
                        
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
                            height=300,
                            disabled=True
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
                                    height=200,
                                    disabled=True,
                                    key="duplication_area"
                                )
                        else:
                            st.info("Duplication check data not available")
                        
                        # Research section
                        st.subheader("Topic Research")
                        st.text_area(
                            "Research Results",
                            value=results["research"],
                            height=300,
                            disabled=True,
                            key="research_area"
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
                                height=400,
                                disabled=True,
                                key="seo_area"
                            )
                        else:
                            st.info("SEO analysis not available")
                        
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                st.info("💡 Make sure your OpenAI API key is valid and has access to the Agents API")
            
            finally:
                # Clean up environment variable
                if "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        <p>Powered by OpenAI Agents SDK | Built with Streamlit</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()