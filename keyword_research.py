#!/usr/bin/env python3
"""
Keyword research integration for BlogAgents
Supports Google Ads API for keyword data and Google Trends for trend analysis
"""

# Suppress gRPC warnings from Google Ads
import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

import streamlit as st
from typing import List, Dict, Optional
from pytrends.request import TrendReq
import time


class KeywordResearcher:
    """Manages keyword research using Google Ads API and Google Trends"""

    def __init__(self, google_ads_config: Optional[Dict] = None):
        """
        Initialize keyword researcher

        Args:
            google_ads_config: Optional dict with Google Ads API credentials
                {
                    'developer_token': str,
                    'client_id': str,
                    'client_secret': str,
                    'refresh_token': str,
                    'customer_id': str
                }
        """
        self.google_ads_config = google_ads_config
        self.google_ads_client = None

        # Initialize Google Trends (always available)
        self.pytrends = TrendReq(hl='en-US', tz=360)

        # Initialize Google Ads client if config provided
        if google_ads_config:
            self._initialize_google_ads()

    def _initialize_google_ads(self):
        """Initialize Google Ads API client with service account"""
        try:
            from google.ads.googleads.client import GoogleAdsClient
            import json
            import tempfile
            import os

            # Parse service account JSON
            service_account_info = json.loads(self.google_ads_config['service_account_json'])

            # Google Ads API requires a file path, so create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(service_account_info, f)
                temp_file_path = f.name

            try:
                # Create config dict for Google Ads using service account file
                config = {
                    'developer_token': self.google_ads_config['developer_token'],
                    'use_proto_plus': True,
                    'json_key_file_path': temp_file_path,
                    'login_customer_id': self.google_ads_config['customer_id']
                }

                # Initialize client
                self.google_ads_client = GoogleAdsClient.load_from_dict(config)

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        except Exception as e:
            st.warning(f"⚠️ Could not initialize Google Ads API: {str(e)}")
            self.google_ads_client = None

    def get_keyword_ideas(self, seed_keywords: List[str], location: str = "US") -> List[Dict]:
        """
        Get keyword ideas and search volumes from Google Ads API

        Args:
            seed_keywords: List of seed keywords to expand
            location: Geographic location for keyword data

        Returns:
            List of dicts with keyword data
        """
        if not self.google_ads_client:
            return []

        try:
            from google.ads.googleads.client import GoogleAdsClient

            keyword_plan_idea_service = self.google_ads_client.get_service(
                "KeywordPlanIdeaService"
            )

            request = self.google_ads_client.get_type("GenerateKeywordIdeasRequest")
            request.customer_id = self.google_ads_config['customer_id']

            # Set location (US = 2840)
            request.geo_target_constants.append(
                keyword_plan_idea_service.geographic_target_constant_path("2840")
            )

            # Set language (English = 1000)
            request.language = keyword_plan_idea_service.language_constant_path("1000")

            # Add seed keywords
            request.keyword_seed.keywords.extend(seed_keywords)

            # Make request
            response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

            keyword_ideas = []
            for idea in response:
                keyword_ideas.append({
                    'keyword': idea.text,
                    'avg_monthly_searches': idea.keyword_idea_metrics.avg_monthly_searches,
                    'competition': idea.keyword_idea_metrics.competition.name,
                    'competition_index': idea.keyword_idea_metrics.competition_index,
                    'low_top_of_page_bid_micros': idea.keyword_idea_metrics.low_top_of_page_bid_micros,
                    'high_top_of_page_bid_micros': idea.keyword_idea_metrics.high_top_of_page_bid_micros
                })

            return keyword_ideas[:50]  # Limit to top 50

        except Exception as e:
            st.warning(f"⚠️ Google Ads API error: {str(e)}")
            return []

    def get_trend_data(self, keywords: List[str]) -> Dict[str, int]:
        """
        Get Google Trends interest scores for keywords

        Args:
            keywords: List of keywords to check (max 5)

        Returns:
            Dict mapping keyword to trend score (0-100)
        """
        try:
            # Google Trends allows max 5 keywords at once
            keywords_chunk = keywords[:5]

            # Build payload
            self.pytrends.build_payload(
                keywords_chunk,
                cat=0,
                timeframe='today 3-m',
                geo='US',
                gprop=''
            )

            # Get interest over time
            interest_df = self.pytrends.interest_over_time()

            if interest_df.empty:
                return {kw: 0 for kw in keywords_chunk}

            # Calculate average interest for each keyword
            trend_scores = {}
            for keyword in keywords_chunk:
                if keyword in interest_df.columns:
                    trend_scores[keyword] = int(interest_df[keyword].mean())
                else:
                    trend_scores[keyword] = 0

            # Add delay to avoid rate limiting
            time.sleep(1)

            return trend_scores

        except Exception as e:
            st.warning(f"⚠️ Google Trends error: {str(e)}")
            return {kw: 0 for kw in keywords}

    def get_related_queries(self, keyword: str) -> List[str]:
        """
        Get related search queries from Google Trends

        Args:
            keyword: Seed keyword

        Returns:
            List of related query strings
        """
        try:
            self.pytrends.build_payload([keyword], timeframe='today 3-m', geo='US')

            related = self.pytrends.related_queries()

            if keyword not in related or related[keyword]['top'] is None:
                return []

            # Get top 10 related queries
            top_queries = related[keyword]['top']
            if not top_queries.empty:
                return top_queries['query'].head(10).tolist()

            return []

        except Exception as e:
            return []

    def enrich_topics_with_keyword_data(self, topics: List[Dict]) -> List[Dict]:
        """
        Enrich topic suggestions with keyword research data

        Args:
            topics: List of topic dicts with 'title' and 'keywords' fields

        Returns:
            Topics enriched with search volume, competition, and trend data
        """
        for topic in topics:
            keywords = topic.get('keywords', [])

            if not keywords:
                # Extract keywords from title
                keywords = [word.lower() for word in topic['title'].split() if len(word) > 3][:3]
                topic['keywords'] = keywords

            # Get trend data (always available)
            trend_scores = self.get_trend_data(keywords)
            topic['trend_score'] = max(trend_scores.values()) if trend_scores else 0
            topic['trend_status'] = self._get_trend_status(topic['trend_score'])

            # Get keyword data from Google Ads if available
            if self.google_ads_client:
                keyword_ideas = self.get_keyword_ideas(keywords)

                if keyword_ideas:
                    # Use the best keyword data
                    best_keyword = max(keyword_ideas, key=lambda x: x['avg_monthly_searches'])
                    topic['search_volume'] = best_keyword['avg_monthly_searches']
                    topic['competition'] = best_keyword['competition']
                    topic['competition_index'] = best_keyword['competition_index']
                else:
                    topic['search_volume'] = 'N/A'
                    topic['competition'] = 'N/A'
            else:
                # Without Google Ads, provide trend-based estimate
                # Trend score (0-100) can indicate relative interest
                trend_score = topic.get('trend_score', 0)
                if trend_score >= 75:
                    topic['search_volume'] = 'High (trend-based)'
                elif trend_score >= 50:
                    topic['search_volume'] = 'Medium (trend-based)'
                elif trend_score >= 25:
                    topic['search_volume'] = 'Low (trend-based)'
                else:
                    topic['search_volume'] = 'Minimal (trend-based)'
                topic['competition'] = 'Enable Google Ads for data'

        return topics

    def _get_trend_status(self, score: int) -> str:
        """Get trend status emoji based on score"""
        if score >= 75:
            return "🔥 Hot"
        elif score >= 50:
            return "📈 Rising"
        elif score >= 25:
            return "➡️ Steady"
        else:
            return "📉 Low"


def create_keyword_researcher(google_ads_config: Optional[Dict] = None) -> KeywordResearcher:
    """Factory function to create KeywordResearcher with error handling"""
    try:
        return KeywordResearcher(google_ads_config)
    except Exception as e:
        st.error(f"Failed to create keyword researcher: {str(e)}")
        return KeywordResearcher()  # Return without Google Ads config
