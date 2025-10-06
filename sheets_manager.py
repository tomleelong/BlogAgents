#!/usr/bin/env python3
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Optional, Dict, List
import streamlit as st

class SheetsManager:
    """Manages Google Sheets integration for BlogAgents app"""

    def __init__(self, service_account_json: str, spreadsheet_id: str):
        """Initialize with user-provided service account JSON and spreadsheet ID"""
        self.service_account_json = service_account_json
        self.spreadsheet_id = spreadsheet_id
        self.gc = None
        self.spreadsheet = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Google Sheets client with service account credentials"""
        try:
            # Parse service account JSON
            service_account_info = json.loads(self.service_account_json)

            # Define scopes
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            # Create credentials
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=scopes
            )

            # Initialize client
            self.gc = gspread.authorize(credentials)
            self.spreadsheet = self.gc.open_by_key(self.spreadsheet_id)

            # Initialize sheets structure
            self._ensure_sheets_exist()

        except Exception as e:
            raise Exception(f"Failed to initialize Google Sheets client: {str(e)}")

    def _ensure_sheets_exist(self):
        """Create required sheets if they don't exist"""
        required_sheets = {
            'Style_Guides': [
                'Domain', 'Last_Updated', 'Tone', 'Heading_Style',
                'List_Style', 'Style_Guide_Text', 'Analysis_Quality'
            ],
            'Generated_Content': [
                'ID', 'Topic', 'Source_Blog', 'Date_Created', 'Status',
                'Final_Content', 'SEO_Score', 'Word_Count', 'User_Notes'
            ],
            'Blog_Sources': [
                'Domain', 'Category', 'Quality_Rating', 'Last_Analyzed',
                'Success_Count', 'Notes'
            ],
            'Topic_Ideas': [
                'ID', 'Source_Blog', 'Date_Created', 'Title', 'Angle',
                'Keywords', 'Content_Type', 'Rationale', 'Search_Volume',
                'Competition', 'Trend_Score', 'Status', 'Used_Date'
            ]
        }

        existing_sheets = [ws.title for ws in self.spreadsheet.worksheets()]

        for sheet_name, headers in required_sheets.items():
            if sheet_name not in existing_sheets:
                # Create new sheet
                worksheet = self.spreadsheet.add_worksheet(
                    title=sheet_name,
                    rows=1000,
                    cols=len(headers)
                )
                # Add headers
                worksheet.append_row(headers)

    def test_connection(self) -> bool:
        """Test if connection to Google Sheets is working"""
        try:
            # Try to access the spreadsheet
            title = self.spreadsheet.title
            return True
        except Exception as e:
            st.error(f"Sheets connection failed: {str(e)}")
            return False

    def get_cached_style_guide(self, domain: str) -> Optional[Dict]:
        """Get cached style guide for a domain"""
        try:
            worksheet = self.spreadsheet.worksheet('Style_Guides')
            records = worksheet.get_all_records()

            for record in records:
                if record['Domain'].lower() == domain.lower():
                    return {
                        'style_guide': record['Style_Guide_Text'],
                        'last_updated': record['Last_Updated'],
                        'tone': record['Tone'],
                        'heading_style': record['Heading_Style'],
                        'list_style': record['List_Style']
                    }
            return None
        except Exception as e:
            st.warning(f"Could not retrieve cached style guide: {str(e)}")
            return None

    def save_style_guide(self, domain: str, style_guide: str, metadata: Dict = None):
        """Save style guide to sheets"""
        try:
            worksheet = self.spreadsheet.worksheet('Style_Guides')

            # Check if domain already exists
            records = worksheet.get_all_records()
            existing_row = None

            for i, record in enumerate(records):
                if record['Domain'].lower() == domain.lower():
                    existing_row = i + 2  # +2 for header and 0-based index
                    break

            # Prepare row data
            row_data = [
                domain,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                metadata.get('tone', '') if metadata else '',
                metadata.get('heading_style', '') if metadata else '',
                metadata.get('list_style', '') if metadata else '',
                style_guide,
                metadata.get('quality', 'Good') if metadata else 'Good'
            ]

            if existing_row:
                # Update existing row
                worksheet.update(f'A{existing_row}:G{existing_row}', [row_data])
            else:
                # Append new row
                worksheet.append_row(row_data)

        except Exception as e:
            st.warning(f"Could not save style guide: {str(e)}")

    def save_generated_content(self, topic: str, source_blog: str, content_data: Dict):
        """Save generated content to sheets"""
        try:
            worksheet = self.spreadsheet.worksheet('Generated_Content')

            # Generate ID (simple timestamp-based)
            content_id = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Calculate word count
            word_count = len(content_data.get('final', '').split())

            # Extract SEO score if available
            seo_score = ''
            if 'seo_analysis' in content_data:
                seo_text = content_data['seo_analysis']
                if 'SEO SCORE:' in seo_text:
                    try:
                        score_line = [line for line in seo_text.split('\n') if 'SEO SCORE:' in line][0]
                        seo_score = score_line.split(':')[1].strip().split('/')[0]
                    except:
                        pass

            row_data = [
                content_id,
                topic,
                source_blog,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Generated',
                content_data.get('final', ''),
                seo_score,
                word_count,
                ''  # User notes - empty initially
            ]

            worksheet.append_row(row_data)

        except Exception as e:
            st.warning(f"Could not save content: {str(e)}")

    def update_blog_source_stats(self, domain: str, success: bool = True):
        """Update blog source statistics"""
        try:
            worksheet = self.spreadsheet.worksheet('Blog_Sources')
            records = worksheet.get_all_records()

            existing_row = None
            for i, record in enumerate(records):
                if record['Domain'].lower() == domain.lower():
                    existing_row = i + 2
                    break

            if existing_row:
                # Update existing entry
                current_success = int(records[existing_row-2].get('Success_Count', 0))
                new_success = current_success + (1 if success else 0)

                worksheet.update(f'E{existing_row}', [[new_success]])
                worksheet.update(f'D{existing_row}', [[datetime.now().strftime('%Y-%m-%d')]])
            else:
                # Create new entry
                row_data = [
                    domain,
                    'Unknown',  # Category - can be filled manually
                    5 if success else 3,  # Quality rating
                    datetime.now().strftime('%Y-%m-%d'),
                    1 if success else 0,  # Success count
                    'Auto-created'
                ]
                worksheet.append_row(row_data)

        except Exception as e:
            st.warning(f"Could not update blog source stats: {str(e)}")

    def get_content_history(self, limit: int = 50) -> List[Dict]:
        """Get recent content generation history"""
        try:
            worksheet = self.spreadsheet.worksheet('Generated_Content')
            records = worksheet.get_all_records()

            # Sort by date (most recent first) and limit
            sorted_records = sorted(
                records,
                key=lambda x: x.get('Date_Created', ''),
                reverse=True
            )

            return sorted_records[:limit]

        except Exception as e:
            st.warning(f"Could not retrieve content history: {str(e)}")
            return []

    def get_blog_source_stats(self) -> List[Dict]:
        """Get blog source performance statistics"""
        try:
            worksheet = self.spreadsheet.worksheet('Blog_Sources')
            records = worksheet.get_all_records()

            # Sort by success count
            sorted_records = sorted(
                records,
                key=lambda x: int(x.get('Success_Count', 0)),
                reverse=True
            )

            return sorted_records

        except Exception as e:
            st.warning(f"Could not retrieve blog source stats: {str(e)}")
            return []

    def save_topic_ideas(self, source_blog: str, topics: List[Dict]):
        """Save generated topic ideas to sheets and add IDs to topic objects"""
        try:
            worksheet = self.spreadsheet.worksheet('Topic_Ideas')

            for topic in topics:
                # Generate ID
                topic_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]

                # Add ID to the topic object for later reference
                topic['ID'] = topic_id

                row_data = [
                    topic_id,
                    source_blog,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    topic.get('title', ''),
                    topic.get('angle', ''),
                    ', '.join(topic.get('keywords', [])),
                    topic.get('content_type', ''),
                    topic.get('rationale', ''),
                    str(topic.get('search_volume', 'N/A')),
                    topic.get('competition', 'N/A'),
                    topic.get('trend_score', 0),
                    'Generated',  # Status
                    ''  # Used_Date - empty initially
                ]

                worksheet.append_row(row_data)

        except Exception as e:
            st.warning(f"Could not save topic ideas: {str(e)}")

    def get_topic_ideas(self, source_blog: str = None, limit: int = 50) -> List[Dict]:
        """Get saved topic ideas, optionally filtered by source blog"""
        try:
            worksheet = self.spreadsheet.worksheet('Topic_Ideas')
            records = worksheet.get_all_records()

            # Filter by source blog if specified
            if source_blog:
                records = [r for r in records if r.get('Source_Blog', '').lower() == source_blog.lower()]

            # Sort by date (most recent first) and limit
            sorted_records = sorted(
                records,
                key=lambda x: x.get('Date_Created', ''),
                reverse=True
            )

            return sorted_records[:limit]

        except Exception as e:
            st.warning(f"Could not retrieve topic ideas: {str(e)}")
            return []

    def mark_topic_used(self, topic_id: str):
        """Mark a topic idea as used"""
        try:
            worksheet = self.spreadsheet.worksheet('Topic_Ideas')
            records = worksheet.get_all_records()

            for i, record in enumerate(records):
                if record.get('ID') == topic_id:
                    row_num = i + 2  # +2 for header and 0-based index
                    worksheet.update(f'L{row_num}', [['Used']])
                    worksheet.update(f'M{row_num}', [[datetime.now().strftime('%Y-%m-%d')]])
                    break

        except Exception as e:
            st.warning(f"Could not mark topic as used: {str(e)}")

def create_sheets_manager(service_account_json: str, spreadsheet_id: str) -> Optional[SheetsManager]:
    """Factory function to create SheetsManager with error handling"""
    try:
        manager = SheetsManager(service_account_json, spreadsheet_id)
        if manager.test_connection():
            return manager
        return None
    except Exception as e:
        st.error(f"Failed to create Sheets manager: {str(e)}")
        return None