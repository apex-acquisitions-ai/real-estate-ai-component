import os
import csv
import json
from dotenv import load_dotenv
from openai import OpenAI
from schema import SEOStrategyResponse

# Load environment variables
load_dotenv()

# Initialize OpenAI SDK pointing to Gemini's OpenAI-compatible base URL
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

csv_path = "data/5_dealcheck_organic_positions.csv"

# Read and parse CSV
keyword_data = []
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            # Extract metrics from row
            volume = int(row.get("Search Volume", 0) or 0)
            kd = int(row.get("Keyword Difficulty", 0) or 0)
            cpc = float(row.get("CPC", 0.0) or 0.0)
            keyword = row.get("Keyword", "")
            intent = row.get("Keyword Intents", "") or row.get("Intent", "")
            traffic = float(row.get("Traffic", 0.0) or 0.0)
            position = int(row.get("Position", 100) or 100)
            
            # Filter criteria: Non-brand terms with reasonable traffic or search volume
            if not keyword or "dealcheck" in keyword.lower() or "deal check" in keyword.lower():
                continue
                
            keyword_data.append({
                "keyword": keyword,
                "position": position,
                "search_volume": volume,
                "keyword_difficulty": kd,
                "cpc": cpc,
                "intent": intent,
                "traffic": traffic
            })
        except Exception:
            continue

# Sort by search volume descending
keyword_data.sort(key=lambda x: x["search_volume"], reverse=True)

# Select the top 25 high-traffic/high-value terms to analyze
selected_keywords = keyword_data[:25]

print(f"Extracted {len(keyword_data)} keywords. Analyzing top {len(selected_keywords)} target terms...")

# Define system prompt for the SEO Analyst
system_prompt = """
You are an expert Real Estate SEO Strategist and SaaS Growth Architect. 
Your task is to analyze organic keyword ranking data from competitor platforms (like DealCheck.io), identify high-value search terms, and build a structured SEO Content and Conversion Strategy.

CRITICAL DIRECTIVES:
1. TARGET SELECTION: Identify the best keyword targets based on High Traffic Potential (Search Volume), Commercial/Transactional Intent, or Low Difficulty "low-hanging fruit" (KD < 30).
2. ACTIONABLE PAGES: Suggest dedicated high-converting Landing Pages for GoHighLevel or modern CMS (with structures and CTAs) to rank for these high-value terms.
3. VALUE-DRIVEN BLOGS: Design educational blog topics with talking points and lead magnets that can attract organically and funnel users into leads.
4. Respond ONLY with a valid JSON object matching the defined response format schema. Do not include markdown wraps (```json) or conversational text.
"""

user_content = "Analyze these top competitor organic keyword positions and build an SEO content and conversion strategy:\n\n"
user_content += json.dumps(selected_keywords, indent=2)

print("\nCalling Gemini API for SEO Strategy Analysis...\n")

try:
    response = client.beta.chat.completions.parse(
        model="models/gemini-3.5-flash-lite",  # Low-overhead lite model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        response_format=SEOStrategyResponse,
        temperature=0.2
    )
    
    # Extract and format JSON result
    result = response.choices[0].message.parsed.model_dump()
    
    # Ensure output folder exists
    output_dir = "sample_evaluations"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "dealcheck_seo_strategy.json")
    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump(result, out_f, indent=2)
        
    print("--- SUCCESS! Live SEO Strategy Generated ---")
    print(f"Saved JSON: {output_path}\n")
    print("Executive Summary:\n", result["executive_summary"])
    
    print("\n[Top Keyword Opportunities]")
    for kw in result["top_keyword_opportunities"][:5]:
        print(f"  - '{kw['keyword']}' (Vol: {kw['search_volume']}, KD: {kw['keyword_difficulty']}, CPC: ${kw['cpc']:.2f})")
        print(f"    Strategic Value: {kw['strategic_value']}")
        
    print("\n[Suggested Landing Pages]")
    for lp in result["suggested_landing_pages"][:2]:
        print(f"  - '{lp['title']}' (Slug: /{lp['slug']}, Target: '{lp['target_keyword']}')")
        print(f"    CTA: {lp['main_cta']}")
        print(f"    Structure: {', '.join(lp['suggested_structure'])}")
        
    print("\n[Suggested Blog Topics]")
    for bt in result["suggested_blog_topics"][:2]:
        print(f"  - Topic: '{bt['title']}' (Target: '{bt['target_keyword']}')")
        print(f"    Lead Magnet: {bt['lead_magnet']}")

except Exception as e:
    print(f"Error during API call: {e}")
