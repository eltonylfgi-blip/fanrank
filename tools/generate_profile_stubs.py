"""Generate one crawler-readable FanRank share stub per public profile.

The public app is static, so social crawlers cannot receive profile-specific
Open Graph metadata from query parameters. These committed HTML files expose
that metadata and immediately return human visitors to the real app.
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
STUB_ROOT = ROOT / "p"
PUBLIC_APP_URL = "https://eltonylfgi-blip.github.io/fanrank/"
SOCIAL_IMAGE_URL = PUBLIC_APP_URL + "social-card.png?v=2"
PRESERVED_QUERY_KEYS = ("idea", "ref", "lang", "qa")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SECTIONS_PATH = (
    "fr_sections_stats?select=slug,name,default_language,verification_status"
    "&order=featured_rank.asc"
)
# FR-INV-010 (P0 legal, Tony 17-jul-2026): el ACOPLE VA AL REVES.
# La indexabilidad NO depende de "reclamado / no reclamado": depende de que la pagina
# LLEVE PUESTO el aviso de no-afiliacion + la via de retirada. Sin aviso => noindex
# automatico; con aviso => indexable. Un perfil nuevo al que se le olvide el aviso cae
# solo del lado seguro, en vez de irse a Google desnudo.
NOINDEX_META = '\n  <meta name="robots" content="noindex,follow">'
NON_AFFILIATION_MARK = "no est&aacute; afiliado, patrocinado ni respaldado"
REMOVAL_MARK = "mailto:"
REMOVAL_EMAIL = "eltonylfgi@gmail.com"
# Avisos de propiedad intelectual de terceros (obligatorios para su contenido de fans).
IP_NOTICES = {
    "brawl-stars": "supercell",
    "clash-royale": "supercell",
    "clash-of-clans": "supercell",
    "squad-busters": "supercell",
    "hay-day": "supercell",
    "boom-beach": "supercell",
}
IP_NOTICE_TEXT = {
    "supercell": (
        "Este material no es oficial y no est&aacute; respaldado por Supercell. "
        "Para m&aacute;s informaci&oacute;n, consulta la Pol&iacute;tica de Contenido de Fans de Supercell: "
        '<a href="https://supercell.com/en/fan-content-policy/" rel="noopener noreferrer">'
        "www.supercell.com/fan-content-policy</a>"
    )
}


def is_claimed(profile: dict) -> bool:
    return str(profile.get("verification_status") or "") == "verified"


def removal_mailto(raw_name: str, slug: str) -> str:
    subject = f"FanRank - retirad el perfil de {raw_name}"
    body = (
        f"Hola:\n\nSoy {raw_name}, o su representante autorizado, y pido que se retire "
        f"este perfil de FanRank.\n\nPerfil: {PUBLIC_APP_URL}p/{slug}/\n\nMi nombre: \n"
        "Mi relacion o cargo: \n\n(Lo retiramos sin pedir nada a cambio.)\n"
    )
    query = urllib.parse.urlencode({"subject": subject, "body": body})
    return html.escape(f"mailto:{REMOVAL_EMAIL}?{query}", quote=True)


def legal_block(profile: dict) -> str:
    """Aviso OBLIGATORIO de todo stub de perfil, este reclamado o no.

    Reclamar solo cambia el TITULAR de la frase (reclamar != patrocinar): el aviso de
    no-afiliacion y la via de retirada de 1 tap van SIEMPRE. Es lo que hace indexable
    la pagina (ver page_is_indexable), asi que no puede "olvidarse" sin perder Google.
    """
    slug = str(profile.get("slug") or "")
    raw_name = " ".join(str(profile.get("name") or slug).split())
    name = html.escape(raw_name, quote=True)
    if is_claimed(profile):
        head = f'''
    <p><strong>Perfil reclamado por su titular.</strong> FanRank {NON_AFFILIATION_MARK}
    por las personas y marcas que aparecen aqu&iacute;. Las ideas las escriben y las votan
    sus fans; no son declaraciones de {name}.</p>'''
    else:
        head = f'''
    <p><strong>Perfil no reclamado.</strong> FanRank {NON_AFFILIATION_MARK} por {name}.
    Las ideas las escriben y las votan sus fans a partir de informaci&oacute;n
    p&uacute;blica; no son declaraciones de {name}.</p>'''
    block = head + f'''
    <p><a href="{removal_mailto(raw_name, slug)}">&iquest;Eres {name} o su representante? Pide que lo quitemos</a></p>'''
    ip_holder = IP_NOTICES.get(slug)
    if ip_holder:
        block += f'''
    <p>{IP_NOTICE_TEXT[ip_holder]}</p>'''
    return block


def page_is_indexable(legal: str) -> bool:
    """UNICA puerta a Google: se juzga el aviso YA RENDERIZADO, no un flag de estado."""
    return NON_AFFILIATION_MARK in legal and REMOVAL_MARK in legal
RANKING_PATH = (
    "fr_ranking?select=id,section,title,title_es,ai_score,web_votes,origin_upvotes"
    "&limit=500"
)


def public_api_config() -> tuple[str, str]:
    source = INDEX.read_text(encoding="utf-8")
    url_match = re.search(r'var SB_URL = "([^"]+)";', source)
    key_match = re.search(r'var SB_KEY = "([^"]+)";', source)
    if not url_match or not key_match:
        raise RuntimeError("FanRank public API configuration was not found in index.html")
    return url_match.group(1), key_match.group(1)


def fetch_public_rows(path: str, api_url: str, public_key: str) -> list[dict]:
    request = urllib.request.Request(
        f"{api_url}/rest/v1/{path}",
        headers={
            "apikey": public_key,
            "Accept": "application/json",
            "User-Agent": "FanRank-static-stub-generator/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        rows = json.loads(response.read().decode("utf-8"))
    if not isinstance(rows, list):
        raise RuntimeError(f"Unexpected API response for {path!r}")
    return rows


def number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def ranking_key(idea: dict) -> tuple[float, float, float, float]:
    ai_score = number(idea.get("ai_score"))
    web_votes = number(idea.get("web_votes"))
    origin_upvotes = number(idea.get("origin_upvotes"))
    return (
        ai_score + min(web_votes * 2, 20),
        ai_score,
        web_votes,
        origin_upvotes,
    )


def compact_title(value: object, limit: int = 80) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def render_stub(profile: dict, top_ideas: list[dict]) -> str:
    slug = str(profile["slug"])
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(f"Unsafe public profile slug: {slug!r}")

    raw_name = " ".join(str(profile.get("name") or slug).split())
    name = html.escape(raw_name, quote=True)
    canonical = f"{PUBLIC_APP_URL}p/{slug}/"
    if top_ideas:
        top_title = top_ideas[0].get("title_es") or top_ideas[0].get("title")
        description = f'Lo #1 que piden sus fans: "{compact_title(top_title)}"'
    else:
        description = f"Descubre y vota las mejores ideas para {raw_name} en FanRank."
    escaped_description = html.escape(description, quote=True)
    # El aviso se construye ANTES que el robots: el robots es su CONSECUENCIA.
    legal_html = legal_block(profile)
    robots_meta = "" if page_is_indexable(legal_html) else NOINDEX_META
    preserved_keys = json.dumps(PRESERVED_QUERY_KEYS, separators=(",", ":"))
    slug_js = json.dumps(slug, ensure_ascii=True)

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ideas para {name} &mdash; votadas por sus fans | FanRank</title>
  <meta name="description" content="{escaped_description}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="FanRank">
  <meta property="og:locale" content="es_ES">
  <meta property="og:locale:alternate" content="en_US">
  <meta property="og:title" content="Ideas para {name} &mdash; votadas por sus fans | FanRank">
  <meta property="og:description" content="{escaped_description}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SOCIAL_IMAGE_URL}">
  <meta property="og:image:alt" content="FanRank, ideas votadas por fans con un coraz&oacute;n violeta">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Ideas para {name} &mdash; votadas por sus fans | FanRank">
  <meta name="twitter:description" content="{escaped_description}">
  <meta name="twitter:image" content="{SOCIAL_IMAGE_URL}">
  <meta name="twitter:image:alt" content="FanRank, ideas votadas por fans con un coraz&oacute;n violeta">{robots_meta}
  <script>
  (function(){{
    var source = new URLSearchParams(location.search);
    var target = new URLSearchParams({{s:{slug_js}}});
    {preserved_keys}.forEach(function(key){{
      if(source.has(key)){{target.set(key,source.get(key));}}
    }});
    location.replace("/fanrank/?" + target.toString());
  }})();
  </script>
</head>
<body>
  <main>
    <h1>Ideas para {name}</h1>
    <p>{escaped_description}</p>{legal_html}
    <p>Abriendo FanRank&hellip;</p>
  </main>
  <noscript><a href="/fanrank/?s={slug}">Abrir las ideas para {name} en FanRank</a></noscript>
</body>
</html>
"""


