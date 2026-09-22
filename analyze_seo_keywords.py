import os, csv, json, re
from dotenv import load_dotenv
from openai import OpenAI
from schema import SEOStrategyResponse

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

def r_csv(p, f):
    items = []
    with open(p, "r", encoding="utf-8") as file:
        for r in csv.DictReader(file):
            try:
                item = f(r)
                if item: items.append(item)
            except Exception: continue
    return items

top_dc = sorted(r_csv("data/5_dealcheck_organic_positions.csv", lambda r: {
    "keyword": r["Keyword"], "position": int(r["Position"] or 100), "search_volume": int(r["Search Volume"] or 0),
    "keyword_difficulty": int(r["Keyword Difficulty"] or 0), "cpc": float(r["CPC"] or 0.0)
} if r["Keyword"] and "dealcheck" not in r["Keyword"].lower() else None), key=lambda x: x["search_volume"], reverse=True)[:10]

top_br = sorted(r_csv("data/6_bricked_organic_positions.csv", lambda r: {
    "keyword": r["Keyword"], "position": int(r["Position"] or 100), "search_volume": int(r["Search Volume"] or 0),
    "keyword_difficulty": int(r["Keyword Difficulty"] or 0), "cpc": float(r["CPC"] or 0.0)
} if r["Keyword"] and int(r["Position"] or 100) <= 20 and not any(b in r["Keyword"].lower() for b in ["bricked", "brikd", "brico"]) else None), key=lambda x: x["search_volume"], reverse=True)[:10]

top_gaps = sorted(r_csv("data/2_keyword_gap_competitors.csv", lambda r: {
    "keyword": r["Keyword"], "search_volume": int(r.get("Volume") or 0), "keyword_difficulty": int(r.get("Keyword Difficulty") or 0),
    "cpc": float(r.get("CPC") or 0.0), "competitor_rankings": f"housecanary: #{r.get('housecanary.com')}, bricked: #{r.get('bricked.ai')}"
} if r["Keyword"] and "dealcheck" not in r["Keyword"].lower() and (r.get("dealcheck.io") == "0" or (r.get("dealcheck.io", "").isdigit() and int(r.get("dealcheck.io")) > 50)) and ((r.get("housecanary.com", "").isdigit() and 1 <= int(r.get("housecanary.com")) <= 40) or (r.get("bricked.ai", "").isdigit() and 1 <= int(r.get("bricked.ai")) <= 40)) else None), key=lambda x: x["search_volume"], reverse=True)[:10]

top_br_gaps = sorted(r_csv("data/7_bricked_keyword_gap.csv", lambda r: {
    "keyword": r["Keyword"], "search_volume": int(r.get("Volume") or 0), "keyword_difficulty": int(r.get("Keyword Difficulty") or 0),
    "cpc": float(r.get("CPC") or 0.0), "rankings": f"bricked: #{r.get('bricked.ai')}, dealcheck: #{r.get('dealcheck.io')}, housecanary: #{r.get('housecanary.com')}"
} if r["Keyword"] else None), key=lambda x: x["search_volume"], reverse=True)[:10]

seen = set()
def parse_backlink(r, s):
    url = r["Source url"]
    m = re.search(r'https?://(?:www\.)?([^/]+)', url)
    dom = m.group(1) if m else url
    if dom and dom not in s and "blogspot" not in dom and "tumblr" not in dom:
        s.add(dom)
        return {"domain": dom, "authority_score": int(r.get("Page ascore") or r.get("authority_score") or 0), "anchor": r["Anchor"]}
    return None

s_dc, s_br = set(), set()
top_dc_bl = sorted(r_csv("data/3_backlink_analytics_referrals.csv", lambda r: parse_backlink(r, s_dc)), key=lambda x: x["authority_score"], reverse=True)[:10]
top_br_bl = sorted(r_csv("data/8_bricked_backlink_analytics.csv", lambda r: parse_backlink(r, s_br)), key=lambda x: x["authority_score"], reverse=True)[:10]

combined_dataset = {
    "dc_strengths": top_dc, "br_strengths": top_br, "dc_gaps": top_gaps, "br_gaps": top_br_gaps, "dc_backlinks": top_dc_bl, "br_backlinks": top_br_bl
}
print(f"Data parsed: DC_str({len(top_dc)}), BR_str({len(top_br)}), DC_gaps({len(top_gaps)}), BR_gaps({len(top_br_gaps)}), DC_bl({len(top_dc_bl)}), BR_bl({len(top_br_bl)})")

system_prompt = """
You are an expert Real Estate SEO Strategist. Analyze competitor keywords, gaps, and referring backlinks (DealCheck, Bricked.ai, HouseCanary), and build an SEO roadmap.
1. TARGETS: Pick top targets based on "Low-hanging fruit" gaps (high volume, low difficulty where competitors rank but DealCheck is weak/absent), high CPC terms, and Bricked's strongest rankings/gaps.
2. PAGES: Suggest high-converting GHL/CMS Landing Pages (with structures and CTAs).
3. BLOGS: Design blog topics with detailed talking points and lead magnets.
4. BACKLINKS: Suggest backlink campaigns targeting high-authority domains in our lists (e.g. rentcast.io, realwealth.com, completeaitraining.com), with strategic pitch hooks and anchor text.
5. Respond ONLY with valid JSON matching the schema. No markdown wraps or conversational text.
"""

try:
    response = client.beta.chat.completions.parse(
        model="models/gemini-3.5-flash-lite",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze organic metrics, competitor gaps, and backlinks:\n" + json.dumps(combined_dataset, indent=2)}
        ],
        response_format=SEOStrategyResponse,
        temperature=0.2
    )
    result = response.choices[0].message.parsed.model_dump()
    os.makedirs("sample_evaluations", exist_ok=True)
    out_path = "sample_evaluations/dealcheck_seo_strategy.json"
    with open(out_path, "w", encoding="utf-8") as out_f:
        json.dump(result, out_f, indent=2)
    print(f"--- SUCCESS! Saved JSON: {out_path} ---\n\nExecutive Summary:\n", result["executive_summary"])
    print("\n[Top Opportunities]")
    for kw in result["top_keyword_opportunities"][:5]:
        print(f"  - '{kw['keyword']}' (Vol: {kw['search_volume']}, KD: {kw['keyword_difficulty']})")
    print("\n[Suggested Backlink Campaigns]")
    for bc in result["suggested_backlink_campaigns"][:3]:
        print(f"  - Domain: '{bc['domain']}' (Authority: {bc['authority_score']})\n    Angle: {bc['strategic_angle']}\n    Anchor: '{bc['anchor_text_suggestion']}'")
except Exception as e:
    print(f"Error during API call: {e}")
