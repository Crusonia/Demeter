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
                page.get_by_label("Your explanation & next question", exact=True).fill(
                    "I will challenge the lag next."
                )
                page.get_by_role("button", name="Save reflection", exact=True).click()
                expect(
                    page.get_by_text("Reflection saved alongside this experiment.")
                ).to_be_visible()
                with page.expect_download() as download:
                    page.get_by_role("button", name="↓ Offline report", exact=True).click()
                download.value.save_as(artifacts / "report.html")
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
                page.get_by_text("See the exact assumptions diff", exact=False).click()
                expect(
                    page.get_by_role("rowheader", name="overrides.beta_upf_progression", exact=True)
                ).to_be_visible()
                nav.get_by_role("button", name="Saved runs", exact=True).click()
                page.locator(".saved-card").filter(has_text="Browser first experiment").click()
                expect(
                    page.get_by_label("Your explanation & next question", exact=True)
                ).to_have_value("I will challenge the lag next.")
                page.get_by_label("Question / chart", exact=True).select_option(
                    "uncertainty_life_expectancy"
                )
                page.wait_for_function("document.querySelector('.js-plotly-plot')?._fullLayout")
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator(".chart-story").scroll_into_view_if_needed()
                page.screenshot(path=str(artifacts / "chart-mobile.png"))
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                nav.get_by_role("button", name="Experiment", exact=True).click()
                page.get_by_label("Model / scenario", exact=True).select_option(
                    label="Experimental · Glp1 access"
                )
                expect(page.get_by_label("Access (%) · step 1", exact=True)).to_be_visible()
                page.get_by_label("Model / scenario", exact=True).select_option(
                    label="Experimental · Diet dynamics"
                )
                expect(page.get_by_label("Response shape", exact=True)).to_be_visible()
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
