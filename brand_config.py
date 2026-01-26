#!/usr/bin/env python3
"""
Brand configuration module for Safety Products Global multi-brand blog generation.

Defines brand-specific settings for Slice, Klever, and PHC brands including
style sources, product catalogs, keywords, and brand voice characteristics.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class BrandName(Enum):
    """Enumeration of available brands."""
    SLICE = "slice"
    KLEVER = "klever"
    PHC = "phc"


@dataclass
class ProductInfo:
    """Information about a brand product for content targeting."""
    name: str
    url: str
    description: str


@dataclass
class BrandConfig:
    """Configuration for a single brand."""

    # Brand identifiers
    name: str
    display_name: str
    primary_domain: str

    # Blog configuration
    blog_url: Optional[str]  # None if no blog exists yet
    rss_feed_url: Optional[str]

    # Style configuration
    style_source_type: str  # "blog", "parent_brand", "manual"
    style_source_url: Optional[str]  # Where to pull style from if not own blog
    fallback_style_guide: Optional[str]  # Manual style guide text for brands without blogs

    # Content targeting
    default_product_categories: List[str] = field(default_factory=list)
    key_products: List[ProductInfo] = field(default_factory=list)
    internal_link_targets: List[str] = field(default_factory=list)

    # SEO and keywords
    primary_keywords: List[str] = field(default_factory=list)
    industry_terms: List[str] = field(default_factory=list)

    # Brand voice characteristics
    tone_keywords: List[str] = field(default_factory=list)
    avoid_terms: List[str] = field(default_factory=list)

    # Company info for content
    company_tagline: str = ""
    value_propositions: List[str] = field(default_factory=list)

    # Visual/branding
    primary_color: str = "#333333"


# Pre-configured brands for Safety Products Global
BRAND_CONFIGS: Dict[str, BrandConfig] = {
    BrandName.SLICE.value: BrandConfig(
        name="slice",
        display_name="Slice",
        primary_domain="sliceproducts.com",
        blog_url="https://blog.sliceproducts.com",
        rss_feed_url="https://blog.sliceproducts.com/rss.xml",
        style_source_type="blog",
        style_source_url="https://blog.sliceproducts.com",
        fallback_style_guide=None,
        default_product_categories=[
            "ceramic blades",
            "safety knives",
            "box cutters",
            "craft knives",
            "utility knives"
        ],
        key_products=[
            # Add products here as needed - minimal structure for now
            # ProductInfo(
            #     name="10558 Smart-Retracting Utility Knife",
            #     url="https://sliceproducts.com/products/...",
            #     description="Auto-retract utility knife with ceramic blade"
            # ),
        ],
        internal_link_targets=[
            "https://sliceproducts.com/collections/",
            "https://sliceproducts.com/pages/",
            "https://blog.sliceproducts.com/"
        ],
        primary_keywords=[
            "ceramic blade",
            "safety knife",
            "finger-friendly blade",
            "safety cutter",
            "ceramic safety blade"
        ],
        industry_terms=[
            "workplace safety",
            "OSHA",
            "cut injuries",
            "ergonomic tools",
            "PPE",
            "hand safety"
        ],
        tone_keywords=["innovative", "safety-conscious", "premium", "professional"],
        avoid_terms=["cheap", "disposable", "basic"],
        company_tagline="The Safer Choice",
        value_propositions=[
            "Ceramic blades last 11x longer than steel",
            "Finger-Friendly blade technology",
            "Award-winning safety design"
        ],
        primary_color="#FF6B35"
    ),

    BrandName.KLEVER.value: BrandConfig(
        name="klever",
        display_name="Klever Innovations",
        primary_domain="kleverinnovations.net",
        blog_url=None,  # No blog yet
        rss_feed_url=None,
        style_source_type="parent_brand",  # Use Slice's style as starting point
        style_source_url="https://blog.sliceproducts.com",
        fallback_style_guide="""
## Klever Innovations Brand Voice Guidelines

### Core Brand Identity
- American-made pride and quality craftsmanship
- Industrial strength and proven durability
- Safety-first engineering philosophy

### Tone & Voice
- Professional and authoritative
- Direct and no-nonsense communication
- Emphasizes reliability, trust, and proven results
- Highlights American manufacturing excellence

### Content Focus Areas
- Concealed blade safety benefits and injury prevention
- American manufacturing quality and standards
- Industrial, warehouse, and distribution center applications
- Cost savings through durability and reduced replacements
- OSHA compliance and workplace safety regulations

### Key Messaging Points
- "Safety is job one"
- Made in USA quality assurance
- Trusted by major brands and corporations
- Proven injury reduction statistics

