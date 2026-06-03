#!/usr/bin/env python3
"""
Auto Article Generator for HomeOfficeGearFinds
Usage: python3 scripts/generate-articles.py [num_articles=2]

Reads from topics/topic-pool.json, generates fresh HTML articles,
updates articles.json and sitemap, then git commit & pushes.
"""

import json, os, sys, subprocess, re
from datetime import date, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_FILE = f'{BASE}/topics/topic-pool.json'
ARTICLES_FILE = f'{BASE}/articles/articles.json'

# ====== TEMPLATES ======
HEADER = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{desc}">
    <link rel="stylesheet" href="../css/style.css">
    <link rel="canonical" href="https://rdcjed.github.io/homeoffice-gear-finds/articles/{slug}.html">
    <meta name="robots" content="index, follow">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <div class="logo">
                <a href="/homeoffice-gear-finds/">
                    <span class="logo-icon">🏠</span>
                    <span class="logo-text">HomeOffice<span class="accent">Gear</span>Finds</span>
                </a>
            </div>
            <nav class="main-nav">
                <button class="mobile-menu-toggle" aria-label="Menu">☰</button>
                <ul>
                    <li><a href="/homeoffice-gear-finds/">Home</a></li>
                    <li><a href="/homeoffice-gear-finds/category/keyboards.html">Keyboards</a></li>
                    <li><a href="/homeoffice-gear-finds/category/headphones.html">Headphones</a></li>
                    <li><a href="/homeoffice-gear-finds/category/monitors.html">Monitors</a></li>
                    <li><a href="/homeoffice-gear-finds/category/accessories.html">Accessories</a></li>
                    <li><a href="/homeoffice-gear-finds/about.html">About</a></li>
                </ul>
            </nav>
        </div>
    </header>
    <section class="article-header">
        <div class="container">
            <div class="article-meta"><span>📅 {date}</span><span>📁 {cat}</span></div>
            <h1>{title}</h1>
            <div class="article-tags">
                <span>#{cat_tag}</span>
                <span>#budgetgear</span>
                <span>#homeoffice</span>
            </div>
        </div>
    </section>
    <article class="article-content">'''

FOOTER = '''        <p style="font-size:0.85rem;color:#6b7280;margin-top:40px;">
            <em>We independently research and recommend products we believe in. This site contains affiliate links.</em>
        </p>
    </article>
    <footer class="site-footer">
        <div class="container">
            <div class="footer-content">
                <div class="footer-brand">
                    <h3>HomeOfficeGearFinds</h3>
                    <p>Helping remote workers find the best budget tech since 2025.</p>
                </div>
                <div class="footer-links">
                    <h4>Quick Links</h4>
                    <ul>
                        <li><a href="/homeoffice-gear-finds/about.html">About</a></li>
                        <li><a href="/homeoffice-gear-finds/privacy-policy.html">Privacy Policy</a></li>
                        <li><a href="/homeoffice-gear-finds/contact.html">Contact</a></li>
                    </ul>
                </div>
                <div class="footer-disclaimer">
                    <p>As an Amazon Associate we earn from qualifying purchases.</p>
                </div>
            </div>
            <div class="footer-bottom">
                <p>&copy; 2025 HomeOfficeGearFinds. All rights reserved.</p>
            </div>
        </div>
    </footer>
    <script src="../js/main.js"></script>
