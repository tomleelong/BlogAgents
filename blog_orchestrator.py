#!/usr/bin/env python3
from typing import Dict, List
from dotenv import load_dotenv
from agents import Agent, Runner, WebSearchTool

load_dotenv()

class BlogAgentOrchestrator:
    def __init__(self):
        # Specialist agents
        self.agents = {
            "style_analyzer": Agent(
                name="Blog Style Analyzer",
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
            "researcher": Agent(
                name="Research Specialist",
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
                instructions="""You are a skilled blog writer.
                - Create engaging, well-structured blog posts
                - Use provided research effectively
                - Write clear introductions and conclusions
                - Include subheadings and bullet points
                - Maintain conversational but professional tone
                """
            ),
            "editor": Agent(
                name="Content Editor",
                instructions="""You are a content editor.
                - Review content for clarity and flow
                - Fix grammar and style issues
                - Ensure consistent tone throughout
                - Improve readability and engagement
                - Suggest structural improvements
                - Consider SEO and AI visibility
                """
            )
        }
    
    def create_blog_post(self, topic: str, reference_blog: str = "TechCrunch.com", requirements: str = "") -> Dict[str, str]:
        """Create a blog post that matches the style of a reference publication."""
        results = {}
        
        try:
            # Step 1: Analyze reference style
            print(f"🎨 Analyzing {reference_blog} style...")
            style_guide = self.analyze_blog_style(reference_blog)
            results["style_guide"] = style_guide
            
            # Step 2: Research topic
            print("🔍 Researching topic...")
            research_prompt = f"Research the topic: {topic}\n\nRequirements: {requirements}"
            research_result = Runner.run_sync(self.agents["researcher"], research_prompt)
            results["research"] = research_result.final_output
            
            # Step 3: Write in matching style
            print("✍️ Writing in matched style...")
            writing_prompt = f"""
            Write a blog post about: {topic}
            
            STYLE GUIDE TO FOLLOW:
            {style_guide}
            
            RESEARCH DATA:
            {research_result.final_output}
            
            REQUIREMENTS: {requirements}
            
            Write the post to closely match the style and voice of {reference_blog}.
            Use the specific patterns, tone, and techniques identified in the style guide.
            """
            
            writing_result = Runner.run_sync(self.agents["writer"], writing_prompt)
            results["draft"] = writing_result.final_output
            
            # Step 4: Edit while preserving style
            print("📝 Editing while preserving style...")
            editing_prompt = f"""
            Edit this blog post while preserving the {reference_blog} style:
            
            ORIGINAL STYLE GUIDE:
            {style_guide}
            
            DRAFT TO EDIT:
            {writing_result.final_output}
            
            Improve grammar, flow, and clarity while maintaining the distinctive voice and style patterns.
            """
            
            editing_result = Runner.run_sync(self.agents["editor"], editing_prompt)
            results["final"] = editing_result.final_output
            
            return results
            
        except Exception as e:
            print(f"❌ Error creating blog post: {e}")
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
    
    def analyze_blog_style(self, blog_source: str = "TechCrunch.com") -> str:
        """Analyze the writing style of a specified blog or publication."""
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
            result = Runner.run_sync(self.agents["style_analyzer"], style_prompt)
            print("✅ Style analysis completed")
            return result.final_output
        except Exception as e:
            print(f"❌ Style analysis failed: {e}")
            return f"Style analysis failed: {e}"
    
    def create_style_matched_post(self, topic: str, reference_blog: str = "TechCrunch.com", requirements: str = "") -> Dict[str, str]:
        """Alias for create_blog_post for backward compatibility."""
        return self.create_blog_post(topic, reference_blog, requirements)

def main():
    orchestrator = BlogAgentOrchestrator()
    
    # Example: Create a style-matched blog post
    topic = "Electric bikes in the US"
    blog_source = "https://lectricebikes.com/"  # Can be changed to any blog
    requirements = """
    - Target audience: Potential electric bike customers
    - Include a call-to-action for a newsletter signup
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