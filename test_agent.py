from dotenv import load_dotenv
from tinyfish import TinyFish, RunStatus

load_dotenv()

client = TinyFish()

schema = {
    "type": "object",
    "properties": {
        "company": {
            "type": "string"
        },
        "opportunities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "location": {"type": "string"},
                    "eligibility": {"type": "string"},
                    "deadline": {"type": "string"},
                    "application_url": {"type": "string"},
                    "source_url": {"type": "string"}
                },
                "required": [
                    "role",
                    "location",
                    "eligibility",
                    "deadline",
                    "application_url",
                    "source_url"
                ]
            }
        }
    },
    "required": ["company", "opportunities"]
}

print("Starting TinyFish Agent...")

response = client.agent.run(
    url="https://www.amazon.jobs/",
    goal="""
    Inspect this official company careers website.

    Find software engineering internship opportunities
    relevant to undergraduate students in India.

    Extract:
    - Job title
    - Location
    - Eligibility
    - Application deadline
    - Official application URL
    - Source URL

    Only return opportunities supported by the website.
    Do not invent missing information.
    If information is unavailable, return "Not specified".

    Return the results in the requested JSON format.
    """,
    output_schema=schema
)

if response.status == RunStatus.COMPLETED:
    print("\nAgent completed successfully!")
    print(response.result)
else:
    print("\nAgent status:", response.status)
    print("Error:", response.error)