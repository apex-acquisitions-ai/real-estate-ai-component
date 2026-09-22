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

top_hc = sorted(r_csv("data/9_housecanary_organic_positions.csv", lambda r: {
    "keyword": r["Keyword"], "position": int(r["Position"] or 100), "search_volume": int(r["Search Volume"] or 0),
    "keyword_difficulty": int(r["Keyword Difficulty"] or 0), "cpc": float(r["CPC"] or 0.0)
} if r["Keyword"] and int(r["Position"] or 100) <= 20 and not any(b in r["Keyword"].lower() for b in ["housecanary", "house canary", "housecanery", "comehome", "withroam"]) else None), key=lambda x: x["search_volume"], reverse=True)[:10]

top_gaps = sorted(r_csv("data/2_keyword_gap_competitors.csv", lambda r: {
    "keyword": r["Keyword"], "search_volume": int(r.get("Volume") or 0), "keyword_difficulty": int(r.get("Keyword Difficulty") or 0),
    "cpc": float(r.get("CPC") or 0.0), "competitor_rankings": f"housecanary: #{r.get('housecanary.com')}, bricked: #{r.get('bricked.ai')}"
} if r["Keyword"] and "dealcheck" not in r["Keyword"].lower() and (r.get("dealcheck.io") == "0" or (r.get("dealcheck.io", "").isdigit() and int(r.get("dealcheck.io")) > 50)) and ((r.get("housecanary.com", "").isdigit() and 1 <= int(r.get("housecanary.com")) <= 40) or (r.get("bricked.ai", "").isdigit() and 1 <= int(r.get("bricked.ai")) <= 40)) else None), key=lambda x: x["search_volume"], reverse=True)[:10]

top_br_gaps = sorted(r_csv("data/7_bricked_keyword_gap.csv", lambda r: {
    "keyword": r["Keyword"], "search_volume": int(r.get("Volume") or 0), "keyword_difficulty": int(r.get("Keyword Difficulty") or 0),
    "cpc": float(r.get("CPC") or 0.0), "rankings": f"bricked: #{r.get('bricked.ai')}, dealcheck: #{r.get('dealcheck.io')}, housecanary: #{r.get('housecanary.com')}"
} if r["Keyword"] else None), key=lambda x: x["search_volume"], reverse=True)[:10]

top_hc_gaps = sorted(r_csv("data/10_housecanary_keyword_gap.csv", lambda r: {
    "keyword": r["Keyword"], "search_volume": int(r.get("Volume") or 0), "keyword_difficulty": int(r.get("Keyword Difficulty") or 0),
    "cpc": float(r.get("CPC") or 0.0), "rankings": f"housecanary: #{r.get('housecanary.com')}, bricked: #{r.get('bricked.ai')}, dealcheck: #{r.get('dealcheck.io')}"
} if r["Keyword"] else None), key=lambda x: x["search_volume"], reverse=True)[:10]

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

data_set = {
    "dc_s": top_dc, "br_s": top_br, "hc_s": top_hc, "dc_g": top_gaps, "br_g": top_br_gaps, "hc_g": top_hc_gaps, "dc_b": top_dc_bl, "br_b": top_br_bl
}
print("Data parsed successfully.")

system_prompt = "You are an Real Estate SEO Strategist. Analyze competitor keywords, gaps, and backlinks (DealCheck, Bricked.ai, HouseCanary) and build a roadmap. Respond ONLY with valid JSON."

try:
    response = client.beta.chat.completions.parse(
        model="models/gemini-3.5-flash-lite",
        messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": "Analyze organic metrics, competitor gaps, and backlinks:\n" + json.dumps(data_set, indent=2)}],
        response_format=SEOStrategyResponse,
        temperature=0.2
    )
    result = response.choices[0].message.parsed.model_dump()
    os.makedirs("sample_evaluations", exist_ok=True)
    out_path = "sample_evaluations/dealcheck_seo_strategy.json"
    with open(out_path, "w", encoding="utf-8") as out_f:
        json.dump(result, out_f, indent=2)
    print("JSON saved:", out_path)
    print("Executive Summary:\n", result["executive_summary"])
    print("\n[Top Opportunities]")
    for kw in result["top_keyword_opportunities"][:5]:
         print(f"- '{kw['keyword']}' (Vol: {kw['search_volume']}, KD: {kw['keyword_difficulty']})")
    print("\n[Suggested Backlink Campaigns]")
    for bc in result["suggested_backlink_campaigns"][:3]:
         print(f"- Domain: '{bc['domain']}' (DA: {bc['authority_score']})\n  Angle: {bc['strategic_angle']}\n  Anchor: '{bc['anchor_text_suggestion']}'")
except Exception as e:
    print(f"Error during API call: {e}")
