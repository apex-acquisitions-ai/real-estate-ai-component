import os, csv, json, re
from dotenv import load_dotenv
from openai import OpenAI
from schema import SEOStrategyResponse

load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

org_kws = []
with open("data/5_dealcheck_organic_positions.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            kw = r.get("Keyword", "")
            if kw and "dealcheck" not in kw.lower():
                org_kws.append({
                    "keyword": kw, "position": int(r.get("Position", 100) or 100),
                    "search_volume": int(r.get("Search Volume", 0) or 0),
                    "keyword_difficulty": int(r.get("Keyword Difficulty", 0) or 0),
                    "cpc": float(r.get("CPC", 0.0) or 0.0), "intent": r.get("Keyword Intents", "")
                })
        except Exception: continue
org_kws.sort(key=lambda x: x["search_volume"], reverse=True)
top_org = org_kws[:15]

gap_kws = []
with open("data/2_keyword_gap_competitors.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            kw = r.get("Keyword", "")
            dc, hc, br = r.get("dealcheck.io", "0") or "0", r.get("housecanary.com", "0") or "0", r.get("bricked.ai", "0") or "0"
            is_dc = (dc == "0" or (dc.isdigit() and int(dc) > 50))
            is_co = ((hc.isdigit() and 1 <= int(hc) <= 40) or (br.isdigit() and 1 <= int(br) <= 40))
            if is_dc and is_co and kw and "dealcheck" not in kw.lower():
                comps = []
                if hc.isdigit() and int(hc) > 0: comps.append(f"housecanary: #{hc}")
                if br.isdigit() and int(br) > 0: comps.append(f"bricked: #{br}")
                gap_kws.append({
                    "keyword": kw, "search_volume": int(r.get("Volume", 0) or 0),
                    "keyword_difficulty": int(r.get("Keyword Difficulty", 0) or 0),
                    "cpc": float(r.get("CPC", 0.0) or 0.0), "intent": r.get("Intents", ""), "competitor_rankings": ", ".join(comps)
                })
        except Exception: continue
gap_kws.sort(key=lambda x: x["search_volume"], reverse=True)
top_gaps = gap_kws[:15]

backlinks = []
seen = set()
with open("data/3_backlink_analytics_referrals.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            ascore = int(r.get("Page ascore", "0") or "0")
            src_url = r.get("Source url", "")
            m = re.search(r'https?://(?:www\.)?([^/]+)', src_url)
            dom = m.group(1) if m else src_url
            if dom and dom not in seen and "blogspot" not in dom and "tumblr" not in dom:
                seen.add(dom)
                backlinks.append({
                    "domain": dom, "authority_score": ascore,
                    "page_title": r.get("Source title", ""), "anchor": r.get("Anchor", "")
                })
        except Exception: continue
backlinks.sort(key=lambda x: x["authority_score"], reverse=True)
top_backlinks = backlinks[:12]

combined_dataset = {
    "dealcheck_organic_strengths": top_org, "critical_seo_competitor_gaps": top_gaps, "high_value_referring_backlink_domains": top_backlinks
}
print(f"Loaded datasets. Analyzing {len(top_org)} strengths + {len(top_gaps)} gaps + {len(top_backlinks)} backlink domains...")

system_prompt = """
You are an expert Real Estate SEO Strategist. Analyze competitor keywords, gaps, and backlinks (DealCheck, HouseCanary, Bricked.ai), and build an SEO roadmap.
1. TARGETS: Pick top targets based on "Low-hanging fruit" gaps (high volume, low difficulty where competitors rank but DealCheck is weak/absent) and high CPC.
2. PAGES: Suggest GHL/CMS Landing Pages (with structures and CTAs).
3. BLOGS: Design blog topics with talking points and lead magnets.
4. BACKLINKS: Suggest backlink campaigns targeting high-authority domains/categories in our list (e.g. rentcast.io, realwealth.com, w2capitalist.com, apps.apple.com), with strategic pitch hooks and anchor text.
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
        print(f"  - '{kw['keyword']}' (Vol: {kw['search_volume']}, KD: {kw['keyword_difficulty']}, CPC: ${kw['cpc']:.2f})")
    print("\n[Suggested Landing Pages]")
    for lp in result["suggested_landing_pages"][:2]:
        print(f"  - '{lp['title']}' (Slug: /{lp['slug']})")
    print("\n[Suggested Blogs]")
    for bt in result["suggested_blog_topics"][:2]:
        print(f"  - Topic: '{bt['title']}'")
    print("\n[Suggested Backlink Campaigns]")
    for bc in result["suggested_backlink_campaigns"][:3]:
        print(f"  - Domain: '{bc['domain']}' (Authority: {bc['authority_score']})\n    Angle: {bc['strategic_angle']}\n    Anchor: '{bc['anchor_text_suggestion']}'")
except Exception as e:
    print(f"Error during API call: {e}")
