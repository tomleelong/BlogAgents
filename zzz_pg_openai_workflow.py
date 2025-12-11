import { webSearchTool, RunContext, Agent, AgentInputItem, Runner, withTrace } from "@openai/agents";
import { z } from "zod";


// Tool definitions
const webSearchPreview = webSearchTool({
  searchContextSize: "medium",
  userLocation: {
    type: "approximate"
  }
})
const WritingStyleSchema = z.object({ writing_style_output: z.string() });
const TextToJsonSchema = z.object({ existing_blog_posts_to_avoid: z.array(z.string()), high_performing_pages: z.array(z.string()), root_blog_url: z.string(), seo_keywords: z.array(z.string()), target_product_urls: z.array(z.string()), topics: z.array(z.string()), writing_requirements: z.string() });
const ResearchSchema = z.object({ research_output: z.string() });
const WriterSchema = z.object({ writer_output: z.string() });
const SeoAnalyzerSchema = z.object({ seo_analzyer_first_pass_output: z.string() });
const InternalLinksSchema = z.object({ internal_links_output: z.string() });
interface WritingStyleContext {
  stateRootBlogUrl: string;
  stateHighPerformingPages: string;
}
const writingStyleInstructions = (runContext: RunContext<WritingStyleContext>, _agent: Agent<WritingStyleContext>) => {
  const { stateRootBlogUrl, stateHighPerformingPages } = runContext.context;
  return `Analyze the writing style of ${stateRootBlogUrl}.

PRIORITY: Analyze these specific high-performing posts first:
${stateHighPerformingPages}

These pages should be the PRIMARY examples in your style guide.

Instructions:
1. Search for recent articles from ${stateRootBlogUrl}
2. If specific pages were provided above, analyze those FIRST and prioritize their patterns
3. Analyze multiple articles to identify consistent patterns
4. Extract the publication's distinctive voice and style characteristics
5. Create a detailed style guide that includes specific examples

Focus on recent articles to capture current writing style. `
}
const writingStyle = new Agent({
  name: "Writing Style",
  instructions: writingStyleInstructions,
  model: "gpt-5.1",
  tools: [
    webSearchPreview
  ],
  outputType: WritingStyleSchema,
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

interface TextToJsonContext {
  workflowInputAsText: string;
}
const textToJsonInstructions = (runContext: RunContext<TextToJsonContext>, _agent: Agent<TextToJsonContext>) => {
  const { workflowInputAsText } = runContext.context;
  return `transform the following to json:
 ${workflowInputAsText}`
}
const textToJson = new Agent({
  name: "text_to_json",
  instructions: textToJsonInstructions,
  model: "gpt-5.1",
  outputType: TextToJsonSchema,
  modelSettings: {
    reasoning: {
      effort: "low",
      summary: "auto"
    },
    store: true
  }
});

interface ResearchContext {
  stateTopics: string;
  stateWritingRequirements: string;
  stateTargetProductUrls: string;
}
const researchInstructions = (runContext: RunContext<ResearchContext>, _agent: Agent<ResearchContext>) => {
  const { stateTopics, stateWritingRequirements, stateTargetProductUrls } = runContext.context;
  return `Research the topic: ${stateTopics}

Requirements:
${stateWritingRequirements}

PRODUCT/PAGE TO PROMOTE: 
${stateTargetProductUrls}                 

Focus your research on:                                     
- Recent developments or trends in this area                
- Facts, statistics, and examples                            
- Unique insights and perspectives
- Practical, actionable information`
}
const research = new Agent({
  name: "Research",
  instructions: researchInstructions,
  model: "gpt-5.1",
  tools: [
    webSearchPreview
  ],
  outputType: ResearchSchema,
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

interface WriterContext {
  stateTopics: string;
  stateWritingStyle: string;
  stateResearch: string;
  stateWritingRequirements: string;
  stateRootBlogUrl: string;
}
const writerInstructions = (runContext: RunContext<WriterContext>, _agent: Agent<WriterContext>) => {
  const { stateTopics, stateWritingStyle, stateResearch, stateWritingRequirements, stateRootBlogUrl } = runContext.context;
  return `Write a blog post about: ${stateTopics}

STYLE GUIDE TO FOLLOW (including formatting patterns):
${stateWritingStyle}

RESEARCH DATA:
${stateResearch}

REQUIREMENTS: 
${stateWritingRequirements}

CRITICAL FORMATTING INSTRUCTIONS:
1. Write the post to closely match the style and voice of ${stateRootBlogUrl}
2. Use the specific patterns, tone, and techniques identified in the style guide
3. Pay special attention to the FORMATTING GUIDE section - match their heading structure, list usage, and emphasis patterns
4. Output the content in proper markdown format that will render correctly
5. Use the same heading hierarchy (H2, H3, etc.) as shown in the style guide examples
6. Follow their bullet point vs. numbered list preferences
7. Apply bold/italic emphasis in the same way they do

The final output should be properly formatted markdown that matches both the writing style AND visual formatting of ${stateRootBlogUrl}`
}
const writer = new Agent({
  name: "Writer",
  instructions: writerInstructions,
  model: "gpt-5.1",
  tools: [
    webSearchPreview
  ],
  outputType: WriterSchema,
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

interface SeoAnalyzerContext {
  stateWriterDraft: string;
  stateTopics: string;
  stateRootBlogUrl: string;
}
const seoAnalyzerInstructions = (runContext: RunContext<SeoAnalyzerContext>, _agent: Agent<SeoAnalyzerContext>) => {
  const { stateWriterDraft, stateTopics, stateRootBlogUrl } = runContext.context;
  return `Analyze this blog post draft for SEO optimization opportunities:

BLOG POST DRAFT:
${stateWriterDraft}

TARGET TOPIC: ${stateTopics}
PUBLICATION STYLE: ${stateRootBlogUrl}

Provide specific, actionable SEO recommendations for:
1. Heading structure and keyword optimization
2. Content improvements for better search visibility
3. Strategic internal linking opportunities 
4. Meta description suggestions
5. Readability and structure enhancements

Focus on recommendations that can be implemented in the editing phase.`
}
const seoAnalyzer = new Agent({
  name: "SEO Analyzer",
  instructions: seoAnalyzerInstructions,
  model: "gpt-5.1",
  tools: [
    webSearchPreview
  ],
  outputType: SeoAnalyzerSchema,
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

interface InternalLinksContext {
  stateWriterDraft: string;
  stateResponseSchemaRootBlogUrl: string;
  stateSeoAnalyzeFirstPass: string;
  stateResponseSchemaTopic: string;
}
const internalLinksInstructions = (runContext: RunContext<InternalLinksContext>, _agent: Agent<InternalLinksContext>) => {
  const { stateWriterDraft, stateResponseSchemaRootBlogUrl, stateSeoAnalyzeFirstPass, stateResponseSchemaTopic } = runContext.context;
  return `Add strategic internal links to this blog post:

BLOG POST CONTENT:
${stateWriterDraft}

WEBSITE/DOMAIN: 
${stateResponseSchemaRootBlogUrl}

SEO RECOMMENDATIONS TO CONSIDER:
${stateSeoAnalyzeFirstPass}

CRITICAL Instructions:
1. Use WebSearchTool to search for existing content on ${stateResponseSchemaRootBlogUrl} that relates to topics in this post
2. Use search queries like: \"site:${stateResponseSchemaRootBlogUrl} [${stateResponseSchemaTopic}]\" to find specific pages
3. ONLY use URLs that you find in actual search results - never guess or construct URLs
4. For each link you want to add:
  - Search for the specific topic using site:${stateResponseSchemaRootBlogUrl} operator
  - Copy the EXACT URL from the search result
  - Use that exact URL in your markdown link
5. Add 2-5 relevant internal links using natural anchor text (if found)
6. If you cannot find relevant pages via search, it's better to not add a link
7. Use markdown format: [anchor text](EXACT_URL_FROM_SEARCH)
8. Each link MUST be verified through search - no exceptions

Return the blog post with ONLY verified internal links added.  `
}
const internalLinks = new Agent({
  name: "Internal Links",
  instructions: internalLinksInstructions,
  model: "gpt-5.1",
  tools: [
    webSearchPreview
  ],
  outputType: InternalLinksSchema,
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

interface EditorContext {
  stateRootBlogUrl: string;
  stateWritingStyle: string;
  inputOutputParsedInternalLinksOutput: string;
  stateSeoAnalyzeFirstPass: string;
}
const editorInstructions = (runContext: RunContext<EditorContext>, _agent: Agent<EditorContext>) => {
  const { stateRootBlogUrl, stateWritingStyle, inputOutputParsedInternalLinksOutput, stateSeoAnalyzeFirstPass } = runContext.context;
  return `Edit this blog post while preserving the ${stateRootBlogUrl} style and internal links:

ORIGINAL STYLE GUIDE:
${stateWritingStyle}

DRAFT TO EDIT:
${inputOutputParsedInternalLinksOutput}

SEO RECOMMENDATIONS TO IMPLEMENT:
${stateSeoAnalyzeFirstPass}

Instructions:
- Improve grammar, flow, and clarity while maintaining the distinctive voice and style patterns
- PRESERVE all internal links that have been added
- Implement SEO recommendations where they don't conflict with style preservation
- Optimize headings, keywords, and content structure based on SEO analysis
  - Ensure the content flows naturally around the linked text
  - Don't remove or modify any [anchor text](URL) formatting
  - Balance SEO optimization with authentic brand voice

Return your output as markdown format`
}
const editor = new Agent({
  name: "Editor",
  instructions: editorInstructions,
  model: "gpt-5.1",
  tools: [
    webSearchPreview
  ],
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

type WorkflowInput = { input_as_text: string };


// Main code entrypoint
export const runWorkflow = async (workflow: WorkflowInput) => {
  return await withTrace("blog_agent", async () => {
    const state = {
      response_schema: {
        existing_blog_posts_to_avoid: [],
        high_performing_pages: [],
        root_blog_url: "",
        seo_keywords: [],
        target_product_urls: [],
        topic: ""
      },
      global: {
        existing_blog_posts_to_avoid: [],
        high_performing_pages: [],
        root_blog_url: "",
        seo_keywords: [],
        target_product_urls: [],
        topic: ""
      },
      existing_blog_posts_to_avoid: [],
      high_performing_pages: [],
      root_blog_url: null,
      seo_keywords: [],
      target_product_urls: [],
      topics: [],
      writing_style: null,
      writing_requirements: null,
      research: null,
      writer_draft: null,
      seo_analyze_first_pass: null,
      internal_links: null,
      edit_output: null
    };
    const conversationHistory: AgentInputItem[] = [
      { role: "user", content: [{ type: "input_text", text: workflow.input_as_text }] }
    ];
    const runner = new Runner({
      traceMetadata: {
        __trace_source__: "agent-builder",
        workflow_id: "wf_692e0fdc02508190b3b51b94f2b7deea0f87a40e1a3b5c93"
      }
    });
    const textToJsonResultTemp = await runner.run(
      textToJson,
      [
        ...conversationHistory
      ],
      {
        context: {
          workflowInputAsText: workflow.input_as_text
        }
      }
    );

    if (!textToJsonResultTemp.finalOutput) {
        throw new Error("Agent result is undefined");
    }

    const textToJsonResult = {
      output_text: JSON.stringify(textToJsonResultTemp.finalOutput),
      output_parsed: textToJsonResultTemp.finalOutput
    };
    state.existing_blog_posts_to_avoid = textToJsonResult.output_parsed.existing_blog_posts_to_avoid;
    state.high_performing_pages = textToJsonResult.output_parsed.high_performing_pages;
    state.root_blog_url = textToJsonResult.output_parsed.root_blog_url;
    state.seo_keywords = textToJsonResult.output_parsed.seo_keywords;
    state.target_product_urls = textToJsonResult.output_parsed.target_product_urls;
    state.topics = textToJsonResult.output_parsed.topics;
    state.writing_requirements = textToJsonResult.output_parsed.writing_requirements;
    const writingStyleResultTemp = await runner.run(
      writingStyle,
      [
        ...conversationHistory
      ],
      {
        context: {
          stateRootBlogUrl: state.root_blog_url,
          stateHighPerformingPages: state.high_performing_pages
        }
      }
    );

    if (!writingStyleResultTemp.finalOutput) {
        throw new Error("Agent result is undefined");
    }

    const writingStyleResult = {
      output_text: JSON.stringify(writingStyleResultTemp.finalOutput),
      output_parsed: writingStyleResultTemp.finalOutput
    };
    state.writing_style = writingStyleResult.output_parsed.writing_style_output;
    const researchResultTemp = await runner.run(
      research,
      [
        ...conversationHistory
      ],
      {
        context: {
          stateTopics: state.topics,
          stateWritingRequirements: state.writing_requirements,
          stateTargetProductUrls: state.target_product_urls
        }
      }
    );

    if (!researchResultTemp.finalOutput) {
        throw new Error("Agent result is undefined");
    }

    const researchResult = {
      output_text: JSON.stringify(researchResultTemp.finalOutput),
      output_parsed: researchResultTemp.finalOutput
    };
    state.research = researchResult.output_parsed.research_output;
    const writerResultTemp = await runner.run(
      writer,
      [
        ...conversationHistory
      ],
      {
        context: {
          stateTopics: state.topics,
          stateWritingStyle: state.writing_style,
          stateResearch: state.research,
          stateWritingRequirements: state.writing_requirements,
          stateRootBlogUrl: state.root_blog_url
        }
      }
    );

    if (!writerResultTemp.finalOutput) {
        throw new Error("Agent result is undefined");
    }

    const writerResult = {
      output_text: JSON.stringify(writerResultTemp.finalOutput),
      output_parsed: writerResultTemp.finalOutput
    };
    state.writer_draft = writerResult.output_parsed.writer_output;
    const seoAnalyzerResultTemp = await runner.run(
      seoAnalyzer,
      [
        ...conversationHistory
      ],
      {
        context: {
          stateWriterDraft: state.writer_draft,
          stateTopics: state.topics,
          stateRootBlogUrl: state.root_blog_url
        }
      }
    );

    if (!seoAnalyzerResultTemp.finalOutput) {
        throw new Error("Agent result is undefined");
    }

    const seoAnalyzerResult = {
      output_text: JSON.stringify(seoAnalyzerResultTemp.finalOutput),
      output_parsed: seoAnalyzerResultTemp.finalOutput
    };
    state.seo_analyze_first_pass = seoAnalyzerResult.output_parsed.seo_analzyer_first_pass_output;
    const internalLinksResultTemp = await runner.run(
      internalLinks,
      [
        ...conversationHistory
      ],
      {
        context: {
          stateWriterDraft: state.writer_draft,
          stateResponseSchemaRootBlogUrl: state.response_schema.root_blog_url,
          stateSeoAnalyzeFirstPass: state.seo_analyze_first_pass,
          stateResponseSchemaTopic: state.response_schema.topic
        }
      }
    );

    if (!internalLinksResultTemp.finalOutput) {
        throw new Error("Agent result is undefined");
    }

    const internalLinksResult = {
      output_text: JSON.stringify(internalLinksResultTemp.finalOutput),
      output_parsed: internalLinksResultTemp.finalOutput
    };
    state.internal_links = internalLinksResult.output_parsed.internal_links_output;
    const editorResultTemp = await runner.run(
      editor,
      [
        ...conversationHistory
      ],
      {
        context: {
          stateRootBlogUrl: state.root_blog_url,
          stateWritingStyle: state.writing_style,
          inputOutputParsedInternalLinksOutput: internalLinksResult.output_parsed.internal_links_output,
          stateSeoAnalyzeFirstPass: state.seo_analyze_first_pass
        }
      }
    );

    if (!editorResultTemp.finalOutput) {
        throw new Error("Agent result is undefined");
    }

    const editorResult = {
      output_text: editorResultTemp.finalOutput ?? ""
    };
  });
}
