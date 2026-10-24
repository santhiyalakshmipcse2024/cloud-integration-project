"""DOM analysis: collect headings, labels, links, images and form controls with selectors + context."""
from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag


def parse(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def css_selector(el: Tag) -> str:
    parts = []
    node = el
    while isinstance(node, Tag) and node.name and node.name != "[document]":
        if node.get("id") and re.fullmatch(r"[A-Za-z][\w\-:.]*", node["id"]):
            parts.append(f"{node.name}#{node['id']}")
            break
        parent = node.parent
        if isinstance(parent, Tag):
            sibs = [s for s in parent.find_all(node.name, recursive=False)]
            idx = next(i for i, s in enumerate(sibs, 1) if s is node)
            parts.append(f"{node.name}:nth-of-type({idx})" if len(sibs) > 1 else node.name)
        else:
            parts.append(node.name)
        node = parent
    return " > ".join(reversed(parts))


def snippet(el: Tag, limit: int = 240) -> str:
    s = re.sub(r"\s+", " ", str(el)).strip()
    return s if len(s) <= limit else s[:limit] + "…"


def context(el: Tag, limit: int = 140) -> str:
    parent = el.parent if isinstance(el.parent, Tag) else el
    txt = re.sub(r"\s+", " ", parent.get_text(" ", strip=True))
    return txt[:limit]


def text_of(el: Tag) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True))


def accessible_name(el: Tag, soup: BeautifulSoup) -> str:
    """Simplified accessible-name computation (aria-labelledby > aria-label > label > content > title)."""
    ids = (el.get("aria-labelledby") or "").split()
    if ids:
        txt = " ".join(text_of(t) for i in ids if (t := soup.find(id=i)))
        if txt.strip():
            return txt.strip()
    if (el.get("aria-label") or "").strip():
        return el["aria-label"].strip()
    if el.name in {"input", "select", "textarea"}:
        if el.get("id"):
            lab = soup.find("label", attrs={"for": el["id"]})
            if lab and text_of(lab):
                return text_of(lab)
        wrap = el.find_parent("label")
        if wrap and text_of(wrap):
            return text_of(wrap)
        if el.name == "input" and el.get("type") in {"submit", "button", "reset"} and el.get("value"):
            return el["value"].strip()
    else:
        content = text_of(el)
        if content:
            return content
        for img in el.find_all("img"):
            if (img.get("alt") or "").strip():
                return img["alt"].strip()
        for svg in el.find_all("svg"):
            t = svg.find("title")
            if t and text_of(t):
                return text_of(t)
    return (el.get("title") or "").strip()


def collect(soup: BeautifulSoup) -> dict:
    def rec(el: Tag, **extra) -> dict:
        return {"selector": css_selector(el), "html": snippet(el), "context": context(el), **extra}

    return {
        "title": text_of(soup.title) if soup.title else "",
        "lang": (soup.html.get("lang") if soup.html else None),
        "headings": [rec(h, level=int(h.name[1]), text=text_of(h)) for h in soup.find_all(re.compile(r"^h[1-6]$"))],
        "links": [rec(a, href=a.get("href"), name=accessible_name(a, soup)) for a in soup.find_all("a", href=True)],
        "images": [rec(i, alt=i.get("alt"), src=i.get("src")) for i in soup.find_all("img")],
        "forms": [rec(c, type=c.get("type", c.name), name=accessible_name(c, soup))
                  for c in soup.find_all(["input", "select", "textarea"]) if c.get("type") != "hidden"],
        "labels": [rec(l, for_=l.get("for"), text=text_of(l)) for l in soup.find_all("label")],
        "buttons": [rec(b, name=accessible_name(b, soup)) for b in soup.find_all("button")],
    }
