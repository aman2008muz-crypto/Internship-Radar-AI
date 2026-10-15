import os
import re
import json
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv
from tinyfish import TinyFish, RunStatus


# =====================================================
# CONFIGURATION
# =====================================================

load_dotenv(override=True)

def get_api_key():
    """Retrieve TinyFish API key from session state, environment, or .env file."""
    if st.session_state.get("custom_api_key"):
        return st.session_state["custom_api_key"].strip()
    load_dotenv(override=True)
    key = os.getenv("TINYFISH_API_KEY", "").strip()
    if key:
        return key

    # Robust fallback: check if .env has bare key or raw string
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("sk-tinyfish-"):
                        return line
                    if line.startswith("TINYFISH_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""

def save_api_key(key: str):
    """Save API key to session state and .env file."""
    clean_key = key.strip()
    st.session_state["custom_api_key"] = clean_key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"TINYFISH_API_KEY={clean_key}\n")
        load_dotenv(override=True)
    except Exception:
        pass

st.set_page_config(
    page_title="Internship Radar AI",
    page_icon="🎯",
    layout="wide"
)

# =====================================================
# SESSION STATE
# =====================================================

defaults = {
    "search_results": [],
    "fetched_pages": [],
    "internships": [],
    "search_preferences": {},
    "search_done": False,
    "fetch_done": False,
    "agent_message": ""
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =====================================================
# STYLING
# =====================================================

st.markdown("""
<style>
.stApp {
    background-color: #0b1020;
    color: #ffffff;
}

.hero {
    padding: 30px;
    border-radius: 20px;
    background: linear-gradient(120deg, #172554, #312e81);
    border: 1px solid #4f46e5;
    margin-bottom: 24px;
}

.job-card {
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #334155;
    background: #151c30;
    margin-bottom: 14px;
}

.metric-card {
    padding: 18px;
    border-radius: 12px;
    background: #151c30;
    border: 1px solid #334155;
}

.stButton > button {
    border-radius: 10px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def safe_url(url):
    """Accept only valid HTTP/HTTPS URLs."""

    if not isinstance(url, str):
        return ""

    url = url.strip()

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return ""

    if not parsed.hostname:
        return ""

    return url


def deduplicate(items):
    """Remove duplicate internships using URL or job identity."""

    unique = {}

    for item in items:
        application_url = safe_url(
            item.get("application_url", "")
        )

        company = str(
            item.get("company", "")
        ).strip().lower()

        role = str(
            item.get("role", "")
        ).strip().lower()

        location = str(
            item.get("location", "")
        ).strip().lower()

        if application_url:
            key = application_url.rstrip("/").lower()
        else:
            key = (company, role, location)

        if key not in unique:
            unique[key] = item

    return list(unique.values())


def calculate_match(job, preferences):
    """Calculate an explainable preference-match score."""

    role = preferences.get("role", "").lower()
    location = preferences.get("location", "").lower()

    student_skills = {
        skill.strip().lower()
        for skill in preferences.get("skills", "").split(",")
        if skill.strip()
    }

    job_role = str(job.get("role", "")).lower()
    job_location = str(job.get("location", "")).lower()

    required_skills = job.get("required_skills", [])

    if isinstance(required_skills, str):
        required_skills = [
            skill.strip()
            for skill in required_skills.split(",")
            if skill.strip()
        ]

    normalized_required = {
        str(skill).lower()
        for skill in required_skills
    }

    matching_skills = student_skills.intersection(
        normalized_required
    )

    # Check for skill occurrences in job title or role
    for skill in student_skills:
        if skill in job_role and skill not in matching_skills:
            matching_skills.add(skill)

    # Role relevance: 40 points
    role_core = role.replace(" intern", "").replace(" developer", "").replace(" designer", "").strip()
    job_core = job_role.replace(" intern", "").replace(" developer", "").replace(" designer", "").strip()

    is_role_match = (
        role_core in job_role
        or job_core in role
        or any(tok in job_role for tok in role_core.split() if len(tok) > 2)
    )
    role_score = 40 if is_role_match else 20

    # Skills match: 40 points
    if normalized_required:
        skills_score = round(
            40 * len(matching_skills) / max(1, len(normalized_required))
        )
    elif matching_skills:
        skills_score = 35
    else:
        skills_score = 25

    # Location compatibility: 20 points
    loc_tokens = [tok.strip() for tok in location.split() if tok.strip()]
    if location == "remote":
        location_score = 20 if "remote" in job_location else 10
    elif any(tok in job_location for tok in loc_tokens):
        location_score = 20
    elif location in ("india", "delhi ncr") and (
        "india" in job_location or "remote" in job_location or "delhi" in job_location or "ncr" in job_location or "noida" in job_location or "gurgaon" in job_location
    ):
        location_score = 20
    else:
        location_score = 10

    score = min(
        100,
        role_score + skills_score + location_score
    )

    return score, sorted(matching_skills)


def normalize_job(job, source_url, preferences):
    """Normalize an extracted opportunity."""

    if not isinstance(job, dict):
        return None

    company = str(job.get("company", "")).strip()
    role = str(job.get("role", "")).strip()

    if not role:
        return None

    application_url = safe_url(
        job.get("application_url", "")
    )

    verified_url = safe_url(
        job.get("source_url", "")
    ) or source_url

    required_skills = job.get("required_skills", [])

    if isinstance(required_skills, str):
        required_skills = [
            s.strip()
            for s in required_skills.split(",")
            if s.strip()
        ]

    if not isinstance(required_skills, list):
        required_skills = []

    item = {
        "company": company or "Not specified",
        "role": role,
        "location": str(
            job.get("location", "Not specified")
        ),
        "eligibility": str(
            job.get("eligibility", "Not specified")
        ),
        "required_skills": required_skills,
        "deadline": str(
            job.get("deadline", "Not specified")
        ),
        "application_url": application_url,
        "source_url": verified_url,
        "verification_status": str(
            job.get("verification_status", "Needs verification")
        )
    }

    score, matching_skills = calculate_match(
        item,
        preferences
    )

    item["match_score"] = score
    item["matching_skills"] = matching_skills

    return item


def response_error(error):
    """Return readable SDK error text."""

    if error is None:
        return "Unknown error"

    return str(getattr(error, "message", error))


def run_agent_for_url(client, target_url, preferences):
    """Execute TinyFish Agent on a target URL to extract live internship data."""

    schema = {
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "opportunities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "location": {"type": "string"},
                        "eligibility": {"type": "string"},
                        "required_skills": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "deadline": {"type": "string"},
                        "application_url": {"type": "string"},
                        "source_url": {"type": "string"},
                        "verification_status": {"type": "string"}
                    },
                    "required": [
                        "role",
                        "location",
                        "eligibility",
                        "deadline",
                        "application_url"
                    ]
                }
            }
        },
        "required": ["company", "opportunities"]
    }

    goal = f"""
    You are an expert technical recruiter and talent scout inspecting this official career website:
    {target_url}

    Candidate Profile:
    - Target Role: {preferences.get('role', '')}
    - Preferred Location: {preferences.get('location', '')}
    - Candidate Skills: {preferences.get('skills', '')}
    - Experience: {preferences.get('experience', '')}

    Find currently open internship listings matching or relevant to this role on this website.
    For every opportunity, extract:
    - Role title
    - Location
    - Eligibility & requirements
    - Required skills
    - Application deadline
    - Official direct application URL
    - Source URL
    - Verification status ("Verified Open" if current/active, else "Needs verification")

    Only return real openings found on the website. Use "Not specified" for missing fields.
    Return results adhering strictly to the requested JSON schema.
    """

    agent_response = client.agent.run(
        url=target_url,
        goal=goal,
        output_schema=schema
    )
    return agent_response


def process_agent_results(agent_response, target_url, preferences):
    """Normalize listings returned by TinyFish Agent."""

    if agent_response.status != RunStatus.COMPLETED:
        return [], f"Agent status: {agent_response.status}"

    data = agent_response.result or {}
    if not isinstance(data, dict):
        return [], "Agent returned an unexpected data format."

    opportunities = data.get("opportunities", [])
    normalized_jobs = []
    company_name = data.get("company") or "Not specified"

    for job in opportunities:
        if not isinstance(job, dict):
            continue
        job["company"] = job.get("company") or company_name
        normalized = normalize_job(job, target_url, preferences)
        if normalized:
            normalized_jobs.append(normalized)

    return normalized_jobs, None


# =====================================================
# HEADER
# =====================================================

st.markdown("""
<div class="hero">
    <h1>🎯 Internship Radar AI</h1>
    <p>
        Discover internships. Match your skills.
        Find your next opportunity.
    </p>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Powered by TinyFish Search, Fetch and Agent"
)


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.title("🎯 Internship Radar")

    st.markdown("---")

    st.markdown("### How it works")

    st.write("1. 🔍 Discover career pages")
    st.write("2. 📄 Read website content")
    st.write("3. 🤖 Extract internship details")
    st.write("4. 🎯 Match your preferences")
    st.write("5. 🔗 Apply through official links")

    st.markdown("---")

    st.caption(
        "Live results depend on website availability "
        "and TinyFish API access."
    )


# =====================================================
# USER PREFERENCES
# =====================================================

st.subheader("🔎 Find Your Next Internship")

col1, col2 = st.columns(2)

with col1:
    role = st.selectbox(
        "Preferred Role",
        [
            "UI/UX Design Intern",
            "Product Design Intern",
            "Software Engineering Intern",
            "Frontend Developer Intern",
            "Full Stack Developer Intern",
            "Data Analyst Intern",
            "Machine Learning Intern",
            "Java Developer Intern",
            "Python Developer Intern"
        ]
    )

    location = st.selectbox(
        "Preferred Location",
        [
            "Delhi NCR",
            "Bengaluru",
            "Remote",
            "India",
            "Hyderabad",
            "Mumbai",
            "Pune"
        ]
    )

with col2:
    role_default_skills = {
        "UI/UX Design Intern": "Figma, UI/UX Design, Prototyping, Wireframing, User Research",
        "Product Design Intern": "Figma, Product Design, User Research, Prototyping",
        "Frontend Developer Intern": "HTML, CSS, JavaScript, React, Figma",
        "Software Engineering Intern": "Python, Java, Data Structures, Problem Solving, Git",
        "Data Analyst Intern": "Python, SQL, Excel, Data Visualization, Pandas",
        "Machine Learning Intern": "Python, PyTorch, Scikit-learn, Machine Learning",
        "Java Developer Intern": "Java, Spring Boot, SQL, OOP, Data Structures",
        "Python Developer Intern": "Python, Django, FastAPI, SQL, Git",
        "Full Stack Developer Intern": "React, Node.js, JavaScript, SQL, Git"
    }

    default_skills = role_default_skills.get(role, "Figma, UI/UX Design, Prototyping")

    skills = st.text_input(
        "Your Skills",
        value=default_skills,
        placeholder="Figma, Wireframing, UI/UX Design, React, Python"
    )

    experience = st.selectbox(
        "Experience Level",
        [
            "Fresher",
            "Less than 1 year",
            "1+ years"
        ]
    )


search_button = st.button(
    "🚀 Discover & Extract Internships (Live TinyFish Agent)",
    type="primary",
    use_container_width=True
)


# =====================================================
# TINYFISH SEARCH + FETCH
# =====================================================

if search_button:

    api_key = get_api_key()
    if not api_key:
        st.error(
            "TinyFish API key not found. "
            "Check your .env file."
        )

    elif not skills.strip():
        st.warning("Please enter your skills first.")

    else:

        # Reset old results
        st.session_state.search_results = []
        st.session_state.fetched_pages = []
        st.session_state.internships = []
        st.session_state.search_done = False
        st.session_state.fetch_done = False
        st.session_state.agent_message = ""

        preferences = {
            "role": role,
            "location": location,
            "skills": skills,
            "experience": experience
        }

        st.session_state.search_preferences = preferences

        query = (
            f"Currently open {role} opportunities in {location}. "
            f"Student skills: {skills}. "
            f"Experience level: {experience}. "
            "Search official company career pages and job portals. "
            "Prioritize current internship listings and official "
            "application URLs."
        )

        try:
            client = TinyFish(api_key=api_key)

            # -----------------------------------------
            # 1. TINYFISH SEARCH
            # -----------------------------------------

            st.subheader("🔍 TinyFish Search")

            with st.spinner(
                "Discovering live career pages..."
            ):

                search_response = client.search.query(query)

            search_items = []

            for item in search_response.results or []:

                url = safe_url(item.url or "")

                if not url:
                    continue

                search_items.append({
                    "title": item.title or "Untitled result",
                    "url": url,
                    "snippet": item.snippet or ""
                })

            st.session_state.search_results = search_items
            st.session_state.search_done = True

            st.success(
                f"Search completed: {len(search_items)} pages discovered."
            )

            # -----------------------------------------
            # 2. SELECT CAREER PAGES
            # -----------------------------------------

            keywords = [
                "career",
                "intern",
                "job",
                "student",
                "university",
                "graduate",
                "opportunit"
            ]

            prioritized = [
                item for item in search_items
                if any(
                    word in item["title"].lower()
                    or word in item["url"].lower()
                    for word in keywords
                )
            ]

            if not prioritized:
                prioritized = search_items

            # Keep the first five URLs to control API usage.
            urls = list(dict.fromkeys(
                item["url"] for item in prioritized
            ))[:5]

            # -----------------------------------------
            # 3. TINYFISH FETCH
            # -----------------------------------------

            if urls:

                st.subheader("📄 TinyFish Fetch")

                with st.spinner(
                    f"Reading {len(urls)} career pages..."
                ):

                    fetch_response = client.fetch.get_contents(
                        urls,
                        format="markdown",
                        links=True
                    )

                fetched = []

                for page in fetch_response.results or []:

                    fetched.append({
                        "url": page.url,
                        "title": getattr(
                            page, "title", "Career page"
                        ),
                        "text": page.text or ""
                    })

                st.session_state.fetched_pages = fetched
                st.session_state.fetch_done = True

                st.success(
                    f"Fetch completed: {len(fetched)} pages read."
                )

                if fetch_response.errors:
                    st.warning(
                        f"{len(fetch_response.errors)} page(s) "
                        "could not be fetched."
                    )

                # -----------------------------------------
                # 4. AUTOMATIC TINYFISH AGENT EXECUTION
                # (Active Web Agent & Wallet Deduction)
                # -----------------------------------------
                target_url = urls[0]
                st.subheader("🤖 TinyFish Agent Execution")

                with st.spinner(
                    f"TinyFish Agent is autonomously inspecting {target_url} "
                    f"to extract verified {role} opportunities (deducts wallet credits)..."
                ):
                    agent_response = run_agent_for_url(
                        client,
                        target_url,
                        st.session_state.search_preferences
                    )
                    normalized_jobs, agent_err = process_agent_results(
                        agent_response,
                        target_url,
                        st.session_state.search_preferences
                    )

                if normalized_jobs:
                    combined = (
                        st.session_state.internships
                        + normalized_jobs
                    )
                    st.session_state.internships = deduplicate(combined)
                    st.session_state.agent_message = (
                        f"Agent completed! Extracted {len(normalized_jobs)} "
                        f"opportunities from {target_url}."
                    )
                    st.success(
                        f"🎉 {st.session_state.agent_message} "
                        "Live steps & wallet credit deducted on TinyFish."
                    )
                elif agent_err:
                    st.warning(f"Agent report: {agent_err}")

            else:
                st.warning("No usable career page URLs found.")

        except Exception as error:
            st.error("TinyFish Search, Fetch, or Agent failed.")
            st.code(response_error(error))


# =====================================================
# SEARCH RESULTS
# =====================================================

if st.session_state.search_done:

    st.subheader("🌐 Discovered Career Pages")

    for index, item in enumerate(
        st.session_state.search_results,
        start=1
    ):

        with st.container():

            st.markdown(
                f"**{index}. {item['title']}**"
            )

            if item["snippet"]:
                st.write(item["snippet"])

            st.link_button(
                "Open Source Website",
                item["url"],
                key=f"search_link_{index}"
            )

            st.divider()


# =====================================================
# FETCHED CONTENT
# =====================================================

if st.session_state.fetch_done:

    st.subheader("📄 Retrieved Website Content")

    st.caption(
        "Fetch retrieves page content. It does not by itself "
        "prove that every listing is open or eligible."
    )

    for index, page in enumerate(
        st.session_state.fetched_pages,
        start=1
    ):

        with st.expander(
            f"Page {index}: {page['url']}"
        ):

            st.write(
                page["text"][:3500]
                or "No readable text returned."
            )


# =====================================================
# TINYFISH AGENT
# =====================================================

if st.session_state.fetched_pages:

    st.markdown("---")

    st.subheader("🤖 Extract Structured Internships")

    page_options = {
        f"{index}. {page['url']}": page
        for index, page in enumerate(
            st.session_state.fetched_pages,
            start=1
        )
    }

    selected_label = st.selectbox(
        "Choose a career page for AI extraction",
        list(page_options.keys())
    )

    selected_page = page_options[selected_label]

    st.caption(
        "Agent runs only when you click the button. "
        "Each run may consume wallet credits."
    )

    extract_button = st.button(
        "🤖 Extract Internship Details with TinyFish Agent",
        type="primary",
        use_container_width=True
    )

    if extract_button:

        try:
            api_key = get_api_key()
            client = TinyFish(api_key=api_key)

            with st.spinner(
                f"TinyFish Agent is inspecting {selected_page['url']} "
                "(deducting wallet credits)..."
            ):
                agent_response = run_agent_for_url(
                    client,
                    selected_page["url"],
                    st.session_state.search_preferences
                )
                normalized_jobs, agent_err = process_agent_results(
                    agent_response,
                    selected_page["url"],
                    st.session_state.search_preferences
                )

            if normalized_jobs:
                combined = (
                    st.session_state.internships
                    + normalized_jobs
                )
                st.session_state.internships = deduplicate(combined)
                st.session_state.agent_message = (
                    f"Agent completed. Extracted {len(normalized_jobs)} candidate listings."
                )
                st.success(f"🎉 Extracted {len(normalized_jobs)} listings from {selected_page['url']}!")
            elif agent_err:
                st.warning(f"Agent status: {agent_err}")

        except Exception as error:
            st.error("TinyFish Agent extraction failed.")
            st.code(response_error(error))


# =====================================================
# MATCHED INTERNSHIPS
# =====================================================

if st.session_state.internships:

    st.markdown("---")

    st.subheader("🎯 Internship Radar Results")

    jobs = sorted(
        st.session_state.internships,
        key=lambda job: job["match_score"],
        reverse=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Unique Listings",
            len(jobs)
        )

    with col2:
        st.metric(
            "Strong Matches",
            sum(
                job["match_score"] >= 70
                for job in jobs
            )
        )

    with col3:
        st.metric(
            "Needs Verification",
            sum(
                job["verification_status"].lower()
                != "verified open"
                for job in jobs
            )
        )

    for index, job in enumerate(jobs, start=1):

        with st.container():

            st.markdown(
                f"""
                <div class="job-card">
                    <h3>{job['role']}</h3>
                    <p>
                        <strong>Company:</strong> {job['company']}
                    </p>
                    <p>
                        <strong>Location:</strong> {job['location']}
                    </p>
                    <p>
                        <strong>Match score:</strong>
                        {job['match_score']}/100
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.write(
                "**Eligibility:**",
                job["eligibility"]
            )

            st.write(
                "**Required skills:**",
                ", ".join(job["required_skills"])
                if job["required_skills"]
                else "Not specified"
            )

            st.write(
                "**Matching skills:**",
                ", ".join(job["matching_skills"])
                if job["matching_skills"]
                else "No confirmed skill overlap"
            )

            st.write(
                "**Deadline:**",
                job["deadline"]
            )

            st.write(
                "**Verification status:**",
                job["verification_status"]
            )

            if job["application_url"]:

                st.link_button(
                    "🚀 Apply on Official Website",
                    job["application_url"],
                    key=f"apply_{index}"
                )

            if job["source_url"]:

                st.link_button(
                    "View Source",
                    job["source_url"],
                    key=f"source_{index}"
                )

            st.divider()

    export_data = [
        {
            key: value
            for key, value in job.items()
            if key != "matching_skills"
        }
        for job in jobs
    ]

    st.download_button(
        "📥 Download Internship Results as JSON",
        data=json.dumps(
            export_data,
            indent=2,
            ensure_ascii=False
        ),
        file_name="internship_radar_results.json",
        mime="application/json"
    )


# =====================================================
# FOOTER
# =====================================================

st.markdown("---")

st.caption(
    "Internship Radar AI | Built with TinyFish Search, "
    "Fetch, Agent and Streamlit."
)

st.caption(
    "Match scores are heuristic rankings, not guarantees "
    "of eligibility or selection."
)