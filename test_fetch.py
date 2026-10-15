from dotenv import load_dotenv
from tinyfish import TinyFish

# Load API key from .env file
load_dotenv()

# Connect to TinyFish
client = TinyFish()

# Website we want to read
urls = [
    "https://www.tinyfish.ai/"
]

print("Fetching website content...")

# Extract website content
response = client.fetch.get_contents(
    urls,
    format="markdown",
    links=True
)

# Display extracted information
for page in response.results:
    print("\nWebsite:", page.url)
    print("\nWebsite content:")
    print((page.text or "")[:2000])

# Display errors, if any
if response.errors:
    print("\nErrors:", response.errors)