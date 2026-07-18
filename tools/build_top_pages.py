"""Build indexable static TOP pages per profile (arsenal F1, 16-jul-2026).

WHY: /p/<slug>/ stubs carry OG metadata but an almost empty body (JS redirect), so
Google has nothing to index. These /top/<slug>/ pages expose the REAL ranking as
static HTML + schema.org ItemList. Honest pSEO: only profiles with >= MIN_IDEAS
real ideas get a page (no cloned empty pages).

Reuses the public-API pattern of tools/generate_profile_stubs.py (reads SB_URL/
SB_KEY from index.html; anon key only sees public views). Writes ONLY under top/
(new, untracked path) - never touches existing files.

Usage:
  python tools/build_top_pages.py                 # fetch live + write top/<slug>/index.html
  python tools/build_top_pages.py --data-file X   # offline (JSON {sections:[],ideas:[]})
  python tools/build_top_pages.py --selftest      # no network, synthetic fixtures
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
TOP_ROOT = ROOT / "top"
PUBLIC_APP_URL = "https://eltonylfgi-blip.github.io/fanrank/"
MIN_IDEAS = 10

SECTIONS_PATH = ("fr_sections_stats?select=slug,name,default_language,verification_status"
                 "&order=featured_rank.asc")

# FR-INV-010 (P0 legal, Tony 17-jul-2026): el ACOPLE VA AL REVES.
# La indexabilidad NO depende de "reclamado / no reclamado": depende de que la pagina
# LLEVE PUESTO el aviso de no-afiliacion + la via de retirada. Sin aviso => noindex
# automatico; con aviso => indexable. Asi un perfil nuevo al que se le olvide el aviso
# cae solo del lado seguro, en vez de irse a Google desnudo.
NOINDEX_META = '\n  <meta name="robots" content="noindex,follow">'
NON_AFFILIATION_MARK = "no est&aacute; afiliado, patrocinado ni respaldado"
REMOVAL_MARK = "mailto:"
REMOVAL_EMAIL = "eltonylfgi@gmail.com"
IP_NOTICES = {"brawl-stars": "supercell", "clash-royale": "supercell",
              "clash-of-clans": "supercell", "squad-busters": "supercell",
              "hay-day": "supercell", "boom-beach": "supercell"}
IP_NOTICE_TEXT = {"supercell": (
    "Este material no es oficial y no est&aacute; respaldado por Supercell. Para m&aacute;s "
    "informaci&oacute;n, consulta la Pol&iacute;tica de Contenido de Fans de Supercell: "
    '<a href="https://supercell.com/en/fan-content-policy/" rel="noopener noreferrer">'
    "www.supercell.com/fan-content-policy</a>")}


def is_claimed(section):
    return str(section.get("verification_status") or "") == "verified"


def removal_mailto(name, slug):
    body = (f"Hola:\n\nSoy {name}, o su representante autorizado, y pido que se retire este "
            f"perfil de FanRank.\n\nPerfil: {PUBLIC_APP_URL}top/{slug}/\n\nMi nombre: \n"
            "Mi relacion o cargo: \n\n(Lo retiramos sin pedir nada a cambio.)\n")
    query = urllib.parse.urlencode({"subject": f"FanRank - retirad el perfil de {name}",
                                    "body": body})
    return html.escape(f"mailto:{REMOVAL_EMAIL}?{query}", quote=True)


def legal_block(section):
    """Aviso OBLIGATORIO de toda pagina de perfil, este reclamada o no.

    Reclamar solo cambia el TITULAR de la frase (reclamar != patrocinar): el aviso de
    no-afiliacion y la via de retirada de 1 tap van SIEMPRE. Es lo que hace indexable
    la pagina (ver page_is_indexable), asi que no puede "olvidarse" sin perder Google.
    """
    slug = str(section.get("slug") or "")
    name = html.escape(" ".join(str(section.get("name") or slug).split()))
    if is_claimed(section):
        head = (f'<p><strong>Perfil reclamado por su titular.</strong> FanRank '
                f'{NON_AFFILIATION_MARK} por las personas y marcas que aparecen '
                f'aqu&iacute;. Las ideas las escriben y las votan sus fans; no son '
                f'declaraciones de {name}.</p>')
    else:
        head = (f'<p><strong>Perfil no reclamado.</strong> FanRank '
                f'{NON_AFFILIATION_MARK} por {name}. Las ideas las escriben y las votan '
                f'sus fans a partir de informaci&oacute;n p&uacute;blica; no son '
                f'declaraciones de {name}.</p>')
    block = (head + f'<p><a href="{removal_mailto(name, slug)}">&iquest;Eres {name} o '
             f'su representante? Pide que lo quitemos</a></p>')
    holder = IP_NOTICES.get(slug)
    if holder:
        block += f"<p>{IP_NOTICE_TEXT[holder]}</p>"
    return block


def page_is_indexable(legal):
    """UNICA puerta a Google: se juzga el aviso YA RENDERIZADO, no un flag de estado."""
    return NON_AFFILIATION_MARK in legal and REMOVAL_MARK in legal
RANKING_PATH = ("fr_ranking?select=id,section,title,title_es,ai_score,web_votes,origin_upvotes"
                "&limit=500")


def public_api_config():
    source = INDEX.read_text(encoding="utf-8")
    url_m = re.search(r'var SB_URL = "([^"]+)";', source)
    key_m = re.search(r'var SB_KEY = "([^"]+)";', source)
    if not url_m or not key_m:
        raise RuntimeError("SB_URL/SB_KEY not found in index.html")
    return url_m.group(1), key_m.group(1)


def fetch_rows(path, api_url, key):
    req = urllib.request.Request(
        f"{api_url}/rest/v1/{path}",
        headers={"apikey": key, "Accept": "application/json",
                 "User-Agent": "FanRank-top-pages/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        rows = json.loads(r.read().decode("utf-8"))
    if not isinstance(rows, list):
        raise RuntimeError(f"unexpected response for {path!r}")
    return rows


def num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def ranking_key(idea):
    # SAME formula as generate_profile_stubs.py (one ranking, one truth)
    return (num(idea.get("ai_score")) + min(num(idea.get("web_votes")) * 2, 20),
            num(idea.get("ai_score")), num(idea.get("web_votes")),
            num(idea.get("origin_upvotes")))


def idea_title(idea):
    return " ".join(str(idea.get("title_es") or idea.get("title") or "").split())


def supports(idea):
    return int(num(idea.get("web_votes")) + num(idea.get("origin_upvotes")))


def build_page(section, ideas, today):
    slug = section["slug"]
    name = section.get("name") or slug
    ideas = sorted(ideas, key=ranking_key, reverse=True)
    n = len(ideas)
    page_url = f"{PUBLIC_APP_URL}top/{slug}/"
    app_url = f"{PUBLIC_APP_URL}?s={slug}&ref=top-{slug}"
    h1 = f"Las {n} ideas que los fans piden para {name} (ranking votado)"
    desc = f'Lo #1 que piden sus fans: "{idea_title(ideas[0])}". Ranking real con {n} ideas votadas.'

    items = []
    for i, idea in enumerate(ideas, 1):
        items.append({"@type": "ListItem", "position": i,
                      "name": idea_title(idea), "url": app_url})
    # El aviso se construye ANTES que el robots: el robots es su CONSECUENCIA.
    legal = legal_block(section)
    robots = "" if page_is_indexable(legal) else NOINDEX_META
    legal_html = f'<section class="legal">{legal}</section>' if legal else ""

    ld = {"@context": "https://schema.org", "@type": "ItemList",
          "name": h1, "url": page_url, "numberOfItems": n,
          "dateModified": today, "itemListElement": items}

    lis = []
    for i, idea in enumerate(ideas, 1):
        cls = ' class="podio"' if i <= 3 else ""
        ap = supports(idea)
        ap_txt = f'<span class="ap">{ap:,} apoyos</span>'.replace(",", ".") if ap else ""
        lis.append(f'    <li{cls}><span class="t">{html.escape(idea_title(idea))}</span> {ap_txt}</li>')

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(h1)} | FanRank</title>
  <meta name="description" content="{html.escape(desc)}">
  <link rel="canonical" href="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="FanRank">
  <meta property="og:title" content="{html.escape(h1)}">
  <meta property="og:description" content="{html.escape(desc)}">
  <meta property="og:url" content="{page_url}">
  <meta property="og:image" content="{PUBLIC_APP_URL}social-card.png?v=2">{robots}
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin:0; background:#0d0b14; color:#efe9ff; font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif; }}
    main {{ max-width:680px; margin:0 auto; padding:32px 20px 48px; }}
    h1 {{ font-size:1.6rem; line-height:1.25; margin:0 0 4px; }}
    h1 em {{ color:#ff4d6d; font-style:normal; }}
    .sub {{ color:#a99fc4; margin:0 0 22px; font-size:.95rem; }}
    ol {{ padding-left:0; counter-reset: rank; list-style:none; margin:0; }}
    li {{ counter-increment: rank; display:flex; gap:12px; align-items:baseline;
         padding:10px 12px; border-bottom:1px solid #221c33; }}
    li::before {{ content: counter(rank); min-width:2ch; text-align:right;
                 color:#7c6fa8; font-weight:700; }}
    li.podio {{ background:linear-gradient(90deg,#1a1428,transparent); border-radius:10px; }}
    li.podio::before {{ color:#ffd166; font-size:1.15em; }}
    .t {{ flex:1; }}
    .ap {{ color:#8ef0c0; font-size:.85rem; white-space:nowrap; }}
    .cta {{ display:block; margin:26px 0 0; text-align:center; background:#ff4d6d; color:#fff;
           text-decoration:none; padding:14px 18px; border-radius:12px; font-weight:700; }}
    .cta:hover {{ transform:translateY(-1px); box-shadow:0 6px 24px #ff4d6d55; }}
    footer {{ margin-top:26px; color:#7c6fa8; font-size:.8rem; text-align:center; }}
    footer a {{ color:#a99fc4; }}
    .legal {{ margin:22px 0 0; padding:13px 15px; border:1px solid #2b2340; border-radius:12px;
             background:#141024; color:#c9c1e0; font-size:.83rem; }}
    .legal p {{ margin:0 0 8px; }}
    .legal p:last-child {{ margin:0; }}
    .legal a {{ color:#8bb8ff; }}
  </style>
</head>
<body>
  <main>
    <h1>Las {n} ideas que los fans piden para <em>{html.escape(name)}</em> (ranking votado)</h1>
    <p class="sub">Ranking real del tabl&oacute;n p&uacute;blico de FanRank &middot; actualizado el {today}</p>
    <ol>
{chr(10).join(lis)}
    </ol>
    <a class="cta" href="{app_url}">Vota o propone la tuya en FanRank &rarr;</a>
    {legal_html}
    <footer>Datos en vivo del tabl&oacute;n <a href="{app_url}">FanRank &middot; {html.escape(name)}</a>.
    Los apoyos suman votos web y upvotes de origen de cada idea.</footer>
  </main>
</body>
</html>
"""