### Writing Guidelines
- Use data and statistics to support claims
- Include real-world industrial applications
- Reference safety certifications and compliance
- Emphasize long-term value over initial cost
""",
        default_product_categories=[
            "concealed blade cutters",
            "safety cutters",
            "box cutters",
            "disposable cutters",
            "replaceable blade cutters"
        ],
        key_products=[
            # Add products here as needed
        ],
        internal_link_targets=[
            "https://kleverinnovations.net/products/",
            "https://kleverinnovations.net/collections/"
        ],
        primary_keywords=[
            "concealed blade",
            "safety cutter",
            "American made safety knife",
            "industrial cutter",
            "warehouse safety cutter"
        ],
        industry_terms=[
            "warehouse safety",
            "distribution center",
            "packaging",
            "industrial safety",
            "workplace injury prevention",
            "OSHA compliance"
        ],
        tone_keywords=["American-made", "durable", "industrial-strength", "reliable", "proven"],
        avoid_terms=["foreign", "imported", "cheap", "flimsy"],
        company_tagline="American Innovation. Proven Safety.",
        value_propositions=[
            "100% American made",
            "Concealed blade technology",
            "Trusted by Fortune 500 companies"
        ],
        primary_color="#1E3A5F"
    ),

    BrandName.PHC.value: BrandConfig(
        name="phc",
        display_name="Pacific Handy Cutter",
        primary_domain="phcsafety.com",
        blog_url=None,  # No blog yet
        rss_feed_url=None,
        style_source_type="parent_brand",
        style_source_url="https://blog.sliceproducts.com",
        fallback_style_guide="""
## Pacific Handy Cutter Brand Voice Guidelines

### Core Brand Identity
- Industry-leading safety innovation
- Multi-functional versatility
- Professional-grade quality and reliability
- Market leadership in grocery and retail

### Tone & Voice
- Expert and knowledgeable
- Solution-oriented approach
- Safety-focused messaging
- Data-driven credibility

### Content Focus Areas
- Multi-tool capabilities and versatility
- Safety certifications and compliance standards
- Industry-specific applications (grocery, retail, foodservice)
- ROI and cost-benefit analysis of safety investments
- Injury reduction statistics and case studies

### Key Messaging Points
- 80% market share among U.S. grocery/retail stores
- Trusted by Walmart, Kroger, Albertsons, Walgreens
- Laceration injuries cost employers $46,000 per injury
- 70-85% injury reduction rates documented

### Writing Guidelines
- Lead with safety ROI and business impact
- Include customer testimonials and case studies
- Reference specific industry applications
- Emphasize professional training and support services
- Highlight market leadership and proven track record
""",
        default_product_categories=[
            "safety knives",
            "utility knives",
            "concealed cutters",
            "bladeless cutters",
            "rescue tools"
        ],
        key_products=[
            # Add products here as needed
        ],
        internal_link_targets=[
            "https://phcsafety.com/products/",
            "https://phcsafety.com/collections/"
        ],
        primary_keywords=[
            "safety knife",
            "multi-function cutter",
            "rescue tool",
            "smart retract knife",
            "auto retract safety knife"
        ],
        industry_terms=[
            "grocery safety",
            "retail safety",
            "foodservice safety",
            "emergency response",
            "safety compliance",
            "workplace injury prevention"
        ],
        tone_keywords=["versatile", "professional-grade", "safety-certified", "market-leading", "trusted"],
        avoid_terms=["amateur", "basic", "unproven"],
        company_tagline="Safety by Design",
        value_propositions=[
            "80% market share in grocery/retail",
            "Multi-functional design",
            "Industry-leading safety features",
            "Proven 70-85% injury reduction"
        ],
        primary_color="#2D5DA8"
    )
}


def get_brand_config(brand_name: str) -> Optional[BrandConfig]:
    """
    Get configuration for a specific brand.

    Args:
        brand_name: Brand identifier (slice, klever, phc)

    Returns:
        BrandConfig object or None if not found
    """
    return BRAND_CONFIGS.get(brand_name.lower())


def get_all_brands() -> List[BrandConfig]:
    """
    Get all configured brands.

    Returns:
        List of BrandConfig objects
    """
    return list(BRAND_CONFIGS.values())


def get_brand_names() -> List[str]:
    """
    Get list of brand name identifiers.

    Returns:
        List of brand name strings
    """
    return list(BRAND_CONFIGS.keys())


def get_effective_style_source(brand_config: BrandConfig) -> str:
    """
    Get the effective style source URL for a brand.

    For brands with their own blog, returns the blog URL.
    For brands without blogs, returns the parent brand's style source.

    Args:
        brand_config: Brand configuration object

    Returns:
        URL string for style analysis
    """
    if brand_config.blog_url:
        return brand_config.blog_url
    return brand_config.style_source_url or ""


def build_brand_context_prompt(brand_config: BrandConfig) -> str:
    """
    Build a brand context string for AI agent prompts.

    Args:
        brand_config: Brand configuration object

    Returns:
        Formatted string with brand context for prompts
    """
    return f"""
BRAND CONTEXT:
- Brand: {brand_config.display_name}
- Domain: {brand_config.primary_domain}
- Tagline: {brand_config.company_tagline}
- Key Value Propositions: {', '.join(brand_config.value_propositions)}
- Brand Tone: {', '.join(brand_config.tone_keywords)}
- Primary Keywords: {', '.join(brand_config.primary_keywords)}
- Industry Terms: {', '.join(brand_config.industry_terms)}
- Terms to Avoid: {', '.join(brand_config.avoid_terms)}
"""
