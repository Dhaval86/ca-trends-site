import os
from datetime import datetime
import requests
from pytrends.request import TrendReq
from bs4 import BeautifulSoup
from jinja2 import Template
from openai import OpenAI

# -------------------- CONFIG --------------------
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
OPENAI_MODEL = "gpt-5"
ARTICLES_DIR = "articles"
BASE_TEMPLATE = "base_template.html"
HTML_FILE = "index.html"
ARCHIVES_FILE = "archives.html"
SITEMAP_FILE = "sitemap.xml"
BASE_URL = "https://Dhaval86.github.io/ca-trends-site/"  # replace with your GitHub Pages URL

client = OpenAI(api_key=OPENAI_KEY)

# -------------------- FUNCTIONS --------------------

def fetch_trending_words(region="india", limit=5):
    pytrends = TrendReq(hl="en-US", tz=330)
    trending = pytrends.trending_searches(pn=region)
    words = trending[0].head(limit).tolist()
    return words

def generate_article(words):
    prompt = f"Write a 200-word SEO friendly article about Chartered Accountancy in India using these trending words: {words}. Keep it informative and concise."
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def fetch_image(word):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": word,
        "gsrlimit": 1,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    try:
        r = requests.get(url, params=params).json()
        pages = r.get("query", {}).get("pages", {})
        if pages:
            for _, page in pages.items():
                return page["imageinfo"][0]["url"]
    except Exception as e:
        print("⚠️ Image fetch failed:", e)
    return None

def render_template(template_file, title, description, content):
    with open(template_file, "r", encoding="utf-8") as f:
        template = Template(f.read())
    return template.render(title=title, description=description, content=content)

def save_article(date_str, article_html):
    if not os.path.exists(ARTICLES_DIR):
        os.makedirs(ARTICLES_DIR)
    path = os.path.join(ARTICLES_DIR, f"{date_str}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(article_html)
    return path

def update_index(article_html, description, today):
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    else:
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")

    # Update daily article
    container = soup.find("div", {"id": "daily-article"})
    if container:
        container.clear()
        container.append(BeautifulSoup(article_html, "html.parser"))
    else:
        new_div = soup.new_tag("div", id="daily-article")
        new_div.append(BeautifulSoup(article_html, "html.parser"))
        soup.body.append(new_div)

    # Add "View Archives" link
    if not soup.find("a", {"id": "archives-link"}):
        link = soup.new_tag("a", href="archives.html", id="archives-link")
        link.string = "📚 View Archives"
        soup.body.append(link)

    # Save updated index
    html = render_template(BASE_TEMPLATE, f"CA Article {today}", description, str(soup.body))
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ index.html updated")

def update_archives():
    files = sorted(os.listdir(ARTICLES_DIR), reverse=True)
    content = "<h2>Article Archives</h2><ul>"
    for f in files:
        if f.endswith(".html"):
            date = f.replace(".html", "")
            content += f'<li><a href="articles/{f}">{date}</a></li>'
    content += "</ul>"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CA Trends Archives</title>
        <meta name="description" content="Browse past daily CA trending articles from India.">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h2 {{ color: #333; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ margin: 8px 0; }}
            a {{ text-decoration: none; color: #0073e6; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>CA Daily Articles - Archives</h1>
        {content}
        <p><a href="index.html">⬅ Back to Today’s Article</a></p>
    </body>
    </html>
    """

    with open(ARCHIVES_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("📚 archives.html updated")

def update_sitemap():
    urls = []
    # Homepage
    urls.append({"loc": BASE_URL + "index.html", "lastmod": datetime.now().strftime("%Y-%m-%d")})
    # Archives
    urls.append({"loc": BASE_URL + "archives.html", "lastmod": datetime.now().strftime("%Y-%m-%d")})
    # Articles
    if os.path.exists(ARTICLES_DIR):
        for f in sorted(os.listdir(ARTICLES_DIR)):
            if f.endswith(".html"):
                urls.append({"loc": BASE_URL + f"{ARTICLES_DIR}/{f}", "lastmod": f.replace(".html","")})

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sitemap += f"  <url>\n    <loc>{u['loc']}</loc>\n    <lastmod>{u['lastmod']}</lastmod>\n  </url>\n"
    sitemap += "</urlset>"

    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write(sitemap)
    print("🌐 sitemap.xml updated")

# -------------------- MAIN --------------------
if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Generating article for {today}...")

    words = fetch_trending_words()
    article_text = generate_article(words)
    image_url = fetch_image(words[0])
    image_html = f'<img src="{image_url}" alt="{words[0]} image">' if image_url else ""

    article_html = f"<h2>CA Trends - {today}</h2>{image_html}<p>{article_text}</p>"
    article_page_html = render_template(BASE_TEMPLATE, f"CA Article {today}", article_text[:150], article_html)
    save_article(today, article_page_html)

    update_index(article_html, article_text[:150], today)
    update_archives()
    update_sitemap()

    print("✅ Daily CA trends site updated successfully!")