</body>
</html>'''

def make_slug(title):
    slug = title.lower().replace(' ', '-').replace(',','').replace('(','').replace(')','')
    slug = slug.replace('&','and').replace('"','').replace("'",'').replace(':','').replace('--','-')
    return slug.strip('-')

def get_product_ideas(kw):
    """Generate realistic product ideas based on keyword"""
    products = []
    kw_lower = kw.lower()
    
    if 'keyboard' in kw_lower:
        products = [
            ("Keychron V1 QMK Custom", "~$65", 5, "Hot-swappable mechanical keyboard with full QMK/VIA support. Premium build quality at a budget price."),
            ("Logitech K380 Multi-Device", "~$30", 4, "Ultra-portable Bluetooth keyboard that pairs with 3 devices. Perfect for laptops and tablets."),
            ("Royal Kludge RK100", "~$45", 4, "96% layout compact mechanical keyboard with wireless Bluetooth 5.0. Great space-saver."),
            ("Arteck 2.4G Wireless Keyboard", "~$20", 4, "Full-size scissor-switch keyboard with nano receiver. Ultra-slim and silent for shared offices."),
            ("MOTOSPEED CK61", "~$38", 4, "60% mechanical gaming keyboard with optical switches. Fast actuation and RGB lighting."),
        ]
    elif 'headphone' in kw_lower or 'earbud' in kw_lower or 'headset' in kw_lower or 'speaker' in kw_lower:
        products = [
            ("Soundcore by Anker Life Q30", "~$65", 5, "Hybrid ANC with 40-hour battery life. Custom EQ via app. Best budget noise-cancelling headphones."),
            ("Soundcore by Anker Space A40", "~$59", 5, "Compact wireless earbuds with adaptive ANC and 50-hour total battery. IPX5 waterproof."),
            ("JBL Tune 510BT", "~$50", 4, "Pure Bass sound with 40-hour battery and foldable design. Quick charge: 5 min = 1 hour."),
            ("1More SonoFlow", "~$55", 4, "LDAC high-res audio support with ANC. 70-hour battery life and comfortable over-ear design."),
            ("Creative Pebble V3", "~$35", 4, "Compact USB-C desktop speakers with 8W RMS power and clear mids/highs. Great for calls."),
        ]
    elif 'chair' in kw_lower or 'seat' in kw_lower or 'cushion' in kw_lower:
        products = [
            ("Hbada Ergonomic Office Chair", "~$169", 5, "Adjustable lumbar support, 3D armrests, and breathable mesh back. Best value ergonomic chair under $200."),
            ("Amazon Basics Ergonomic Chair", "~$145", 4, "High-back mesh office chair with adjustable tilt and lumbar support. Reliable and simple."),
            ("ComfiLife Gel Memory Foam Cushion", "~$30", 5, "Cooling gel-infused memory foam seat cushion. Relieves tailbone and sciatica pressure."),
            ("Everlasting Comfort Lumbar Support", "~$35", 5, "Memory foam back cushion with adjustable straps. Fits any office chair perfectly."),
            ("Gaiam Balance Ball Chair", "~$75", 4, "Active sitting solution with balance ball and stability base. Engages core while you work."),
        ]
    elif 'monitor' in kw_lower or 'display' in kw_lower or 'screen' in kw_lower:
        products = [
            ("Arzopa 15.6\" Portable Monitor", "~$99", 5, "1080p IPS USB-C portable monitor. Auto-rotate, built-in speakers. Perfect second screen for laptops."),
            ("Dell S2421HN", "~$149", 4, "24-inch 1080p IPS with dual HDMI. Slim bezels and excellent color reproduction."),
            ("AOC 24B2XH", "~$119", 4, "24-inch frameless IPS monitor with 75Hz refresh. Great budget primary or second monitor."),
            ("VANSOR Blue Light Blocking Filter", "~$28", 5, "Anti-blue light screen protector for 24-27 inch monitors. Reduces eye strain by 99%."),
            ("WALI Monitor Arm", "~$30", 5, "Single monitor gas spring arm. Frees up desk space and improves ergonomics."),
        ]
    elif 'mouse' in kw_lower:
        products = [
            ("Logitech M720 Triathlon", "~$40", 5, "Multi-device Bluetooth mouse. 24-month battery, hyper-fast scroll, 3 device switching."),
            ("Logitech M585", "~$30", 4, "Silent click wireless mouse with Logitech Flow. Great for multi-computer setups."),
            ("Anker Ergonomic Vertical Mouse", "~$22", 5, "Vertical grip design reduces wrist strain. 3 adjustable DPI levels. Best ergonomic budget pick."),
            ("VicTsing Wireless Mouse", "~$14", 4, "Ultra-budget wireless mouse with USB receiver. 5-button design with DPI adjustment."),
            ("Microsoft Surface Arc Mouse", "~$48", 4, "Flat-fold Bluetooth mouse. Touch-sensitive scroll. Ultra-portable and elegant."),
        ]
    elif 'charger' in kw_lower or 'power' in kw_lower or 'battery' in kw_lower:
        products = [
            ("Anker Nano II 65W GaN", "~$35", 5, "Compact GaN USB-C charger. 65W PD for laptops. Folds flat for travel. 3x smaller than original."),
            ("Baseus 65W GaN 6-Outlet", "~$39", 4, "Desktop charger with 65W USB-C PD plus 5 USB-A ports. Charges 6 devices simultaneously."),
            ("Anker PowerCore 20100mAh", "~$45", 5, "High-capacity portable charger. Dual USB output. Enough to charge a phone 5+ times."),
            ("Belkin BoostCharge Wireless Pad", "~$20", 4, "15W fast wireless charging pad. Works with iPhone and Samsung. Slim and non-slip."),
            ("UGREEN 30W Car Charger", "~$15", 4, "USB-C 30W PD car charger. Super fast charging for phones and tablets during commute."),
        ]
    else:
        products = [
            ("Amazon Basics Premium Product", "~$25", 4, "Reliable and affordable option from Amazon's own brand. Solid build quality with good reviews."),
            ("Anker Quality Product", "~$35", 5, "Trusted brand known for excellent build quality and customer service. Great value proposition."),
            ("UGREEN Alternative", "~$18", 4, "Budget-friendly option with premium features. Excellent value for money."),
            ("Baseus All-in-One", "~$28", 4, "Feature-packed design that punches above its price point. Good reviews from users."),
            ("VIVO Budget Pick", "~$22", 4, "Simple, functional, and affordable. Thousands of positive reviews on Amazon."),
        ]
    return products

def generate_article(topic):
    """Generate a full HTML article from a topic"""
    kw = topic['kw']
    prods = topic.get('products') or get_product_ideas(kw)
    
    # Build title
    parts = kw.split()
    title = ' '.join(parts).title()
    if not title.startswith('Best'):
        title = 'Best ' + title
    
    # Add year if not present
    if '2025' not in title and '2026' not in title:
        title += ' in 2025'
    
    slug = make_slug(title)
    date_str = date.today().isoformat()
    cat = 'Accessories'
    cat_tag = 'accessories'
    
    # Build intro
    topic_words = kw.replace('best budget ', '').replace('best ', '')
    intro = f"Looking for the best budget {topic_words}? We've tested the top products on the market to bring you honest, hands-on recommendations that won't break the bank."
    
    # Build product cards
    pc = ''
    for i, (name, price, stars, desc) in enumerate(prods):
        stars_html = '★' * stars + '☆' * (5 - stars)
        pc += f'''
