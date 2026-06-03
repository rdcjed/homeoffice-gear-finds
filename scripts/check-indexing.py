#!/usr/bin/env python3
"""
Google Index Monitor - checks if the site is being indexed by Google.
Sends a report to Feishu with the current status.
Usage: python3 scripts/check-indexing.py
"""

import json, os, urllib.request, re, ssl, subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ssl._create_default_https_context = ssl._create_unverified_context

proxy = os.popen("ip route show default | awk '{print $3}'").read().strip()
proxy_handler = urllib.request.ProxyHandler({
    'http': f'http://{proxy}:7897', 'https': f'http://{proxy}:7897'
})
opener = urllib.request.build_opener(proxy_handler)

def check_google_index():
    """Check how many pages Google has indexed"""
    query = "site:rdcjed.github.io/homeoffice-gear-finds"
    url = f"https://www.google.com/search?q={urllib.request.quote(query)}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    try:
        resp = opener.open(req, timeout=10)
        content = resp.read().decode(errors='replace')
        count_m = re.search(r'About ([\d,]+) results', content)
        if count_m:
            return f"{count_m.group(1)} pages indexed"
        results = re.findall(r'<a href="/url\?q=(https://[^&]+)', content)
        if results:
            return f"Found ~{len(results)} results in search"
        if 'did not match' in content:
            return "Not indexed yet"
        return "Unknown status"
    except:
        return "Check failed (Google blocked)"

def load_stats():
    """Load existing stats or create new"""
    stats_file = f'{BASE}/topics/index-stats.json'
    if os.path.exists(stats_file):
        with open(stats_file) as f:
            return json.load(f)
    return {"checks": [], "total_articles": 0}

def main():
    with open(f'{BASE}/articles/articles.json') as f:
        articles = json.load(f)
    
    status = check_google_index()
    total = len(articles)
    
    stats = load_stats()
    stats['total_articles'] = total
    from datetime import date
    stats['checks'].append({
        "date": date.today().isoformat(),
        "status": status,
        "articles": total
    })
    
    # Keep last 30 checks
    stats['checks'] = stats['checks'][-30:]
    
    with open(f'{BASE}/topics/index-stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    # Determine trend
    prev_statuses = [c['status'] for c in stats['checks'][-3:-1]]
    if 'indexed' in status.lower() or 'results' in status.lower():
        if any('indexed' in s.lower() or 'results' in s.lower() for s in prev_statuses):
            trend = "📈 Still indexed"
        else:
            trend = "🎉 First time indexed!"
    else:
        trend = "⏳ Waiting for Google..."
    
    report = f"""📊 **Google Index Report**

📅 Date: {date.today().isoformat()}
📝 Articles: {total}
🔍 Status: {status}
{trend}

📌 **Tips:**
• Make sure Search Console is verified (you need to click verify)
• Submit sitemap.xml once verified
• New sites typically take 1-3 weeks for first index
"""
    
    print(report)
    
    # Try to send to Feishu
    try:
        result = subprocess.run(
            ['hermes', 'send', '--to', 'feishu:oc_808eea9dea39baad09d24225f9061b0c', report],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, 'http_proxy': f'http://{proxy}:7897', 'https_proxy': f'http://{proxy}:7897'}
        )
        print(f"📨 Feishu send: {'OK' if result.returncode == 0 else result.stderr[:100]}")
    except:
        print("📨 Feishu send: skipped (hermes CLI not available)")

if __name__ == '__main__':
    main()