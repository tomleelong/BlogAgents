#!/usr/bin/env python3
import asyncio
import threading
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dotenv import load_dotenv
from agents import Agent, Runner, WebSearchTool

load_dotenv()

class BlogAgentOrchestrator:
    def __init__(self, model="gpt-4o"):
        # Store the model for all agents
        self.model = model
        
        # Thread pool for agent execution (prevents resource leaks)
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent-")
        
        # Specialist agents
        self.agents = {
            "style_analyzer": Agent(
                name="Blog Style Analyzer",
                model=self.model,
                instructions="""You are a writing style analyzer that can analyze any blog or publication.
                
                Your tasks:
                1. Use web search to fetch recent articles from the specified blog/publication: {blog_source}
                2. Analyze their writing style, tone, and voice patterns
                3. Extract key stylistic elements including:
                   - Headlines: structure, length, power words
                   - Opening paragraphs: hook techniques, information density
                   - Voice: tone characteristics and personality
                   - Technical language: complexity level and jargon usage
                   - Sentence structure: variety, length patterns, rhythm
                   - Common phrases, vocabulary, and expressions
                   - Paragraph organization and flow
                   - Typical post length
                4. Create actionable style guidelines for writers to replicate
                
                Focus on identifying measurable, replicable patterns.
                Provide specific examples from the analyzed content.
                """,
                tools=[WebSearchTool()]
            ),
            "content_checker": Agent(
                name="Content Duplication Checker",
                model=self.model,
                instructions="""You are a content duplication specialist that checks for existing content on blogs.
                
                Your tasks:
                1. Search the specified blog/website for existing content on the given topic
                2. Identify any articles that cover similar or identical subjects
                3. Assess the level of duplication risk and content overlap
                4. Provide recommendations for differentiation if duplicates are found
                
                Analysis criteria:
                - Look for articles with similar titles, topics, or keywords
                - Check for content that covers the same main points
                - Identify seasonal or recurring content patterns
                - Consider different angles or approaches to the same topic
                
                Return analysis in this format:
                DUPLICATION STATUS: [CLEAR/WARNING/HIGH_RISK]
                EXISTING CONTENT FOUND: [Number] similar articles
                SIMILAR ARTICLES:
                - [Title] - [URL] - [Similarity level: Low/Medium/High]
                
                RECOMMENDATIONS:
                - [Specific suggestions for differentiation]
                - [Unique angles to explore]
                - [How to add value beyond existing content]
                """,
                tools=[WebSearchTool()]
            ),
            "researcher": Agent(
                name="Research Specialist",
                model=self.model,
                instructions="""You are a research specialist for blog content.
                - Research the given topic thoroughly
                - Find relevant facts, statistics, and examples
                - Identify key points and subtopics
                - Provide structured research data
                - Include sources when possible
                """,
                tools=[WebSearchTool()]
            ),
            "writer": Agent(
                name="Content Writer",
                model=self.model, 
                instructions="""You are a skilled blog writer.
                - Create engaging, well-structured blog posts
                - Use provided research effectively
                - Write clear introductions and conclusions
                - Include subheadings and bullet points
                - Maintain conversational but professional tone
                """
            ),
            "internal_linker": Agent(
                name="Internal Linking Specialist",
                model=self.model,
                instructions="""You are an internal linking specialist for blog content.
                
                Your tasks:
                1. Analyze the blog post content for internal linking opportunities
                2. Identify keywords and phrases that could link to other relevant content
                3. Search for related articles on the same website/domain
                4. Add strategic internal links using natural anchor text
                5. Ensure links enhance user experience and SEO
                
                Guidelines:
                - Use natural, contextual anchor text (avoid "click here")
                - Link to genuinely relevant and helpful content
                - Don't over-link (2-5 internal links per 1000 words is optimal)
                - Prioritize links that add value to the reader
                - Use varied anchor text for similar topics
                - Link to both newer and evergreen content when appropriate
                - Prioritize collections pages and blog posts over pdps
                
                Return the content with internal links added in markdown format [anchor text](URL).
                """,
                tools=[WebSearchTool()]
            ),
            "editor": Agent(
                name="Content Editor",
                model=self.model,
                instructions="""You are a content editor.
                - Review content for clarity and flow
                - Fix grammar and style issues
                - Ensure consistent tone throughout
                - Improve readability and engagement
                - Suggest structural improvements
                - Consider SEO and AI visibility
                - Preserve any internal links that have been added
                """
            ),
            "seo_analyzer": Agent(
                name="SEO Content Analyzer",
                model=self.model,
                instructions="""You are an SEO analysis specialist that evaluates blog content.
                
                Your tasks:
                1. Analyze the final blog post for SEO best practices
                2. Provide specific, actionable recommendations
                3. Give an overall SEO score and breakdown
                
                Evaluation criteria:
                - Title optimization (length, keywords, compelling)
                - Heading structure (H1, H2, H3 hierarchy)
                - Content length and readability
                - Keyword usage and density
                - Internal linking effectiveness
                - Meta description potential
                - Content structure and scannability
                - Search intent alignment
                
                Return analysis in this format:
                SEO SCORE: [X/100]
                
                STRENGTHS:
                ✅ [What's working well]
                
                IMPROVEMENTS:
                ⚠️ [Specific actionable recommendations]
                
                TITLE ANALYSIS: [Assessment and suggestions]
                CONTENT STRUCTURE: [Heading hierarchy, readability]
                KEYWORD USAGE: [Natural integration assessment]
                INTERNAL LINKS: [Link quality and relevance]
                
                QUICK WINS:
                - [1-3 easy improvements for immediate SEO gains]
                """
            )
        }
    
    def _run_agent_safely(self, agent, prompt, timeout_seconds=300):
        """Run agent with Streamlit thread compatibility and proper resource management."""
        
        def run_in_thread():
            """Run the agent in a separate thread with its own event loop."""
            loop = None
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = Runner.run_sync(agent, prompt)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": e}
            finally:
                # Ensure event loop is properly cleaned up
                if loop is not None:
                    try:
                        loop.close()
                    except Exception:
                        pass  # Ignore cleanup errors
        
        # Use ThreadPoolExecutor for proper resource management
        try:
            future = self._thread_pool.submit(run_in_thread)
            data = future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            raise TimeoutError(f"Agent '{agent.name}' execution timed out after {timeout_seconds} seconds")
        
        if not data["success"]:
            print(f"❌ Agent '{agent.name}' execution failed: {data['error']}")
            raise data["error"]
        
        return data["result"]
    
    def __del__(self):
        """Cleanup thread pool on destruction."""
        if hasattr(self, '_thread_pool'):
            self._thread_pool.shutdown(wait=True)

    def create_blog_post(self, topic: str, reference_blog: str, requirements: str = "", status_callback=None) -> Dict[str, str]:
        """Create a blog post that matches the style of a reference publication."""
        results = {}
        
        try:
            # Step 1: Analyze reference style
            if status_callback:
                status_callback("🎨 Analyzing blog style...", 10)
            print(f"🎨 Analyzing {reference_blog} style...")
            style_guide = self.analyze_blog_style(reference_blog, status_callback)
            results["style_guide"] = style_guide
            
            # Step 2: Check for content duplication
            if status_callback:
                status_callback("🔍 Checking for duplicate content...", 30)
            print("🔍 Checking for existing content on this topic...")
            duplication_prompt = f"""
            Check for existing content on {reference_blog} about the topic: {topic}
            
            Search for articles that cover similar subjects and assess duplication risk.
            Provide specific recommendations for differentiation if duplicates are found.
            
            Topic to check: {topic}
            Website to search: {reference_blog}
            """
            
            duplication_result = self._run_agent_safely(self.agents["content_checker"], duplication_prompt)
            results["duplication_check"] = duplication_result.final_output
            
            # Parse duplication status for warnings
            duplication_status = "CLEAR"
            if "HIGH_RISK" in duplication_result.final_output:
                duplication_status = "HIGH_RISK"
            elif "WARNING" in duplication_result.final_output:
                duplication_status = "WARNING"
            results["duplication_status"] = duplication_status
            
            # Step 3: Research topic
            if status_callback:
                status_callback("🔍 Researching topic...", 45)
            print("🔍 Researching topic...")
            research_prompt = f"""
            Research the topic: {topic}
            
            Requirements: {requirements}
            
            DUPLICATION ANALYSIS:
            {duplication_result.final_output}
            
            Based on the duplication analysis above, focus your research on:
            - New angles or perspectives not covered in existing content
            - Recent developments or trends in this area
            - Unique insights that add value beyond what already exists
            - Facts, statistics, and examples that differentiate this post
            """
            research_result = self._run_agent_safely(self.agents["researcher"], research_prompt)
            results["research"] = research_result.final_output
            
            # Step 4: Write in matching style
            if status_callback:
                status_callback("✍️ Writing blog post...", 60)
            print("✍️ Writing in matched style...")
            writing_prompt = f"""
            Write a blog post about: {topic}
            
            STYLE GUIDE TO FOLLOW:
            {style_guide}
            
            RESEARCH DATA:
            {research_result.final_output}
            
            REQUIREMENTS: {requirements}
            
            DUPLICATION STATUS: {duplication_status}
            Note: Based on the duplication analysis, ensure your content offers unique value and differentiation.
            
            Write the post to closely match the style and voice of {reference_blog}.
            Use the specific patterns, tone, and techniques identified in the style guide.
            """
            
            writing_result = self._run_agent_safely(self.agents["writer"], writing_prompt)
            results["draft"] = writing_result.final_output
            
            # Step 5: Add internal links
            if status_callback:
                status_callback("🔗 Adding internal links...", 75)
            print("🔗 Adding internal links...")
            linking_prompt = f"""
            Add strategic internal links to this blog post:
            
            BLOG POST CONTENT:
            {writing_result.final_output}
            
            WEBSITE/DOMAIN: {reference_blog}
            
            Instructions:
            1. Search for existing content on {reference_blog} that relates to topics in this post
            2. Add 2-5 relevant internal links using natural anchor text
            3. Focus on links that genuinely help the reader learn more
            4. Use markdown format: [anchor text](URL)
            5. Don't over-link or force unnatural links
            
            Return the blog post with internal links added.
            """
            
            linking_result = self._run_agent_safely(self.agents["internal_linker"], linking_prompt)
            results["with_links"] = linking_result.final_output
            
            # Step 6: Edit while preserving style and links
            if status_callback:
                status_callback("📝 Final editing and polishing...", 90)
            print("📝 Final editing while preserving style and links...")
            editing_prompt = f"""
            Edit this blog post while preserving the {reference_blog} style and internal links:
            
            ORIGINAL STYLE GUIDE:
            {style_guide}
            
            DRAFT TO EDIT:
            {linking_result.final_output}
            
            Instructions:
            - Improve grammar, flow, and clarity while maintaining the distinctive voice and style patterns
            - PRESERVE all internal links that have been added
            - Ensure the content flows naturally around the linked text
            - Don't remove or modify any [anchor text](URL) formatting
            """
            
            editing_result = self._run_agent_safely(self.agents["editor"], editing_prompt)
            results["final"] = editing_result.final_output
            
            # Step 7: SEO Analysis
            if status_callback:
                status_callback("📊 Analyzing SEO performance...", 95)
            print("📊 Analyzing SEO performance...")
            seo_prompt = f"""
            Analyze this final blog post for SEO best practices and provide actionable recommendations:
            
            BLOG POST TO ANALYZE:
            {editing_result.final_output}
            
            TARGET TOPIC: {topic}
            PUBLICATION STYLE: {reference_blog}
            
            Provide a comprehensive SEO analysis with specific recommendations for improvement.
            """
            
            seo_result = self._run_agent_safely(self.agents["seo_analyzer"], seo_prompt)
            results["seo_analysis"] = seo_result.final_output
            
            if status_callback:
                status_callback("✅ Blog post completed with SEO analysis!", 100)
            
            return results
            
        except Exception as e:
            print(f"❌ Error creating blog post: {e}")
            if status_callback:
                status_callback(f"❌ Error: {str(e)}", 0)
            results["error"] = str(e)
            return results
    
    def parallel_research(self, topic: str, research_areas: List[str]) -> Dict[str, str]:
        """Conduct parallel research on different aspects of a topic."""
        from concurrent.futures import ThreadPoolExecutor
        
        def research_area(area: str) -> str:
            prompt = f"Research specifically about {area} in relation to {topic}"
            result = Runner.run_sync(self.agents["researcher"], prompt)
            return result.final_output
        
        print(f"🔍 Conducting parallel research on {len(research_areas)} areas...")
        
        with ThreadPoolExecutor() as executor:
            futures = {area: executor.submit(research_area, area) for area in research_areas}
            results = {area: future.result() for area, future in futures.items()}
        
        print("✅ Parallel research completed")
        return results
    
    def analyze_blog_style(self, blog_source: str, status_callback=None) -> str:
        """Analyze the writing style of a specified blog or publication."""
        if status_callback:
            status_callback(f"🎨 Fetching articles from {blog_source}...", 15)
        print(f"🎨 Analyzing writing style of {blog_source}...")
        
        style_prompt = f"""
        Analyze the writing style of {blog_source}.
        
        Instructions:
        1. Search for recent articles from {blog_source}
        2. Analyze multiple articles to identify consistent patterns
        3. Extract the publication's distinctive voice and style characteristics
        4. Create a detailed style guide that includes specific examples
        
        Focus on recent articles to capture current writing style.
        """
        
        try:
            if status_callback:
                status_callback("🔍 Analyzing writing patterns...", 25)
            result = self._run_agent_safely(self.agents["style_analyzer"], style_prompt)
            print("✅ Style analysis completed")
            return result.final_output
        except Exception as e:
            print(f"❌ Style analysis failed: {e}")
            return f"Style analysis failed: {e}"
    
    def create_style_matched_post(self, topic: str, reference_blog: str, requirements: str = "") -> Dict[str, str]:
        """Alias for create_blog_post for backward compatibility."""
        return self.create_blog_post(topic, reference_blog, requirements)

def main():
    orchestrator = BlogAgentOrchestrator()
    
    # Example: Create a style-matched blog post
    topic = "The Future of Remote Work"
    blog_source = "YourBlog.com"  # Can be changed to any blog
    requirements = """
    - Target audience: Business professionals
    - Include practical examples
    - Keep under 1500 words
    - Add call-to-action for newsletter signup
    """
    
    print(f"🚀 Creating blog post about: {topic}")
    print(f"📰 Matching style of: {blog_source}")
    print("=" * 50)
    
    # Use the sync style-matched workflow
    results = orchestrator.create_blog_post(topic, blog_source, requirements)
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
        return
    
    print("\n" + "=" * 50)
    print(f"📄 FINAL BLOG POST (in {blog_source} style):")
    print("=" * 50)
    print(results["final"])
    
    print("\n" + "=" * 50)
    print(f"🎨 EXTRACTED STYLE GUIDE from {blog_source}:")
    print("=" * 50)
    print(results["style_guide"][:500] + "..." if len(results["style_guide"]) > 500 else results["style_guide"])

if __name__ == "__main__":
    main()