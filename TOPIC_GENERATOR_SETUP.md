# Topic Generator with Keyword Research Setup Guide

## Overview
The Topic Generator helps you discover content ideas by:
- Analyzing reference blogs for content gaps
- Generating AI-powered topic suggestions
- Validating topics with Google Trends (free)
- Optional: Getting search volumes from Google Ads API

## Features

### Built-in (No Setup Required)
- ✅ AI-powered topic generation
- ✅ Content gap analysis
- ✅ Google Trends validation
- ✅ Topic suggestions matched to blog style

### Optional: Google Ads API Integration
- 📊 Search volume data
- 📈 Competition analysis
- 💰 CPC estimates
- 🎯 Keyword research

## Quick Start (Without Google Ads)

1. **Enter Reference Blog URL** in sidebar
2. **Enter OpenAI API Key** in sidebar
3. **Click "Generate Topic Ideas"** button
4. **Review suggestions** with trend data
5. **Click "Use This Topic"** to auto-fill

That's it! The basic topic generator works immediately.

---

## Advanced: Google Ads API Setup

If you want search volume and competition data, follow these steps:

### Prerequisites
- Google Ads account with active campaigns
- Basic spending ($10-50/month minimum)
- Developer token from Google

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "BlogAgents Keywords"
3. Note your Project ID

### Step 2: Enable Google Ads API

1. Go to "APIs & Services" > "Library"
2. Search for "Google Ads API"
3. Click "Enable"

### Step 3: Get Developer Token

1. Go to [Google Ads](https://ads.google.com)
2. Tools & Settings > Setup > API Center
3. Request developer token
4. Wait for approval (usually 1-2 business days)
5. Copy your developer token

### Step 4: Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. APIs & Services > Credentials
3. Click "Create Credentials" > "OAuth client ID"
4. Application type: "Desktop app"
5. Name: "BlogAgents"
6. Download JSON (save as `client_secrets.json`)

### Step 5: Generate Refresh Token

Run this Python script to generate refresh token:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

# Your OAuth2 credentials
CLIENT_ID = "your_client_id_here"
CLIENT_SECRET = "your_client_secret_here"

# OAuth2 scopes for Google Ads
SCOPES = ['https://www.googleapis.com/auth/adwords']

# Create flow
flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=SCOPES
)

# Run local server for authentication
credentials = flow.run_local_server(port=8080)

# Print refresh token
print(f"Refresh Token: {credentials.refresh_token}")
```

### Step 6: Get Customer ID

1. Go to [Google Ads](https://ads.google.com)
2. Look at top-right corner
3. Copy customer ID (format: 123-456-7890)
4. Remove hyphens: 1234567890

### Step 7: Configure in BlogAgents

1. Open BlogAgents app
2. Sidebar: Check "Enable Google Ads API"
3. Expand "Google Ads API Configuration"
4. Enter:
   - **Developer Token**: From Step 3
   - **Client ID**: From Step 4
   - **Client Secret**: From Step 4
   - **Refresh Token**: From Step 5
   - **Customer ID**: From Step 6 (no hyphens)
5. Click "Test Google Ads Connection"
6. Should see "✅ Connected to Google Ads API!"

## Using the Topic Generator

### Basic Workflow

1. **Configure** (One Time):
   - Add OpenAI API key
   - Add Reference Blog URL
   - Optional: Configure Google Ads API

2. **Generate Topics**:
   - Click "🎯 Generate Topic Ideas"
   - Wait for AI analysis
   - Review 8-10 topic suggestions

3. **Review Data**:
   - **Angle**: Unique perspective
   - **Keywords**: SEO keywords
   - **Rationale**: Why it works
   - **Content Type**: Guide, Tutorial, etc.
   - **Trend**: Google Trends score
   - **Search Volume**: (if Google Ads enabled)
   - **Competition**: (if Google Ads enabled)

4. **Select Topic**:
   - Click "✏️ Use This Topic"
   - Auto-fills main form
   - Generate content as normal

### Understanding Keyword Data

#### Google Trends (Always Available)
- **Score**: 0-100 interest level
- **🔥 Hot**: 75+ (very popular)
- **📈 Rising**: 50-75 (growing interest)
- **➡️ Steady**: 25-50 (consistent)
- **📉 Low**: 0-25 (low interest)

#### Google Ads Data (Optional)
- **Search Volume**: Monthly searches
- **Competition**: LOW/MEDIUM/HIGH
- **Competition Index**: 0-100 score

## Troubleshooting

### "Failed to connect to Google Ads API"
- Verify developer token is approved
- Check OAuth credentials are correct
- Ensure customer ID has no hyphens
- Confirm Google Ads account has active campaigns

### "No topic ideas generated"
- Check OpenAI API key is valid
- Verify reference blog URL is accessible
- Try different reference blog
- Check internet connection

### "Keyword research not working"
- Google Ads API is optional
- Google Trends always works (no auth needed)
- Verify all 5 credentials are entered correctly
- Test connection before generating topics

## Best Practices

1. **Start Simple**: Use without Google Ads first
2. **Test Reference Blogs**: Try different blogs for variety
3. **Save Good Topics**: Use sheets integration to store ideas
4. **Review Trends**: Higher trend scores = more timely content
5. **Check Competition**: Lower competition = easier to rank

## API Costs

### OpenAI API
- Topic generation: ~$0.01-0.05 per request
- Uses same model as content generation

### Google Ads API
- **FREE** with active Google Ads account
- No per-request charges
- Requires active campaign spending

### Google Trends
- **FREE** always
- No authentication required
- Built into the app

## Security Notes

- Store credentials securely
- Don't share API keys
- Use environment variables in production
- Rotate tokens periodically
- Monitor API usage

## Support

For issues or questions:
- Check troubleshooting section first
- Review [Google Ads API Docs](https://developers.google.com/google-ads/api)
- Contact support with specific error messages

## Future Enhancements

Planned features:
- Topic calendar planning
- Save favorite topics to Sheets
- Batch topic generation
- Competitor topic analysis
- Trending topics dashboard