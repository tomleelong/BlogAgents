#!/usr/bin/env python3
"""
Streamlit app for Topic Idea Generation using TopicIdeaAgent.
"""
import streamlit as st
import os
import logging
import time
from dotenv import load_dotenv

load_dotenv()


class Config:
    """App configuration."""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# Logging setup
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def generate_topics(
    api_key: str,
    model: str,
    reference_blog: str,
    target_keywords: list,
    product_target: str,
    existing_topics: list,
    num_topics: int,
    status_placeholder,
    progress_bar
) -> dict:
    """
    Generate topic ideas using TopicIdeaAgent.

    Args:
        api_key: OpenAI API key
        model: Model to use
        reference_blog: Blog URL to analyze
        target_keywords: List of keywords to incorporate
        product_target: Product/service to promote
        existing_topics: Topics to avoid duplicating
        num_topics: Number of topics to generate
        status_placeholder: Streamlit placeholder for status
        progress_bar: Streamlit progress bar

    Returns:
        dict with success status and data/error
    """
    os.environ["OPENAI_API_KEY"] = api_key

    logger.info(f"Generating topics for {reference_blog}")

    try:
        from custom_agents import TopicIdeaAgent

        agent = TopicIdeaAgent(model=model)

        def status_callback(message: str, progress: int):
            status_placeholder.info(message)
            progress_bar.progress(progress)

        status_callback("Initializing TopicIdeaAgent...", 10)

        topics = agent.generate(
            reference_blog=reference_blog,
            target_keywords=target_keywords if target_keywords else None,
            product_target=product_target if product_target else None,
            existing_topics=existing_topics if existing_topics else None,
            num_topics=num_topics,
            status_callback=status_callback
        )

        logger.info(f"Generated {len(topics)} topics")
        return {"success": True, "data": topics}

    except Exception as e:
        logger.error(f"Topic generation failed: {str(e)}")
        return {"success": False, "error": str(e)}


