#!/usr/bin/env python3
"""Gráficos de linguagens públicas para o README de Gabriel Markus.

Fonte: GET /users/{user}/repos e GET /repos/{owner}/{repo}/languages.
Não acessa repositórios privados nem usa estimativas de proficiência.
"""
import collections
import datetime
import html
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

USER = "gabrielmarkusmt"
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = pathlib.Path("assets")
OUT.mkdir(exist_ok=True)
COLORS = {
    "JavaScript": "#f7df1e", "TypeScript": "#3178c6", "HTML": "#e34f26",
    "CSS": "#8a58b5", "Python": "#3572a5", "C#": "#9b4f96",
    "PHP": "#777bb4", "Shell": "#89e051", "Java": "#b07219",
    "SCSS": "#c6538c", "C++": "#f34b7d", "Go": "#00add8",
}
FALLBACK = ["#a78bfa", "#22d3ee", "#34d399", "#f472b6", "#fbbf24"]
WIDTH = 940

def api(path):
    url = "https://api.github.com" + path
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "GabrielMarkus-README-Stats"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def text(value):
    return html.escape(str(value), quote=True)

def color(name):
    return COLORS.get(name, FALLBACK[sum(name.encode()) % len(FALLBACK)])

def pct(value):
    return f"{value:.2f}%" if 0 < value < .1 else f"{value:.1f}%"

def frame(height, title, subtitle):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{text(title)}">',
        f'<title>{text(title)}</title>',
        '<defs><linearGradient id="back" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#0d1117"/><stop offset="1" stop-color="#201633"/></linearGradient></defs>',
        f'<rect x="1" y="1" width="938" height="{height-2}" rx="18" fill="url(#back)" stroke="#43345f" stroke-width="2"/>',
        '<rect x="30" y="30" width="6" height="44" rx="3" fill="#a78bfa"/>',
        f'<text x="51" y="50" fill="#f5f3ff" font-size="24" font-weight="bold" font-family="Arial,sans-serif">{text(title)}</text>',
        f'<text x="52" y="73" fill="#aea6c7" font-size="14" font-family="Arial,sans-serif">{text(subtitle)}</text>',
        '<path d="M 50 95 H 890" stroke="#3c3654"/>',
    ]

def summary_svg(totals, repo_count):
    ordered = sorted(totals.items(), key=lambda p: (-p[1], p[0].lower()))
    total = sum(totals.values())
    height = 166 + len(ordered) * 56
    parts = frame(height, "LINGUAGENS EM NÚMEROS",
                  "Distribuição por bytes de código em repositórios públicos")
    for index, (name, amount) in enumerate(ordered):
        y = 130 + index * 56
        percentage = 100 * amount / total
        parts.extend([
            f'<circle cx="57" cy="{y-5}" r="5" fill="{color(name)}"/>',
            f'<text x="72" y="{y}" font-size="16" font-weight="bold" fill="#e9e5f9" font-family="Arial,sans-serif">{text(name)}</text>',
            f'<text x="882" y="{y}" text-anchor="end" font-size="16" font-weight="bold" fill="#c4b5fd" font-family="Arial,sans-serif">{pct(percentage)}</text>',
            f'<rect x="50" y="{y+10}" width="832" height="16" rx="8" fill="#302c41"/>',
            f'<rect x="50" y="{y+10}" width="{max(1.5,832*percentage/100):.2f}" height="16" rx="8" fill="{color(name)}"/>',
        ])
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y")
    parts += [f'<text x="50" y="{height-24}" fill="#9f98b4" font-size="12" font-family="Arial,sans-serif">Fonte: GitHub API • {repo_count} repositórios com código • Atualizado: {stamp}</text>', '</svg>']
    return "\n".join(parts) + "\n"

def per_repo_svg(rows):
    rows.sort(key=lambda pair: (-sum(pair[1].values()), pair[0].lower()))
    rows = rows[:8]
    height = 175 + len(rows) * 69
    parts = frame(height, "TECNOLOGIAS POR REPOSITÓRIO",
                  "Composição percentual dos projetos públicos com maior volume de código")
    for i, (name, langs) in enumerate(rows):
        y = 128 + i * 69
        top = sorted(langs.items(), key=lambda pair: -pair[1])
        total = sum(langs.values())
        label = name[:42] + ("…" if len(name) > 42 else "")
        legend = " • ".join(f"{lang} {pct(100*n/total)}" for lang,n in top[:3])
        if len(legend) > 63:
            legend = legend[:62] + "…"
        parts.extend([
            f'<text x="50" y="{y}" fill="#f1edff" font-size="16" font-weight="bold" font-family="Arial,sans-serif">{text(label)}</text>',
            f'<text x="882" y="{y}" text-anchor="end" fill="#aea6c7" font-size="12" font-family="Arial,sans-serif">{text(legend)}</text>',
            f'<rect x="50" y="{y+13}" width="832" height="22" rx="5" fill="#302c41"/>',
        ])
        x = 50.0
        for lang, amount in top:
            segment = 832 * amount / total
            if segment > .2:
                parts.append(f'<rect x="{x:.2f}" y="{y+13}" width="{segment:.2f}" height="22" fill="{color(lang)}"/>')
            x += segment
    parts += [f'<text x="50" y="{height-25}" fill="#9f98b4" font-size="12" font-family="Arial,sans-serif">As barras somam 100% do código detectado em cada projeto; não medem proficiência.</text>', '</svg>']
    return "\n".join(parts) + "\n"

def main():
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{USER}/repos?type=owner&per_page=100&page={page}")
        if not isinstance(batch, list):
            raise RuntimeError("Resposta inválida da API.")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    totals = collections.Counter()
    rows = []
    for repo in repos:
        name = repo["name"]
        if repo.get("private") or repo.get("fork") or name.lower() == USER.lower() or repo.get("size", 0) == 0:
            continue
        route = "/repos/" + USER + "/" + urllib.parse.quote(name, safe="") + "/languages"
        langs = {key: int(value) for key, value in api(route).items() if isinstance(value, int) and value > 0}
        if not langs:
            continue
        totals.update(langs)
        rows.append((name, langs))
    if not totals:
        raise RuntimeError("Sem linguagens detectadas: gráficos existentes preservados.")
    (OUT / "language-usage.svg").write_text(summary_svg(totals, len(rows)), encoding="utf-8")
    (OUT / "repository-languages.svg").write_text(per_repo_svg(rows), encoding="utf-8")
    print(f"Atualizados {len(rows)} repositórios públicos e {len(totals)} linguagens.")

if __name__ == "__main__":
    main()
