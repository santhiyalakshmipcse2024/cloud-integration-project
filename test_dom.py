from a11y_auditor.dom_analysis import collect, parse, css_selector


def test_collect_and_selectors():
    soup = parse('<html lang="en"><body><div id="a"><p>x</p><p><a href="/z">Z</a></p></div><img src="i.png" alt="i"></body></html>')
    d = collect(soup)
    assert d["lang"] == "en" and d["links"][0]["name"] == "Z" and d["images"][0]["alt"] == "i"
    assert d["links"][0]["selector"] == "div#a > p:nth-of-type(2) > a"
    assert css_selector(soup.img) == "html > body > img"