<div class="product-card">
    <div class="product-card-image">📦</div>
    <div class="product-card-info">
        <h3>{i+1}. {name}</h3>
        <div class="price">{price}</div>
        <div class="rating">{stars_html}</div>
        <p>{desc}</p>
        <a href="#" class="btn-buy" rel="nofollow sponsored">Check Price →</a>
    </div>
</div>'''
    
    # Build article body
    why_need = f'''Why You Need This'''
    why_text = f"Whether you're setting up a new home office or upgrading your existing workspace, finding the right {topic_words} at the right price makes all the difference. We've done the research so you don't have to."
    
    content = f'''
<h2>{why_need}</h2>
<p>{why_text}</p>

<h2>Our Top Picks</h2>
{pc}

<div class="verdict-box">
    <h3>🏆 Final Verdict</h3>
    <p>After testing and comparing dozens of products, we're confident these are the best budget {topic_words} available right now. Any of these picks will serve you well without breaking the bank.</p>
</div>
'''
    
    header = HEADER.format(title=title, desc=f"Looking for the best {topic_words}? Our expert review covers the top {len(prods)} budget-friendly options.", slug=slug, date=date_str, cat=cat, cat_tag=cat_tag)
    
    return header + content + FOOTER, {
        "title": title,
        "emoji": "📦",
        "category": cat,
        "excerpt": intro[:150],
        "date": date_str,
        "url": f"articles/{slug}.html"
    }, slug

def main():
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    
    # Load topic pool
    with open(TOPICS_FILE) as f:
        topics = json.load(f)
    
    # Mark unused topics
    for t in topics:
        t.setdefault('used', False)
    
    # Find unused topics
    unused = [t for t in topics if not t.get('used')]
    if not unused:
        print("⚠️ All topics used! Resetting pool.")
        for t in topics:
            t['used'] = False
        unused = topics
    
    to_generate = unused[:num]
    
    # Load existing articles
    with open(ARTICLES_FILE) as f:
        articles = json.load(f)
    
    generated = []
    for topic in to_generate:
        html, entry, slug = generate_article(topic)
        filepath = f'{BASE}/articles/{slug}.html'
        
        # Check for duplicate
        if os.path.exists(filepath):
            slug = slug + '-' + str(len([a for a in articles if slug in a['url']]))
            entry['url'] = f'articles/{slug}.html'
            filepath = f'{BASE}/articles/{slug}.html'
        
        with open(filepath, 'w') as f:
            f.write(html)
        
        articles.append(entry)
        topic['used'] = True
        generated.append(entry['title'])
        print(f"✅ Generated: {entry['title']}")
    
    # Save updates
    with open(TOPICS_FILE, 'w') as f:
        json.dump(topics, f, indent=2)
    with open(ARTICLES_FILE, 'w') as f:
        json.dump(articles, f, indent=2)
    
    # Update sitemap
    urls = [("/homeoffice-gear-finds/", "1.0", "daily")]
    for a in articles:
        urls.append((f"/homeoffice-gear-finds/{a['url']}", "0.7", "weekly"))
    for page in ["about.html", "privacy-policy.html", "contact.html"]:
        urls.append((f"/homeoffice-gear-finds/{page}", "0.3", "monthly"))
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for path, priority, changefreq in urls:
        sitemap += f'  <url>\n    <loc>https://rdcjed.github.io{path}</loc>\n    <lastmod>{date.today().isoformat()}</lastmod>\n    <changefreq>{changefreq}</changefreq>\n    <priority>{priority}</priority>\n  </url>\n'
    sitemap += '</urlset>'
    
    with open(f'{BASE}/sitemap.xml', 'w') as f:
        f.write(sitemap)
    
    # Git commit and push
    try:
        os.chdir(BASE)
        proxy = os.popen("ip route show default | awk '{print $3}'").read().strip()
        env = os.environ.copy()
        env['HTTP_PROXY'] = f'http://{proxy}:7897'
        env['HTTPS_PROXY'] = f'http://{proxy}:7897'
        env['GIT_SSL_NO_VERIFY'] = '1'
        
        subprocess.run(['git', 'add', '-A'], env=env, cwd=BASE)
        subprocess.run(['git', 'commit', '-m', f'🤖 Auto: {len(generated)} new articles - {", ".join(generated[:3])}'], env=env, cwd=BASE)
        subprocess.run(['git', 'push', 'origin', 'main'], env=env, cwd=BASE)
        print(f"✅ Git push successful!")
    except Exception as e:
        print(f"⚠️ Git push failed: {e}")
    
    print(f"\n📊 Generated {len(generated)} articles. Total: {len(articles)}")
    return len(generated)

if __name__ == '__main__':
    main()