def main():
    """Streamlit app entry point."""
    st.set_page_config(
        page_title="Blog Agent",
        layout="wide"
    )

    st.title("Blog Agent")
    st.markdown("Generate topic ideas, select the ones you like, then generate blog content")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")

        # API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            value=Config.OPENAI_API_KEY or "",
            type="password",
            help="Your OpenAI API key"
        )

    # Reference blog URL (required)
    reference_blog = st.text_input(
        "Reference Blog URL (required)",
        placeholder="https://blog.example.com/",
        help="The blog to analyze for style and content strategy"
    )

    # High performing pages (optional)
    high_performing_pages_input = st.text_area(
        "High Performing Pages (optional)",
        placeholder="e.g. https://blog.example.com/best-article\nhttps://blog.example.com/top-post",
        height=100,
        help="URLs of high-performing blog posts to analyze for style patterns"
    )

    # Parse high performing pages into list
    high_performing_pages = []
    if high_performing_pages_input.strip():
        high_performing_pages = [p.strip() for p in high_performing_pages_input.split('\n') if p.strip()]

    # Target keywords (optional)
    keywords_input = st.text_area(
        "Target Keywords (optional)",
        placeholder="e.g: safety knives, utility knives, box cutter safety",
        height=100,
        help="Keywords to incorporate into topic ideas for SEO"
    )

    # Parse keywords into list
    target_keywords = []
    if keywords_input.strip():
        target_keywords = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]

    # Product target (optional)
    product_target = st.text_area(
        "Target Product/Service URLs (optional)",
        placeholder="e.g. https://example.com/products/my-product\nhttps://example.com/products/some-other-product",
        height=100,
        help="Product or service to naturally promote in topic ideas"
    )

    # Existing topics to avoid (optional)
    existing_topics_input = st.text_area(
        "Existing Topics to Avoid (optional)",
        placeholder="Enter existing blog post titles, one per line:\nHow to Choose the Right Safety Knife\n10 Tips for Warehouse Safety",
        height=150,
        help="Existing blog posts to avoid duplicating"
    )

    # Parse existing topics into list
    existing_topics = []
    if existing_topics_input.strip():
        existing_topics = [t.strip() for t in existing_topics_input.split('\n') if t.strip()]

    # Additional requirements (optional)
    additional_requirements = st.text_area(
        "Additional Requirements (optional)",
        placeholder="Content must be at least 2000 words and has a call to action",
        height=100,
        help="Additional requirements for blog content generation"
    )

    # Number of topics
    num_topics_input = st.text_input(
        "Number of Topics",
        value="5",
        help="How many topic ideas to generate"
    )

    # Parse num_topics as integer
    try:
        num_topics = int(num_topics_input)
        if num_topics < 1:
            num_topics = 1
        elif num_topics > 20:
            num_topics = 20
    except ValueError:
        num_topics = 5

    # Generate button
    generate_disabled = not api_key or not reference_blog.strip()
    if st.button("Generate Topic Ideas", type="primary", disabled=generate_disabled):
        st.session_state.run_generation = True

    st.markdown("---")
    st.header("Topic Ideas")

    # Run generation if triggered
    if st.session_state.get('run_generation'):
        st.session_state.run_generation = False

        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        status_placeholder.info("Initializing...")

        start_time = time.time()
        result = generate_topics(
            api_key=api_key,
            model=Config.OPENAI_MODEL,
            reference_blog=reference_blog,
            target_keywords=target_keywords,
            product_target=product_target,
            existing_topics=existing_topics,
            num_topics=num_topics,
            status_placeholder=status_placeholder,
            progress_bar=progress_bar
        )
        elapsed_seconds = int(time.time() - start_time)

        # Format elapsed time as HH:MM:SS
        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        if result["success"]:
            progress_bar.progress(100)
            status_placeholder.success(f"Generated {len(result['data'])} topic ideas! Time elapsed: {elapsed_str}")
            st.session_state.generated_topics = result["data"]
        else:
            status_placeholder.error(f"Error: {result['error']} (Time elapsed: {elapsed_str})")

    # Display generated topics
    if 'generated_topics' in st.session_state and st.session_state.generated_topics:
        topics = st.session_state.generated_topics

        # Initialize selected topics in session state if not exists
        if 'selected_topics' not in st.session_state:
            st.session_state.selected_topics = {}

        for i, topic in enumerate(topics):
            topic_key = f"topic_{i}"
            col_check, col_expander = st.columns([0.05, 0.95])

            with col_check:
                is_selected = st.checkbox(
                    "",
                    key=topic_key,
                    value=st.session_state.selected_topics.get(topic_key, False),
                    label_visibility="collapsed"
                )
                st.session_state.selected_topics[topic_key] = is_selected

            with col_expander:
                with st.expander(f"{i + 1}. {topic.get('title', 'Untitled')}", expanded=(i == 0)):
                    st.markdown(f"**Angle:** {topic.get('angle', 'N/A')}")
                    st.markdown(f"**Rationale:** {topic.get('rationale', 'N/A')}")
                    st.markdown(f"**Content Type:** {topic.get('content_type', 'N/A')}")
                    keywords = topic.get('keywords', [])
                    if keywords:
                        st.markdown(f"**Keywords:** {', '.join(keywords)}")

        # Get selected topics count
        selected_indices = [i for i in range(len(topics)) if st.session_state.selected_topics.get(f"topic_{i}", False)]
        selected_count = len(selected_indices)

        # Generate Blog(s) button
        st.markdown("---")
        button_label = f"Generate Blog(s) ({selected_count} selected)" if selected_count > 0 else "Generate Blog(s)"
        generate_blogs_disabled = selected_count == 0
        if st.button(button_label, type="primary", disabled=generate_blogs_disabled):
            st.session_state.run_blog_generation = True
            st.session_state.selected_topics_for_blogs = [topics[i] for i in selected_indices]

        # Display generated JSON for testing
        if st.session_state.get('run_blog_generation'):
            st.session_state.run_blog_generation = False

            st.markdown("---")
            st.subheader("Generated JSON (for testing)")

            selected_topics_list = st.session_state.get('selected_topics_for_blogs', [])

            for i, topic in enumerate(selected_topics_list):
                # Build writing_requirements from topic attributes
                writing_requirements_parts = []
                if topic.get('angle'):
                    writing_requirements_parts.append(f"Angle: {topic.get('angle')}")
                if topic.get('rationale'):
                    writing_requirements_parts.append(f"Rationale: {topic.get('rationale')}")
                if topic.get('content_type'):
                    writing_requirements_parts.append(f"Content Type: {topic.get('content_type')}")
                if topic.get('keywords'):
                    writing_requirements_parts.append(f"Keywords: {', '.join(topic.get('keywords', []))}")
                if additional_requirements.strip():
                    writing_requirements_parts.append(f"Additional Requirements: {additional_requirements.strip()}")
                writing_requirements = '\n'.join(writing_requirements_parts)

                # Build JSON object
                topic_json = {
                    "high_performing_pages": high_performing_pages if high_performing_pages else ["N/A"],
                    "root_blog_url": reference_blog,
                    "target_product_urls": [p.strip() for p in product_target.split('\n') if p.strip()] if product_target.strip() else ["N/A"],
                    "topics": [topic.get('title', 'Untitled')],
                    "writing_requirements": writing_requirements
                }

                with st.expander(f"Topic {i + 1}: {topic.get('title', 'Untitled')}", expanded=True):
                    st.json(topic_json)

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; padding: 1rem 0;'>
        <p>Powered by Bertram Labs</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
