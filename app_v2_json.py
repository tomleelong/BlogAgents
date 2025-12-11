#!/usr/bin/env python3
"""
Streamlit app for submitting JSON to OpenAI AgentBuilder workflow.
"""
import streamlit as st
import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables immediately after imports
load_dotenv()

# Configuration
class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    WORKFLOW_ID = os.getenv("WORKFLOW_ID", "wf_692e0fdc02508190b3b51b94f2b7deea0f87a40e1a3b5c93")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Logging setup
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Sample JSON template
SAMPLE_JSON = """{
  "existing_blog_posts_to_avoid": [
    "https://blog.example.com/post-1",
    "https://blog.example.com/post-2"
  ],
  "high_performing_pages": [
    "https://blog.example.com/high-performer-1",
    "https://blog.example.com/high-performer-2"
  ],
  "root_blog_url": "https://blog.example.com/",
  "seo_keywords": [
    "keyword1",
    "keyword2",
    "keyword3"
  ],
  "target_product_urls": [
    "https://www.example.com/products/product-1"
  ],
  "topics": [
    "your topic here"
  ],
  "writing_requirements": "length should be 2000 words, include FAQ section, add call to action"
}"""


def validate_json(json_text: str) -> tuple[bool, str, dict | None]:
    """
    Validate JSON text and return parsed object.

    Returns:
        tuple: (is_valid, error_message, parsed_json)
    """
    if not json_text or not json_text.strip():
        return False, "JSON input is empty", None

    try:
        parsed = json.loads(json_text)
        logger.info("JSON validation successful")
        return True, "", parsed
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None


def call_workflow(json_input: str, api_key: str) -> dict:
    """
    Call the OpenAI AgentBuilder workflow with JSON input.

    Args:
        json_input: JSON string to send to the workflow
        api_key: OpenAI API key

    Returns:
        dict with response or error
    """
    import requests

    logger.info(f"Calling workflow: {Config.WORKFLOW_ID}")

    url = "https://api.openai.com/v1/responses"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o",
        "input": json_input,
        "workflow": {
            "id": Config.WORKFLOW_ID
        }
    }

    try:
        logger.info("Sending request to OpenAI workflow API")
        response = requests.post(url, headers=headers, json=payload, timeout=600)

        logger.info(f"Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            logger.info("Workflow completed successfully")
            return {"success": True, "data": result}
        else:
            error_detail = response.text
            logger.error(f"API error: {response.status_code} - {error_detail}")
            return {"success": False, "error": f"API Error ({response.status_code}): {error_detail}"}

    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return {"success": False, "error": "Request timed out after 10 minutes"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return {"success": False, "error": f"Request failed: {str(e)}"}


def main():
    """Streamlit app entry point."""
    st.set_page_config(
        page_title="Blog Agent Workflow",
        page_icon=">",
        layout="wide"
    )

    st.title("> Blog Agent Workflow")
    st.markdown("Submit JSON configuration to run the OpenAI AgentBuilder workflow")

    # Sidebar for configuration
    with st.sidebar:
        st.header("™ Configuration")

        # API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            value=Config.OPENAI_API_KEY or "",
            type="password",
            help="Your OpenAI API key"
        )

        # Workflow ID display
        st.text_input(
            "Workflow ID",
            value=Config.WORKFLOW_ID,
            disabled=True,
            help="The AgentBuilder workflow ID"
        )

        st.markdown("---")

        # Load sample button
        if st.button("=Ë Load Sample JSON"):
            st.session_state.json_input = SAMPLE_JSON
            st.rerun()

        # Clear button
        if st.button("=Ñ Clear Input"):
            st.session_state.json_input = ""
            st.rerun()

    # Main content
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("=Ý JSON Input")

        # Initialize session state for json_input if not exists
        if 'json_input' not in st.session_state:
            st.session_state.json_input = ""

        # JSON textarea
        json_input = st.text_area(
            "Enter your JSON configuration:",
            value=st.session_state.json_input,
            height=500,
            placeholder=SAMPLE_JSON,
            help="Paste your JSON configuration here"
        )

        # Update session state
        st.session_state.json_input = json_input

        # Validate button
        col_validate, col_submit = st.columns(2)

        with col_validate:
            if st.button(" Validate JSON", use_container_width=True):
                is_valid, error_msg, parsed = validate_json(json_input)
                if is_valid:
                    st.success("JSON is valid!")
                    with st.expander("Parsed JSON", expanded=False):
                        st.json(parsed)
                else:
                    st.error(error_msg)

        with col_submit:
            submit_disabled = not api_key or not json_input.strip()
            if st.button("=€ Submit to Workflow", type="primary", use_container_width=True, disabled=submit_disabled):
                # Validate JSON first
                is_valid, error_msg, parsed = validate_json(json_input)

                if not is_valid:
                    st.error(error_msg)
                else:
                    st.session_state.run_workflow = True
                    st.session_state.workflow_input = json_input

    with col2:
        st.header("=Ê Output")

        # Run workflow if triggered
        if st.session_state.get('run_workflow'):
            st.session_state.run_workflow = False

            with st.spinner("Running workflow... This may take several minutes."):
                progress_bar = st.progress(0, text="Initializing...")

                progress_bar.progress(10, text="Sending request to OpenAI...")
                result = call_workflow(st.session_state.workflow_input, api_key)

                progress_bar.progress(100, text="Complete!")

                if result["success"]:
                    st.success("Workflow completed successfully!")

                    # Store result in session state
                    st.session_state.workflow_result = result["data"]
                else:
                    st.error(result["error"])

        # Display results if available
        if 'workflow_result' in st.session_state:
            result_data = st.session_state.workflow_result

            # Try to extract the output text
            if isinstance(result_data, dict):
                # Check for common response structures
                output_text = None

                if 'output' in result_data:
                    output_text = result_data['output']
                elif 'choices' in result_data and len(result_data['choices']) > 0:
                    choice = result_data['choices'][0]
                    if 'message' in choice:
                        output_text = choice['message'].get('content', '')
                    elif 'text' in choice:
                        output_text = choice['text']

                if output_text:
                    st.markdown("### Generated Content")
                    st.markdown(output_text)

                    # Download button
                    st.download_button(
                        label="=å Download as Markdown",
                        data=output_text,
                        file_name="blog_post.md",
                        mime="text/markdown"
                    )

                # Show raw response in expander
                with st.expander("= Raw API Response", expanded=False):
                    st.json(result_data)
            else:
                st.text_area("Result", value=str(result_data), height=400)

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; padding: 1rem 0;'>
        <p>Powered by OpenAI AgentBuilder | Workflow ID: {}</p>
        </div>
        """.format(Config.WORKFLOW_ID),
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