def selftest() -> int:
    """Sin red: prueba que la puerta a Google es el AVISO, no el estado de reclamado."""
    global legal_block
    ok = True
    ideas = [{"title_es": "idea top", "ai_score": 90, "web_votes": 3, "origin_upvotes": 10}]
    libre = {"slug": "orslok", "name": "Orslok"}
    page = render_stub(libre, ideas)
    # NO reclamado pero CON aviso => vuelve a Google (Tony 17-jul: "mejor q salgamos en google").
    ok &= "Perfil no reclamado" in page and NON_AFFILIATION_MARK in page
    ok &= "mailto:eltonylfgi@gmail.com" in page and "Pide que lo quitemos" in page
    ok &= "noindex" not in page
    # Reclamar solo cambia el TITULAR de la frase: aviso y via de retirada SIGUEN.
    claimed = render_stub(dict(libre, verification_status="verified"), ideas)
    ok &= "Perfil no reclamado" not in claimed
    ok &= NON_AFFILIATION_MARK in claimed and "mailto:eltonylfgi@gmail.com" in claimed
    ok &= "noindex" not in claimed
    # Aviso de IP de terceros donde toca (Supercell), y sigue siendo indexable.
    supercell = render_stub({"slug": "brawl-stars", "name": "Brawl Stars"}, ideas)
    ok &= "respaldado por Supercell" in supercell and "noindex" not in supercell
    # EL ACOPLE INVERTIDO, probado: sin aviso => noindex automatico. Imposible
    # publicar en Google un perfil desnudo aunque alguien rompa el generador.
    real_legal_block = legal_block
    legal_block = lambda profile: ""
    try:
        naked = render_stub(libre, ideas)
        ok &= '<meta name="robots" content="noindex,follow">' in naked
    finally:
        legal_block = real_legal_block
    print("SELFTEST:", "OK (8/8)" if ok else "FALLO")
    return 0 if ok else 1


def main() -> int:
    api_url, public_key = public_api_config()
    profiles = fetch_public_rows(SECTIONS_PATH, api_url, public_key)
    ideas = fetch_public_rows(RANKING_PATH, api_url, public_key)

    ideas_by_profile: defaultdict[str, list[dict]] = defaultdict(list)
    for idea in ideas:
        ideas_by_profile[str(idea.get("section") or "")].append(idea)

    generated = 0
    for profile in profiles:
        slug = str(profile.get("slug") or "")
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError(f"Unsafe public profile slug: {slug!r}")
        top_ideas = sorted(ideas_by_profile[slug], key=ranking_key, reverse=True)[:3]
        destination = STUB_ROOT / slug / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_stub(profile, top_ideas), encoding="utf-8", newline="\n")
        generated += 1

    print(f"[OK] stubs={generated} ideas={len(ideas)} root={STUB_ROOT}")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(main())