def build_all(data, out_root, today=None):
    today = today or date.today().isoformat()
    by_section = {}
    for idea in data.get("ideas", []):
        by_section.setdefault(idea.get("section"), []).append(idea)
    written, skipped = [], []
    urls = []
    for section in data.get("sections", []):
        slug = section.get("slug") or ""
        ideas = by_section.get(slug, [])
        if len(ideas) < MIN_IDEAS or not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug):
            skipped.append((slug, len(ideas)))
            continue
        d = out_root / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(build_page(section, ideas, today), encoding="utf-8")
        written.append((slug, len(ideas)))
        # Al sitemap solo lo que de verdad lleva el aviso puesto (misma puerta que el robots).
        if page_is_indexable(legal_block(section)):
            urls.append(f"{PUBLIC_APP_URL}top/{slug}/")
    if True:
        sm = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for u in urls:
            sm.append(f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n  </url>")
        sm.append("</urlset>")
        out_root.mkdir(parents=True, exist_ok=True)
        (out_root / "sitemap-top.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    return written, skipped


def selftest():
    import tempfile
    global legal_block
    ok = True
    data = {"sections": [{"slug": "grande", "name": "Grande"},
                         {"slug": "vacio", "name": "Vacio"}],
            "ideas": ([{"id": i, "section": "grande", "title": f"idea {i}",
                        "title_es": f"idea {i}", "ai_score": 50 + i,
                        "web_votes": 1 if i == 3 else 0, "origin_upvotes": 100 * i}
                       for i in range(1, 13)]
                      + [{"id": 99, "section": "vacio", "title": "x", "title_es": "x",
                          "ai_score": 1, "web_votes": 0, "origin_upvotes": 0}])}
    out = Path(tempfile.mkdtemp()) / "top"
    written, skipped = build_all(data, out, today="2026-07-16")
    ok &= written == [("grande", 12)]
    ok &= ("vacio", 1) in skipped                      # GATE < MIN_IDEAS
    page = (out / "grande" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    ld = json.loads(m.group(1))
    ok &= ld["@type"] == "ItemList" and ld["numberOfItems"] == 12
    ok &= ld["itemListElement"][0]["position"] == 1
    ok &= "Las 12 ideas" in page and 'lang="es"' in page
    # FR-INV-010 (Tony 17-jul): 'grande' NO esta reclamado pero LLEVA el aviso puesto
    # => vuelve a Google y al sitemap. Salir en Google no depende de reclamar.
    ok &= "Perfil no reclamado" in page and NON_AFFILIATION_MARK in page and "mailto:" in page
    ok &= "noindex" not in page
    ok &= (out / "sitemap-top.xml").read_text(encoding="utf-8").count("<loc>") == 1
    # Reclamar solo cambia el TITULAR de la frase: aviso y via de retirada SIGUEN.
    claimed_data = {"sections": [dict(data["sections"][0], verification_status="verified")],
                    "ideas": data["ideas"]}
    out2 = Path(tempfile.mkdtemp()) / "top"
    build_all(claimed_data, out2, today="2026-07-16")
    claimed_page = (out2 / "grande" / "index.html").read_text(encoding="utf-8")
    ok &= "Perfil no reclamado" not in claimed_page
    ok &= NON_AFFILIATION_MARK in claimed_page and "mailto:" in claimed_page
    ok &= "noindex" not in claimed_page
    ok &= (out2 / "sitemap-top.xml").read_text(encoding="utf-8").count("<loc>") == 1
    # EL ACOPLE INVERTIDO, probado: si la pagina se queda SIN aviso, cae SOLA a noindex
    # y fuera del sitemap. Es imposible publicar en Google un perfil desnudo.
    real_legal_block = legal_block
    legal_block = lambda section: ""
    try:
        out3 = Path(tempfile.mkdtemp()) / "top"
        build_all(data, out3, today="2026-07-16")
        naked = (out3 / "grande" / "index.html").read_text(encoding="utf-8")
        ok &= '<meta name="robots" content="noindex,follow">' in naked
        ok &= (out3 / "sitemap-top.xml").read_text(encoding="utf-8").count("<loc>") == 0
    finally:
        legal_block = real_legal_block
    print("SELFTEST:", "OK (14/14)" if ok else "FALLO")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--data-file" in sys.argv:
        data = json.loads(Path(sys.argv[sys.argv.index("--data-file") + 1])
                          .read_text(encoding="utf-8"))
    else:
        api_url, key = public_api_config()
        data = {"sections": fetch_rows(SECTIONS_PATH, api_url, key),
                "ideas": fetch_rows(RANKING_PATH, api_url, key)}
    written, skipped = build_all(data, TOP_ROOT)
    for slug, n in written:
        print(f"[OK] top/{slug}/index.html  ({n} ideas)")
    for slug, n in skipped:
        print(f"[GATE] {slug}: {n} ideas < {MIN_IDEAS} -> sin pagina (pSEO honesto)")


if __name__ == "__main__":
    main()
