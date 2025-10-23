#!/usr/bin/env python3
import asyncio
import threading
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dotenv import load_dotenv
from agents import Agent, Runner, WebSearchTool

load_dotenv()

class BlogAgentOrchestrator:
    def __init__(self, model="gpt-5"):
        # Store the model for all agents
        self.model = model
        
        # Thread pool for agent execution (prevents resource leaks)
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent-")
        
        # Specialist agents
        self.agents = {
            "topic_generator": Agent(
                name="Topic Idea Generator",
                model=self.model,
                instructions="""You are a topic idea generator for blog content.

                Your tasks:
                1. Analyze the reference blog/website to understand their content strategy
                2. Identify content gaps and opportunities
                3. Consider trending topics in their industry
                4. Generate specific, actionable topic ideas that match their style

                For each topic idea, provide:
                - **Title**: Compelling headline in the blog's style
                - **Angle**: Unique perspective or approach
                - **Keywords**: 3-5 relevant keywords for SEO
                - **Rationale**: Why this topic would work for their audience
                - **Content Type**: (Guide, Tutorial, Listicle, Case Study, etc.)

                Generate 8-10 diverse topic ideas that:
                - Match the blog's content style and tone
                - Fill gaps in their existing content
                - Appeal to their target audience
                - Have SEO potential
                - Are specific and actionable

                Format each idea clearly with all fields included.
                """,
                tools=[WebSearchTool()]
            ),
            "style_analyzer": Agent(
                name="Blog Style Analyzer",
                model=self.model,
                instructions="""You are a writing style analyzer that can analyze any blog or publication.

                Your tasks:
                1. Use web search to fetch recent articles from the specified blog/publication: {blog_source}
                2. Analyze their writing style, tone, voice patterns, and formatting structure
                3. Extract key stylistic elements including:
                   - Headlines: structure, length, power words, formatting (H1, H2, H3)
                   - Opening paragraphs: hook techniques, information density
                   - Voice: tone characteristics and personality
                   - Technical language: complexity level and jargon usage
                   - Sentence structure: variety, length patterns, rhythm
                   - Common phrases, vocabulary, and expressions
                   - Paragraph organization and flow
                   - Typical post length
                   - FORMATTING PATTERNS: How they structure content with:
                     * Heading hierarchy (H2, H3, H4 usage)
                     * List formatting (bullet points, numbered lists)
                     * Text emphasis (bold, italic usage patterns)
                     * Paragraph lengths and breaks
                     * Call-out boxes, quotes, or special formatting
                     * Code blocks or technical formatting (if applicable)
                4. Create actionable style guidelines for writers to replicate

                Include a specific FORMATTING GUIDE section with:
                - Markdown formatting patterns they use
                - Heading structure preferences
                - List and emphasis usage patterns
                - How they break up content visually

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
                instructions="""You are a skilled blog writer who creates content in proper markdown format.

                CRITICAL MARKDOWN FORMATTING REQUIREMENTS:
                1. Use proper heading hierarchy:
                   - Main title: # Title
                   - Major sections: ## Section Title
                   - Subsections: ### Subsection Title

                2. Format lists correctly:
                   - Bullet lists: - Item or * Item
                   - Numbered lists: 1. Item, 2. Item
                   - Sub-items: Use proper indentation with spaces

                3. Use text emphasis:
                   - Bold: **important text**
                   - Italic: *emphasized text*

                4. Structure content properly:
                   - Blank lines between paragraphs
                   - Blank lines before and after headings
                   - Blank lines before and after lists

                5. Follow the style guide's formatting patterns exactly

                EXAMPLE PROPER MARKDOWN STRUCTURE:
                # Main Title

                Introduction paragraph with **key points** highlighted.

                ## Major Section

                Content paragraph explaining the section.

                ### Subsection

                - First bullet point
                - Second bullet point with **emphasis**
                - Third point

                Another paragraph continuing the discussion.

                ## Next Major Section

                1. Numbered item one
                2. Numbered item two
                3. Numbered item three

                Your tasks:
                - Create engaging, well-structured blog posts using PROPER markdown formatting
                - Use provided research effectively
                - Write clear introductions and conclusions
                - Follow the specific formatting patterns from the style guide
                - Maintain conversational but professional tone
                - ALWAYS use proper markdown syntax as shown in the example above
                """
            ),
            "internal_linker": Agent(
                name="Internal Linking Specialist",
                model=self.model,
                instructions="""You are an internal linking specialist for blog content.

                Your tasks:
                1. Analyze the blog post content for internal linking opportunities
                2. Identify keywords and phrases that could link to other relevant content
                3. Search for related articles on the same website/domain using WebSearchTool
                4. ONLY use URLs that you find directly from search results - do not construct or guess URLs
                5. Verify each link by ensuring it appears in actual search results
                6. Add strategic internal links using natural anchor text

                CRITICAL Guidelines:
                - ONLY use URLs that appear in your WebSearchTool search results
                - DO NOT create, construct, or guess any URLs
                - Each link must be from an actual page you found via search
                - Include the full URL exactly as it appears in search results
                - If you cannot find relevant pages via search, do not add links
                - Use natural, contextual anchor text (avoid "click here")
                - Link to genuinely relevant and helpful content
                - Don't over-link (2-5 internal links per 1000 words is optimal)
                - Prioritize links that add value to the reader
                - Use varied anchor text for similar topics
                - Link to both newer and evergreen content when appropriate
                - Prioritize collections pages and blog posts over pdps

                Format: Use markdown [anchor text](EXACT_URL_FROM_SEARCH)
                If unsure about a link, leave it out rather than guessing.

                Return the content with ONLY verified internal links added.
                """,
                tools=[WebSearchTool()]
            ),
            "editor": Agent(
                name="Content Editor",
                model=self.model,
                instructions="""You are a content editor specializing in markdown-formatted content.

                CRITICAL MARKDOWN EDITING REQUIREMENTS:
                1. PRESERVE and IMPROVE markdown formatting:
                   - Keep all heading hierarchy (# ## ###)
                   - Maintain proper list formatting (- * 1.)
                   - Preserve text emphasis (**bold**, *italic*)
                   - Ensure blank lines between sections

                2. FIX any broken markdown:
                   - Add missing # symbols for headings
                   - Fix inconsistent list formatting
                   - Add proper line breaks and spacing
                   - Ensure proper markdown structure

                3. Content improvements:
                   - Review content for clarity and flow
                   - Fix grammar and style issues
                   - Ensure consistent tone throughout
                   - Improve readability and engagement
                   - Suggest structural improvements
                   - Consider SEO and AI visibility
                   - Preserve any internal links that have been added

                EXAMPLE OF PROPER MARKDOWN STRUCTURE TO MAINTAIN:
                # Main Title

                Introduction paragraph.

                ## Major Section

                Content with **important points** highlighted.

                ### Subsection

                - Bullet point one
                - Bullet point two
                - Bullet point three

                More content here.

                Your output must be properly formatted markdown that renders correctly in Streamlit.
                If the input markdown is poorly formatted, FIX IT while preserving the content.
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
        """Execute agent in isolated thread to prevent Streamlit async conflicts."""
        
        def run_in_thread():
            """Run agent with its own event loop in separate thread."""
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

    def create_blog_post(self, topic: str, reference_blog: str, requirements: str = "", status_callback=None, cached_style_guide: str = None, product_target: str = None, specific_pages: List[str] = None) -> Dict[str, str]:
        """Main workflow: orchestrates all 7 agents to create style-matched blog post."""
        results = {}

        # Add product target to requirements if provided
        if product_target:
            product_instruction = f"\n\nIMPORTANT - PRODUCT/PAGE TO PROMOTE:\n{product_target}\n\nNaturally incorporate mentions of this product/page where relevant. Provide value first, then subtly position the product as a helpful solution. Include a link if a URL was provided."
            requirements = requirements + product_instruction if requirements else product_instruction

        try:
            # Step 1: Analyze reference style (or use cached)
            if cached_style_guide:
                if status_callback:
                    status_callback("📋 Using cached style guide...", 15)
                print(f"📋 Using cached style guide for {reference_blog}")
                style_guide = cached_style_guide
            else:
                if status_callback:
                    status_callback("🎨 Analyzing blog style...", 10)
                print(f"🎨 Analyzing {reference_blog} style...")
                style_guide = self.analyze_blog_style(reference_blog, status_callback, specific_pages)

            results["style_guide"] = style_guide
            
            # Step 2: Research topic (duplication check moved to topic generation phase)
            if status_callback:
                status_callback("🔍 Researching topic...", 45)
            print("🔍 Researching topic...")
            research_prompt = f"""
            Research the topic: {topic}

            Requirements: {requirements}

            Focus your research on:
            - Recent developments or trends in this area
            - Facts, statistics, and examples
            - Unique insights and perspectives
            - Practical, actionable information
            """
            research_result = self._run_agent_safely(self.agents["researcher"], research_prompt)
            results["research"] = research_result.final_output
            
            # Step 4: Write in matching style
            if status_callback:
                status_callback("✍️ Writing blog post...", 60)
            print("✍️ Writing in matched style...")
            writing_prompt = f"""
            Write a blog post about: {topic}

            STYLE GUIDE TO FOLLOW (including formatting patterns):
            {style_guide}

            RESEARCH DATA:
            {research_result.final_output}

            REQUIREMENTS: {requirements}

            CRITICAL FORMATTING INSTRUCTIONS:
            1. Write the post to closely match the style and voice of {reference_blog}
            2. Use the specific patterns, tone, and techniques identified in the style guide
            3. Pay special attention to the FORMATTING GUIDE section - match their heading structure, list usage, and emphasis patterns
            4. Output the content in proper markdown format that will render correctly
            5. Use the same heading hierarchy (H2, H3, etc.) as shown in the style guide examples
            6. Follow their bullet point vs. numbered list preferences
            7. Apply bold/italic emphasis in the same way they do

            The final output should be properly formatted markdown that matches both the writing style AND visual formatting of {reference_blog}.
            """
            
            writing_result = self._run_agent_safely(self.agents["writer"], writing_prompt)
            results["draft"] = writing_result.final_output
            
            # Step 5: SEO Analysis of draft for optimization recommendations  
            if status_callback:
                status_callback("📊 Analyzing draft for SEO optimization...", 65)
            print("📊 Analyzing draft for SEO recommendations...")
            initial_seo_prompt = f"""
            Analyze this blog post draft for SEO optimization opportunities:
            
            BLOG POST DRAFT:
            {writing_result.final_output}
            
            TARGET TOPIC: {topic}
            PUBLICATION STYLE: {reference_blog}
            
            Provide specific, actionable SEO recommendations for:
            1. Heading structure and keyword optimization
            2. Content improvements for better search visibility
            3. Strategic internal linking opportunities 
            4. Meta description suggestions
            5. Readability and structure enhancements
            
            Focus on recommendations that can be implemented in the editing phase.
            """
            
            try:
                initial_seo_result = self._run_agent_safely(self.agents["seo_analyzer"], initial_seo_prompt)
                results["initial_seo_analysis"] = initial_seo_result.final_output
                print(f"✅ Initial SEO analysis completed: {len(results['initial_seo_analysis'])} characters")
            except Exception as e:
                print(f"❌ Initial SEO analysis failed: {e}")
                results["initial_seo_analysis"] = f"Initial SEO analysis failed: {str(e)}"
            
            # Step 6: Add internal links (with SEO insights)
            if status_callback:
                status_callback("🔗 Adding strategic internal links...", 75)
            print("🔗 Adding internal links with SEO optimization...")
            linking_prompt = f"""
            Add strategic internal links to this blog post:

            BLOG POST CONTENT:
            {writing_result.final_output}

            WEBSITE/DOMAIN: {reference_blog}

            SEO RECOMMENDATIONS TO CONSIDER:
            {results.get("initial_seo_analysis", "No SEO recommendations available")}

            CRITICAL Instructions:
            1. Use WebSearchTool to search for existing content on {reference_blog} that relates to topics in this post
            2. Use search queries like: "site:{reference_blog} [topic]" to find specific pages
            3. ONLY use URLs that you find in actual search results - never guess or construct URLs
            4. For each link you want to add:
               - Search for the specific topic using site:{reference_blog} operator
               - Copy the EXACT URL from the search result
               - Use that exact URL in your markdown link
            5. Add 2-5 relevant internal links using natural anchor text (if found)
            6. If you cannot find relevant pages via search, it's better to not add a link
            7. Use markdown format: [anchor text](EXACT_URL_FROM_SEARCH)
            8. Each link MUST be verified through search - no exceptions

            Return the blog post with ONLY verified internal links added.
            """
            
            linking_result = self._run_agent_safely(self.agents["internal_linker"], linking_prompt)
            results["with_links"] = linking_result.final_output
            
            # Step 7: Edit with SEO optimization while preserving style and links
            if status_callback:
                status_callback("📝 Final editing with SEO optimization...", 85)
            print("📝 Final editing with SEO optimization...")
            editing_prompt = f"""
            Edit this blog post while preserving the {reference_blog} style and internal links:
            
            ORIGINAL STYLE GUIDE:
            {results["style_guide"]}
            
            DRAFT TO EDIT:
            {linking_result.final_output}
            
            SEO RECOMMENDATIONS TO IMPLEMENT:
            {results.get("initial_seo_analysis", "No SEO recommendations available")}
            
            Instructions:
            - Improve grammar, flow, and clarity while maintaining the distinctive voice and style patterns
            - PRESERVE all internal links that have been added
            - Implement SEO recommendations where they don't conflict with style preservation
            - Optimize headings, keywords, and content structure based on SEO analysis
            - Ensure the content flows naturally around the linked text
            - Don't remove or modify any [anchor text](URL) formatting
            - Balance SEO optimization with authentic brand voice
            """
            
            editing_result = self._run_agent_safely(self.agents["editor"], editing_prompt)
            results["final"] = editing_result.final_output
            
            # Step 8: Final SEO Analysis and Performance Assessment
            if status_callback:
                status_callback("📊 Final SEO performance analysis...", 95)
            print("📊 Final SEO performance assessment...")
            final_seo_prompt = f"""
            Perform a final SEO analysis of this completed blog post:
            
            FINAL BLOG POST:
            {editing_result.final_output}
            
            ORIGINAL SEO RECOMMENDATIONS:
            {results.get("initial_seo_analysis", "No initial SEO recommendations were available")}
            
            TARGET TOPIC: {topic}
            PUBLICATION STYLE: {reference_blog}
            
            Provide a comprehensive final SEO assessment including:
            1. How well the original recommendations were implemented
            2. Current SEO score and performance analysis  
            3. Any remaining optimization opportunities
            4. Content quality and search visibility assessment
            """
            
            final_seo_result = self._run_agent_safely(self.agents["seo_analyzer"], final_seo_prompt)
            results["seo_analysis"] = final_seo_result.final_output
            
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
        """Unused function for parallel research - not integrated in main workflow."""
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
    
    def analyze_blog_style(self, blog_source: str, status_callback=None, specific_pages: List[str] = None) -> str:
        """Uses style_analyzer agent to extract writing patterns from reference blog."""
        if status_callback:
            status_callback(f"🎨 Fetching articles from {blog_source}...", 15)
        print(f"🎨 Analyzing writing style of {blog_source}...")

        # Build specific pages context
        specific_pages_context = ""
        if specific_pages and len(specific_pages) > 0:
            specific_pages_context = f"""

            PRIORITY: Analyze these specific high-performing posts first:
            {chr(10).join(f"- {page}" for page in specific_pages)}

            These pages should be the PRIMARY examples in your style guide.
            """

        style_prompt = f"""
        Analyze the writing style of {blog_source}.
        {specific_pages_context}

        Instructions:
        1. Search for recent articles from {blog_source}
        2. If specific pages were provided above, analyze those FIRST and prioritize their patterns
        3. Analyze multiple articles to identify consistent patterns
        4. Extract the publication's distinctive voice and style characteristics
        5. Create a detailed style guide that includes specific examples

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
        """Legacy function name - calls create_blog_post internally."""
        return self.create_blog_post(topic, reference_blog, requirements)

    def generate_topic_ideas(self, reference_blog: str, preferences: str = "", status_callback=None, trending_keywords: List[str] = None, product_target: str = None, existing_topics: List[str] = None) -> List[Dict]:
        """
        Generate topic ideas for a blog based on their content strategy and trending keywords

        Args:
            reference_blog: URL of the blog to analyze
            preferences: Optional user preferences (industry, audience, content type)
            status_callback: Optional callback for progress updates
            trending_keywords: Optional list of trending keywords to inform topic generation
            product_target: Optional product/service information to promote naturally
            existing_topics: Optional list of existing blog post titles to avoid duplication

        Returns:
            List of topic idea dicts
        """
        try:
            if status_callback:
                status_callback("💡 Analyzing blog and generating topic ideas...", 50)

            print(f"💡 Generating topic ideas for {reference_blog}...")

            # Build keyword context if provided
            keyword_context = ""
            if trending_keywords:
                keyword_context = f"""

                TRENDING KEYWORDS TO INCORPORATE:
                These keywords are currently trending or have high search volume. Try to build topics around these:
                {', '.join(trending_keywords[:10])}
                """

            # Build product context if provided
            product_context = ""
            if product_target:
                product_context = f"""

                PRODUCT/SERVICE TO PROMOTE:
                {product_target}

                IMPORTANT: Create topics that naturally lead to this product as a solution. The content should provide value first, then subtly position the product as helpful. Avoid being overly promotional.
                """

            # Build existing topics context if provided
            duplication_context = ""
            if existing_topics and len(existing_topics) > 0:
                # Show first 50 topics to avoid token limit
                topics_sample = existing_topics[:50]
                duplication_context = f"""

                EXISTING BLOG POSTS TO AVOID DUPLICATING:
                {chr(10).join(f"- {title}" for title in topics_sample)}
                {f"(and {len(existing_topics) - 50} more...)" if len(existing_topics) > 50 else ""}

                CRITICAL: Do NOT suggest topics that are too similar to these existing posts. Generate completely new angles and subjects.
                """

            prompt = f"""
            Generate 5 topic ideas for the blog: {reference_blog}

            Additional preferences:
            {preferences if preferences else "No specific preferences"}
            {keyword_context}
            {product_context}
            {duplication_context}

            Instructions:
            1. Quickly search {reference_blog} for 3-5 recent articles to understand their style
            2. Generate 5 specific, actionable topic ideas that match their content style
            3. Focus on topics they HAVEN'T covered yet - avoid duplicating the existing topics list above
            4. If trending keywords were provided, prioritize topics that incorporate those high-value keywords
            5. If a product target was provided, create topics that naturally allow mentioning/promoting the product while providing genuine value

            For EACH topic, use this EXACT format:
            ## 1. Compelling Title Here
            - **Angle**: One sentence unique perspective
            - **Keywords**: keyword1, keyword2, keyword3
            - **Rationale**: One sentence why this works
            - **Content Type**: Guide/Tutorial/Listicle/Case Study

            Generate all 5 topics now. Be concise but specific.
            """

            result = self._run_agent_safely(self.agents["topic_generator"], prompt, timeout_seconds=600)  # 10 minutes

            if status_callback:
                status_callback("✅ Topic ideas generated!", 100)

            # Parse the result into structured topics
            topics = self._parse_topic_ideas(result.final_output)

            return topics

        except Exception as e:
            print(f"❌ Error generating topics: {e}")
            if status_callback:
                status_callback(f"❌ Error: {str(e)}", 0)
            return []

    def _parse_topic_ideas(self, raw_output: str) -> List[Dict]:
        """Parse the agent's topic ideas output into structured format"""
        import re

        topics = []
        lines = raw_output.split('\n')

        current_topic = None

        for line in lines:
            line = line.strip()

            # Match topic title (e.g., "## 1. Title Here" or "1. Title Here")
            title_match = re.match(r'^#{0,2}\s*\d+\.\s*(.+)$', line)
            if title_match:
                # Save previous topic
                if current_topic and current_topic.get('title'):
                    topics.append(current_topic)

                # Start new topic
                current_topic = {
                    'title': title_match.group(1).strip(),
                    'angle': '',
                    'keywords': [],
                    'rationale': '',
                    'content_type': ''
                }
                continue

            if not current_topic:
                continue

            # Extract fields
            if line.startswith('- **Angle**:') or line.startswith('**Angle**:'):
                current_topic['angle'] = line.split(':', 1)[1].strip()
            elif line.startswith('- **Keywords**:') or line.startswith('**Keywords**:'):
                keywords_str = line.split(':', 1)[1].strip()
                current_topic['keywords'] = [kw.strip() for kw in keywords_str.split(',')]
            elif line.startswith('- **Rationale**:') or line.startswith('**Rationale**:'):
                current_topic['rationale'] = line.split(':', 1)[1].strip()
            elif line.startswith('- **Content Type**:') or line.startswith('**Content Type**:'):
                current_topic['content_type'] = line.split(':', 1)[1].strip()

        # Don't forget last topic
        if current_topic and current_topic.get('title'):
            topics.append(current_topic)

        return topics

    def extract_blog_topics(self, blog_url: str) -> List[str]:
        """
        Extract all blog post titles from the reference blog

        Args:
            blog_url: URL of the blog (can be RSS feed or blog homepage)

        Returns:
            List of blog post titles
        """
        try:
            print(f"📰 Extracting topics from {blog_url}...")

            prompt = f"""
            Extract all available blog post titles from: {blog_url}

            Instructions:
            1. Fetch the content from this URL
            2. Extract all blog post titles you can find
            3. Return ONLY the titles as a simple list, one per line
            4. No numbering, no formatting, just the title text

            Return format:
            Title 1
            Title 2
            Title 3
            """

            result = self._run_agent_safely(
                self.agents["research"],  # Use research agent with WebSearchTool
                prompt,
                timeout_seconds=120
            )

            # Parse titles from output (one per line)
            titles = []
            for line in result.final_output.split('\n'):
                line = line.strip()
                # Skip empty lines and common header lines
                if line and len(line) > 10:  # Ignore very short lines
                    titles.append(line)

            print(f"✅ Extracted {len(titles)} topics from {blog_url}")
            return titles

        except Exception as e:
            print(f"❌ Error extracting topics: {e}")
            return []

def main():
    """CLI entry point - runs example blog post generation."""
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