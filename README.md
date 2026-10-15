# 🚀 Internship Radar AI

### Stop Searching. Start Discovering.

**Internship Radar AI** is an AI-powered internship discovery platform designed to help students find relevant opportunities across company career pages and job portals.

Built for the **TinyFish × TechnoJam Student Bounty**, the project uses TinyFish's web intelligence capabilities to discover relevant pages, retrieve webpage content, and extract structured internship information.

The goal is to make internship discovery smarter, faster, and more personalized.

---

## 💡 Problem Statement

Students often spend hours searching multiple company career websites and job portals to find internships that match their skills, interests, and preferred locations.

The process is time-consuming, repetitive, and makes it difficult to compare opportunities efficiently.

## 🎯 Our Solution

Internship Radar AI streamlines internship discovery through automated web research and personalized matching.

Users can specify their target role, preferred location, and technical skills to discover relevant opportunities and review structured information with links to the original sources.

---

## ✨ Key Features

- 🔎 **Smart Internship Discovery** — Discover relevant career pages and internship opportunities using TinyFish Search.
- 🌐 **Live Webpage Retrieval** — Retrieve and inspect actual webpage content using TinyFish Fetch.
- 🤖 **AI-Powered Extraction** — Extract structured internship details using TinyFish Agent.
- 🎯 **Personalized Matching** — Estimate opportunity relevance based on roles, skills, and location preferences.
- 🧹 **Duplicate Detection** — Reduce duplicate listings collected from multiple sources.
- 🔗 **Application Links** — Access source-supported application links and original career pages.
- 📍 **Location-Based Discovery** — Search according to preferred locations and remote opportunities.
- 💾 **Saved Opportunities** — Keep track of interesting internships.
- 📊 **Structured Results** — View internship information in an organized format.
- 📥 **Data Export** — Export supported results to CSV and JSON.
- 🛡️ **Source Transparency** — Distinguish extracted information from details that remain unverified.
- 🎨 **Modern Dashboard** — Explore opportunities through a clean, student-friendly interface.

*Feature availability depends on the current implementation. Only describe features as operational after testing them.*

---

## ⚙️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic and data processing |
| Streamlit | Interactive web interface |
| TinyFish Search | Discover relevant webpages |
| TinyFish Fetch | Retrieve webpage content |
| TinyFish Agent | Extract structured information |
| Pandas | Data processing and organization |
| python-dotenv | Environment variable management |
| JSON / CSV | Structured data and exports |

---

## 🏗️ How It Works

The application follows a simple discovery pipeline:

1. **User Preferences** — The user enters a target role, preferred location, and relevant skills.
2. **Search** — TinyFish Search discovers relevant career pages and internship listings.
3. **Fetch** — TinyFish Fetch retrieves content from selected webpages.
4. **Extract** — TinyFish Agent extracts structured internship information from supported sources.
5. **Normalize & Deduplicate** — The application standardizes records and identifies duplicates.
6. **Match & Rank** — Opportunities receive estimated match scores based on user preferences.
7. **Review & Apply** — Users inspect the original source and follow available application links.

```text
User Preferences
       |
       v
TinyFish Search
       |
       v
Career Pages & Job Listings
       |
       v
TinyFish Fetch
       |
       v
TinyFish Agent
       |
       v
Structured Internship Data
       |
       v
Deduplication & Matching
       |
       v
Internship Radar AI Dashboard
       |
       v
Review Opportunities & Apply
