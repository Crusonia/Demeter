"""CI headless smoke: the offline report must execute Plotly without network access."""

from pathlib import Path
import argparse

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--report", type=Path, default=Path("outputs/observability/index.html"))
parser.add_argument("--figures", type=int, default=37)
args = parser.parse_args()
report = args.report.resolve()
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # Block network: all report assets must already be embedded in the document.
    page.route("https://**/*", lambda route: route.abort())
    page.route("http://**/*", lambda route: route.abort())
    page.goto(report.as_uri())
    page.wait_for_function(
        "expected => document.querySelectorAll('.js-plotly-plot').length === expected && "
        "Array.from(document.querySelectorAll('.js-plotly-plot')).every(p => p._fullLayout)",
        arg=args.figures,
    )
    assert not errors, errors
    assert page.get_by_text("VALIDATION ONLY — NOT SCIENTIFIC FINDINGS.", exact=False).count() >= 1
    page.screenshot(path=str(report.parent / "browser-smoke.png"), full_page=False)
    # A historical panel and a dependency graph must also have rendered geometry.
    assert page.locator("#plot-dependencies svg.main-svg").count() > 0
    assert page.locator("#plot-history_e0_both_sexes svg.main-svg").count() > 0
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(report.parent / "browser-mobile.png"), full_page=False)
    browser.close()
print(f"{args.figures} Plotly figures rendered offline without JavaScript errors")
