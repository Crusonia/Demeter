"""Exercise the local launcher and real model reruns in desktop/mobile Chromium."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def verify() -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "outputs/explorer-browser"
    artifacts.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="runs-", dir=artifacts))
    log = destination / "launcher.log"
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "demeter.cli",
                "explore",
                "--no-browser",
                "--destination",
                str(destination),
            ],
            cwd=root,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = time.monotonic() + 180
            url = None
            while time.monotonic() < deadline:
                match = re.search(
                    r"http://127\.0\.0\.1:\d+/#token=\S+", log.read_text(encoding="utf-8")
                )
                if match:
                    url = match[0]
                    break
                if process.poll() is not None:
                    raise AssertionError(log.read_text(encoding="utf-8"))
                time.sleep(0.1)
            assert url, "Launcher did not supply a browser link"
            # The launcher prints the URL just before Uvicorn finishes startup.
            from urllib.request import urlopen

            for _ in range(100):
                try:
                    with urlopen(url.split("#")[0], timeout=1):
                        break
                except OSError:
                    time.sleep(0.1)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.set_default_timeout(15000)
                expect.set_options(timeout=20000)
                errors, external = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                origin = urlsplit(url).netloc

                def local_only(route):
                    if urlsplit(route.request.url).netloc != origin:
                        external.append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()

                page.route("http**://**/*", local_only)
                page.goto(url)
                nav = page.get_by_role("navigation", name="Main navigation")
                expect(page.get_by_role("button", name="Run this experiment")).to_be_enabled()
                assert "#token" not in page.url
                page.screenshot(path=str(artifacts / "learn-desktop.png"))
                nav.get_by_role("button", name="Experiment", exact=True).click()
                page.get_by_label("Model years", exact=True).fill("2")
                page.get_by_label("Experiment name", exact=True).fill("Browser first experiment")
                page.get_by_label("Your prediction", exact=True).fill(
                    "The response will take time."
                )
                page.get_by_role("button", name="Check assumptions", exact=True).click()
                expect(page.get_by_role("status").filter(has_text="valid")).to_be_visible()
                page.get_by_role("button", name="Run experiment →", exact=True).click()
                expect(page.get_by_role("button", name="Use these assumptions")).to_be_visible(
                    timeout=180000
                )
                page.wait_for_function("document.querySelector('.js-plotly-plot')?._fullLayout")
                expect(page.get_by_text("How to read this", exact=True)).to_be_visible()
                page.get_by_label(re.compile("Compare reference as dotted lines")).check()
                page.wait_for_function(
                    "document.querySelector('.js-plotly-plot').data.some(t => t.name.startsWith('Reference'))"
                )
                page.locator(".chart-story").screenshot(path=str(artifacts / "chart-desktop.png"))
                views = page.get_by_role("group", name="Chart views")
                views.get_by_role("button", name="Data", exact=True).click()
                expect(page.locator(".chart-pane tbody tr").first).to_be_visible()
                with page.expect_download() as download:
                    page.get_by_role("button", name="↓ CSV", exact=True).click()
                download.value.save_as(artifacts / "stocks.csv")
                assert "healthy" in (artifacts / "stocks.csv").read_text()
                views.get_by_role("button", name="Sources", exact=True).click()
                expect(page.locator(".chart-pane .source").first).to_be_visible()
                page.get_by_text("Test your explanation", exact=True).click()
                expect(page.get_by_text("Predict before running", exact=True)).to_be_visible()
                panel = page.locator(".chart-pane > .source-list")
                mechanism = panel.get_by_role(
                    "combobox", name="Evidence for a mechanism", exact=True
                )
                mechanism.select_option(label="upf exposure → lagged response")
                expect(panel.locator(".source")).to_have_count(2)
                expect(panel.get_by_text("diet lag years", exact=True)).to_be_visible()
                panel.get_by_text("Saved scenario assumptions", exact=True).click()
                expect(panel.locator(".scenario-assumptions")).to_contain_text(
                    "Browser first experiment"
                )
                panel.get_by_text("Unresolved evidence and limits", exact=True).click()
                expect(panel).to_contain_text("no clinical dose range, saturation or timing")
                page.screenshot(path=str(artifacts / "mechanism-evidence-desktop.png"))
                mechanism.select_option("")
                picker = page.get_by_role("combobox", name="Question / chart", exact=True)
                picker.select_option("history_e0_both_sexes")
                views.get_by_role("button", name="Sources", exact=True).click()
                expect(panel.locator(".source")).to_have_count(1)
                expect(panel.get_by_text("U.S., all races, Both Sexes", exact=True)).to_be_visible()
                expect(panel.get_by_text("beta upf progression", exact=True)).to_have_count(0)
                picker.select_option("stocks")
                page.get_by_role(
                    "textbox", name="Your explanation & next question", exact=True
                ).fill("I will challenge the lag next.")
                page.get_by_role("button", name="Save reflection", exact=True).click()
                expect(
                    page.get_by_text("Reflection saved alongside this experiment.")
                ).to_be_visible()
                with page.expect_download() as download:
                    page.get_by_role("button", name="↓ Offline report", exact=True).click()
                download.value.save_as(artifacts / "report.html")
                offline = browser.new_page()
                offline.route("http**://**/*", lambda route: route.abort())
                offline.goto((artifacts / "report.html").as_uri())
                offline.locator("#stocks .chart-evidence > summary").click()
                expect(offline.locator("#stocks .chart-evidence > .source").first).to_be_visible()
                offline.locator("#stocks .scenario-assumptions > summary").click()
                expect(offline.locator("#stocks .scenario-assumptions")).to_contain_text(
                    "Browser first experiment"
                )
                expect(offline.locator("#stocks .chart-evidence")).to_contain_text(
                    "no clinical dose range, saturation or timing"
                )
                expect(offline.locator("#stocks .teaching")).to_contain_text(
                    "Predict before running"
                )
                offline.close()
                assert "Why it happens in this model" in (artifacts / "report.html").read_text(
                    encoding="utf-8"
                )
                first_path = next(destination.glob("*/request.json"))
                original = first_path.read_bytes()
                first_id = first_path.parent.name
                page.get_by_role("button", name="Use these assumptions").click()
                page.get_by_label("Experiment name", exact=True).fill("Browser changed assumption")
                page.get_by_label("UPF reduction from reference (%)").fill("20")
                page.locator("summary").filter(has_text="Advanced assumptions").click()
                page.get_by_label("beta_upf_progression: nominal", exact=True).fill("0.5")
                page.get_by_label("Compare with").select_option(first_id)
                nav.get_by_role("button", name="Explore", exact=True).click()
                expect(
                    page.get_by_text("Your editor has different assumptions.", exact=False)
                ).to_be_visible()
                nav.get_by_role("button", name="Experiment", exact=True).click()
                page.get_by_role("button", name="Run experiment →", exact=True).click()
                expect(page.get_by_role("button", name="Use these assumptions")).to_be_visible(
                    timeout=180000
                )
                assert first_path.read_bytes() == original
                saved = [
                    json.loads(path.read_text()) for path in destination.glob("*/request.json")
                ]
                assert len(saved) == 2 and any(r["reference_id"] == first_id for r in saved)
                second = next(
                    path.parent
                    for path in destination.glob("*/request.json")
                    if json.loads(path.read_text())["reference_id"] == first_id
                )
                experiment_charts = json.loads((second / "report/charts.json").read_text())
                reference_charts = json.loads((second / "reference-charts.json").read_text())

                def beta(charts):
                    stocks = next(c for c in charts["charts"] if c["id"] == "stocks")
                    return next(
                        p["value"]
                        for p in stocks["evidence"]["parameters"]
                        if p["key"] == "beta_upf_progression"
                    )

                assert beta(experiment_charts) == 0.5 and beta(reference_charts) != 0.5
                views.get_by_role("button", name="Sources", exact=True).click()
                panel.get_by_text("Saved scenario assumptions", exact=True).click()
                expect(panel.locator(".scenario-assumptions")).to_contain_text(
                    "Browser changed assumption"
                )
                expect(panel.locator(".scenario-assumptions")).not_to_contain_text(
                    "Browser first experiment"
                )
                page.get_by_text("See the exact assumptions diff", exact=False).click()
                expect(
                    page.get_by_text("overrides.beta_upf_progression", exact=True)
                ).to_be_visible()
                nav.get_by_role("button", name="Saved runs", exact=True).click()
                page.locator(".saved-card").filter(has_text="Browser first experiment").click()
                try:
                    expect(
                        page.get_by_role(
                            "textbox", name="Your explanation & next question", exact=True
                        )
                    ).to_have_value("I will challenge the lag next.")
                    # Reopening the already selected run must refresh it as well.
                    nav.get_by_role("button", name="Saved runs", exact=True).click()
                    page.locator(".saved-card").filter(has_text="Browser first experiment").click()
                    expect(
                        page.get_by_role(
                            "textbox", name="Your explanation & next question", exact=True
                        )
                    ).to_have_value("I will challenge the lag next.")
                except AssertionError as exc:
                    page.screenshot(path=str(artifacts / "reopen-failure.png"))
                    raise AssertionError(
                        page.locator("body").inner_text()[-3000:] + str(errors)
                    ) from exc
                page.get_by_role("combobox", name="Question / chart", exact=True).select_option(
                    "uncertainty_life_expectancy"
                )
                page.wait_for_function("document.querySelector('.js-plotly-plot')?._fullLayout")
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator(".chart-story").scroll_into_view_if_needed()
                page.screenshot(path=str(artifacts / "chart-mobile.png"))
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                views.get_by_role("button", name="Sources", exact=True).click()
                page.locator(".chart-story").scroll_into_view_if_needed()
                expect(page.locator(".chart-pane .source").first).to_be_visible()
                page.screenshot(path=str(artifacts / "evidence-mobile.png"))
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                nav.get_by_role("button", name="Experiment", exact=True).click()
                page.get_by_role("combobox", name="Model / scenario", exact=True).select_option(
                    label="Experimental · Glp1 access"
                )
                expect(page.get_by_label("Access (%) · step 1", exact=True)).to_be_visible()
                for step in (4, 3, 2):
                    page.get_by_role(
                        "button", name=f"Remove access step {step}", exact=True
                    ).click()
                page.get_by_label("Model years", exact=True).fill("2")
                page.get_by_label("Experiment name", exact=True).fill("Browser GLP-1 assumptions")
                page.get_by_role("button", name="Run experiment →", exact=True).click()
                expect(page.get_by_role("button", name="Use these assumptions")).to_be_visible(
                    timeout=180000
                )
                picker.select_option("glp1_capacity")
                views.get_by_role("button", name="Sources", exact=True).click()
                panel.get_by_text("Saved scenario assumptions", exact=True).click()
                expect(panel.locator(".scenario-assumptions")).to_contain_text(
                    '"monthly_price_usd": 900'
                )
                expect(panel.locator(".scenario-assumptions")).to_contain_text(
                    '"supply_fraction": 0.03'
                )
                panel.get_by_text("Unresolved evidence and limits", exact=True).click()
                expect(panel).to_contain_text("interactions, adverse-event outcomes")
                page.screenshot(path=str(artifacts / "glp1-evidence-mobile.png"))
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                nav.get_by_role("button", name="Experiment", exact=True).click()
                page.get_by_role("combobox", name="Model / scenario", exact=True).select_option(
                    label="Experimental · Diet dynamics"
                )
                expect(
                    page.get_by_role("combobox", name="Response shape", exact=True)
                ).to_be_visible()
                page.screenshot(path=str(artifacts / "experiment-mobile.png"))
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                assert not errors, errors
                assert not external, external
                browser.close()
            print(
                "Explorer verified: real reruns, reference, frozen inputs, notes, exports, mobile; no external assets or JS errors."
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    verify()
