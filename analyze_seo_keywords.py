import os, csv, json
from dotenv import load_dotenv
from openai import OpenAI
from schema import SEOStrategyResponse

load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# 1. Parse Organic Strengths
organic_keywords = []
with open("data/5_dealcheck_organic_positions.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            kw = r.get("Keyword", "")
            if kw and "dealcheck" not in kw.lower():
                organic_keywords.append({
                    "keyword": kw, "position": int(r.get("Position", 100) or 100),
                    "search_volume": int(r.get("Search Volume", 0) or 0),
                    "keyword_difficulty": int(r.get("Keyword Difficulty", 0) or 0),
                    "cpc": float(r.get("CPC", 0.0) or 0.0), "intent": r.get("Keyword Intents", "")
                })
        except Exception: continue

organic_keywords.sort(key=lambda x: x["search_volume"], reverse=True)
top_organic = organic_keywords[:15]

# 2. Parse Competitor Gaps
gap_keywords = []
with open("data/2_keyword_gap_competitors.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            kw = r.get("Keyword", "")
            vol_str = r.get("Volume", "0") or "0"
            volume = int(vol_str) if vol_str.isdigit() else 0
            kd_str = r.get("Keyword Difficulty", "0") or "0"
            kd = int(kd_str) if kd_str.isdigit() else 0
            cpc_str = r.get("CPC", "0.0") or "0.0"
            cpc = float(cpc_str) if cpc_str.replace('.', '', 1).isdigit() else 0.0
            
            dc, hc, br = r.get("dealcheck.io", "0") or "0", r.get("housecanary.com", "0") or "0", r.get("bricked.ai", "0") or "0"
            is_dc_absent = (dc == "0" or (dc.isdigit() and int(dc) > 50))
            is_comp_present = ((hc.isdigit() and 1 <= int(hc) <= 40) or (br.isdigit() and 1 <= int(br) <= 40))
            
            if is_dc_absent and is_comp_present and kw and "dealcheck" not in kw.lower():
                comps = []
                if hc.isdigit() and int(hc) > 0: comps.append(f"housecanary: #{hc}")
                if br.isdigit() and int(br) > 0: comps.append(f"bricked: #{br}")
                gap_keywords.append({
                    "keyword": kw, "search_volume": volume, "keyword_difficulty": kd,
                    "cpc": cpc, "intent": r.get("Intents", ""), "competitor_rankings": ", ".join(comps)
                })
        except Exception: continue

gap_keywords.sort(key=lambda x: x["search_volume"], reverse=True)
top_gaps = gap_keywords[:15]

combined_dataset = {"dealcheck_organic_strengths": top_organic, "critical_seo_competitor_gaps": top_gaps}
print(f"Extracted {len(organic_keywords)} strength keywords and {len(gap_keywords)} gap keywords.")

system_prompt = """
You are an expert Real Estate SEO Strategist. Analyze competitor organic keywords and gaps (DealCheck vs HouseCanary vs Bricked.ai), and build an SEO roadmap.
1. TARGET SELECTION: Pick top targets based on "Low-hanging fruit" gaps (high volume, low difficulty where competitors rank but DealCheck is weak/absent) and high CPC intent terms.
2. PAGES: Suggest GHL/CMS Landing Pages (with structures and CTAs) to capture this traffic.
3. BLOGS: Design blog topics with talking points and lead magnets.
4. Respond ONLY with valid JSON matching the schema. No markdown wraps or conversational text.
"""

try:
    response = client.beta.chat.completions.parse(
        model="models/gemini-3.5-flash-lite",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze organic metrics and competitor gaps, and design an SEO strategy:\n" + json.dumps(combined_dataset, indent=2)}
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
    for kw in result["top_keyword_opportunities"][:6]:
        print(f"  - '{kw['keyword']}' (Vol: {kw['search_volume']}, KD: {kw['keyword_difficulty']}, CPC: ${kw['cpc']:.2f})")
        print(f"    Strategic Value: {kw['strategic_value']}")
    print("\n[Suggested Landing Pages]")
    for lp in result["suggested_landing_pages"][:2]:
        print(f"  - '{lp['title']}' (Slug: /{lp['slug']}, Target: '{lp['target_keyword']}')\n    CTA: {lp['main_cta']}\n    Structure: {', '.join(lp['suggested_structure'])}")
    print("\n[Suggested Blogs]")
    for bt in result["suggested_blog_topics"][:2]:
        print(f"  - Topic: '{bt['title']}' (Target: '{bt['target_keyword']}')\n    Lead Magnet: {bt['lead_magnet']}")
except Exception as e:
    print(f"Error during API call: {e}")
