"""Generate clean-URL pages, 404.html, sitemap.xml and robots.txt for GitHub Pages.

The site is a single-page app (index.html). GitHub Pages serves a folder's
index.html for clean URLs like /campaigns/amazon-injuries/, so this script
writes a copy of index.html into one folder per page, each with its own
<title>, description and social-share preview (Open Graph) tags.

Run after changing data/site.json or index.html:
    python scripts/build_pages.py
The "Build pages" GitHub Action also runs it automatically on every push.

Settings live in data/site.json -> "brand":
    siteUrl   e.g. "https://youthimpactfund.com"   (no trailing slash)
    basePath  "/" for a custom domain or username.github.io,
              "/repo-name/" for a project site at username.github.io/repo-name/
"""
import html
import json
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "data/site.json").read_text(encoding="utf-8"))
PORT = json.loads((ROOT / "data/portfolio.json").read_text(encoding="utf-8"))
B = SITE["brand"]
SITE_URL = B.get("siteUrl", "").rstrip("/")
BASE = "/" + B.get("basePath", "/").strip("/") + "/" if B.get("basePath", "/").strip("/") else "/"
NAME = B["name"]
DEFAULT_DESC = ("Youth Impact Fund is the world's first student-run ESG fund. Students research companies, "
                "manage real portfolios and run shareholder campaigns for a more sustainable world.")
DEFAULT_IMG = "assets/og-image.png"
GENERATED_DIRS = ["about", "team", "curriculum", "portfolio", "reports", "campaigns", "funds",
                  "login", "signup", "privacy", "terms"]


def plain(text, limit=160):
    t = re.sub(r"\[/?[a-z]+(=[^\]]*)?\]", "", text or "", flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= limit else t[: limit - 1].rsplit(" ", 1)[0] + "…"


def pages():
    yield "", NAME, DEFAULT_DESC, DEFAULT_IMG, True
    yield "about/", f"About · {NAME}", plain(SITE["home"]["aboutText"]), DEFAULT_IMG, True
    yield "team/", f"Team · {NAME}", "Meet the students and mentor who lead Youth Impact Fund's research, investing and campaigns.", DEFAULT_IMG, True
    yield "campaigns/", f"Campaigns · {NAME}", "Shareholder campaigns and petitions by Youth Impact Fund on worker safety, privacy, governance and more.", DEFAULT_IMG, True
    for c in SITE["campaigns"]:
        og = f"assets/og/{c['id']}.jpg"  # 1200x630 share image; falls back to the site image
        yield f"campaigns/{c['id']}/", f"{c['title']} · {NAME}", plain(c.get("summary") or c.get("body")), og if (ROOT / og).exists() else DEFAULT_IMG, True
    yield "funds/", f"Funds · {NAME}", "Every Youth Impact Fund fund is designed and managed by a student, each with its own thesis, criteria and holdings.", DEFAULT_IMG, True
    for f in SITE["funds"]:
        first = next((s["body"] for s in f.get("sections", [])), "")
        desc = plain(f"Managed by {f['manager'].strip()}. {first}")
        yield f"funds/{f['slug']}/", f"{f['name']} · {NAME}", desc, DEFAULT_IMG, True
    yield "portfolio/", f"Portfolio · {NAME}", "Holdings, returns and allocation of the main Youth Impact Fund portfolio, updated during market hours.", DEFAULT_IMG, True
    for h in PORT["holdings"]:
        yield f"portfolio/{h['symbol']}/", f"{h['symbol']} · {h['name']} · {NAME}", plain(f"{h['name']} in the Youth Impact Fund portfolio: {h.get('info', {}).get('product', '')}"), DEFAULT_IMG, True
    yield "reports/", f"Reports · {NAME}", f"{len(SITE['reports'])} company, industry, ESG and macroeconomic research reports written by Youth Impact Fund members.", DEFAULT_IMG, True
    yield "curriculum/", f"Curriculum · {NAME}", "Free video lessons on stock investing and shareholder activism from Youth Impact Fund.", DEFAULT_IMG, True
    for c in SITE["curriculum"]:
        title = c["title"].replace("\n", " ")
        yield f"curriculum/{c['slug']}/", f"{title} · {NAME}", plain(c["description"]), DEFAULT_IMG, True
        for i, l in enumerate(c["lessons"], 1):
            yield f"curriculum/{c['slug']}/{i}/", f"{l['title']} · {NAME}", plain(f"Lesson {i} of {title}: {l['title']} ({l['duration']})."), DEFAULT_IMG, True
    yield "privacy/", f"Privacy Policy · {NAME}", "How Youth Impact Fund collects, uses and protects your information.", DEFAULT_IMG, True
    yield "terms/", f"Terms of Service · {NAME}", "The terms for using the Youth Impact Fund website, accounts, petitions and voting.", DEFAULT_IMG, True
    yield "login/", f"Log In · {NAME}", "Log in to Youth Impact Fund.", DEFAULT_IMG, False
    yield "signup/", f"Sign Up · {NAME}", "Create a Youth Impact Fund account.", DEFAULT_IMG, False


def absolute(path):
    return f"{SITE_URL}{BASE}{path}"


def seo_block(path, title, desc, img, index):
    e = lambda v: html.escape(v, quote=True)
    url, image = absolute(path), absolute(img)
    lines = [
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(desc)}">',
        f'<link rel="canonical" href="{e(url)}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{e(NAME)}">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{e(url)}">',
        f'<meta property="og:image" content="{e(image)}">',
    ]
    lines += ['<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">']
    lines += [
        f'<meta name="twitter:card" content="{"summary_large_image"}">',
        f'<meta name="twitter:title" content="{e(title)}">',
        f'<meta name="twitter:description" content="{e(desc)}">',
        f'<meta name="twitter:image" content="{e(image)}">',
    ]
    if not index:
        lines.append('<meta name="robots" content="noindex">')
    return "<!--seo-->\n" + "\n".join(lines) + "\n<!--/seo-->"


def main():
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    src = re.sub(r'<base href="[^"]*">', f'<base href="{BASE}">', src, count=1)
    seo_re = re.compile(r"<!--seo-->.*?<!--/seo-->", re.S)
    assert seo_re.search(src), "index.html is missing the <!--seo--> block"

    for d in GENERATED_DIRS:  # clear old output so removed pages disappear
        shutil.rmtree(ROOT / d, ignore_errors=True)

    urls, n = [], 0
    for path, title, desc, img, index in pages():
        page = seo_re.sub(lambda _: seo_block(path, title, desc, img, index), src, count=1)
        out = ROOT / path / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        n += 1
        if index:
            urls.append(absolute(path))

    # 404.html: any unknown path still loads the app, which shows its own "Page not found".
    nf = seo_re.sub(lambda _: seo_block("", f"Page not found · {NAME}", DEFAULT_DESC, DEFAULT_IMG, False), src, count=1)
    (ROOT / "404.html").write_text(nf, encoding="utf-8")

    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls]
    sm.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {absolute('sitemap.xml')}\n", encoding="utf-8")

    manifest = {
        "name": NAME, "short_name": "YIF", "description": DEFAULT_DESC,
        "start_url": BASE, "scope": BASE, "display": "standalone",
        "background_color": "#EFF3F8", "theme_color": "#003EDD",
        "icons": [
            {"src": "assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "assets/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    (ROOT / "site.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {n} pages, 404.html, sitemap.xml ({len(urls)} URLs), robots.txt, site.webmanifest")


if __name__ == "__main__":
    main()
