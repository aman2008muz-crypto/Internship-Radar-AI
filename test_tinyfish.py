from dotenv import load_dotenv
from tinyfish import TinyFish

load_dotenv()

client = TinyFish()

response = client.search.query(
    "software engineering internships India official careers"
)

print("Total results:", response.total_results)

for item in response.results[:5]:
    print("\nTitle:", item.title)
    print("URL:", item.url)
    print("Snippet:", item.snippet)