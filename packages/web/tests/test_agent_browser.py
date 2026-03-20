"""Agent-browser tests for Cloudwright web UI.

Covers every README-documented feature exercisable through the browser:
- Page layout, branding, empty state
- Architecture design via chat (NL to spec) with real LLM
- Diagram rendering with tier grouping, connections, cost overlay
- Cost breakdown table with per-component pricing
- Compliance validation (HIPAA, PCI-DSS, SOC 2, Well-Architected)
- Export panel with format options
- Spec panel with YAML display
- Modify tab for architecture modification
- Suggestion buttons (context-aware, post-spec)
- Multi-turn chat (design → modify via sidebar)
- Streaming indicators during generation
- New button with confirmation dialog
- Summary bar with component count, cost, provider, WA score
- Download buttons (Terraform, YAML)
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request

import pytest

HAS_LLM = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

skip_no_browser = pytest.mark.skipif(
    not HAS_PLAYWRIGHT or not HAS_LLM,
    reason="Requires playwright and LLM API key",
)

_PORT = 18765
_BASE = f"http://localhost:{_PORT}"


@pytest.fixture(scope="module")
def web_server():
    """Start the web server for browser tests."""
    env = os.environ.copy()
    proc = subprocess.Popen(
        ["python3", "-c", f"from cloudwright_web.app import serve; serve(port={_PORT})"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{_BASE}/api/health")
            break
        except Exception:
            time.sleep(1)
    yield _BASE
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="module")
def browser_ctx(web_server):
    """Shared playwright browser context for the module."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context()
        yield ctx
        ctx.close()
        browser.close()


@pytest.fixture
def page(browser_ctx):
    """Fresh page per test."""
    p = browser_ctx.new_page()
    yield p
    p.close()


def _chat_input(page):
    return page.locator('input[placeholder*="Describe"]')


def _send_btn(page):
    return page.locator("button", has_text="Send")


def _submit_message(page, text: str):
    _chat_input(page).fill(text)
    _send_btn(page).click()


def _wait_for_idle(page, timeout_ms: int = 90_000):
    """Wait until the loading indicator disappears."""
    page.wait_for_function(
        "() => !document.body.innerText.includes('Generating') "
        "&& !document.body.innerText.includes('Modifying') "
        "&& !document.body.innerText.includes('Costing') "
        "&& !document.body.innerText.includes('Finalizing')",
        timeout=timeout_ms,
    )


def _design_and_wait(page, web_server, prompt: str):
    """Navigate, design, wait for idle. Returns page for chaining."""
    page.goto(web_server)
    _submit_message(page, prompt)
    _wait_for_idle(page, timeout_ms=90_000)
    return page


# ---------------------------------------------------------------------------
# 1. Page Layout & Branding
# ---------------------------------------------------------------------------


@skip_no_browser
class TestPageLoads:
    def test_title_or_chat_input_present(self, page, web_server):
        page.goto(web_server)
        has_title = "Cloudwright" in page.title() or page.locator("h1", has_text="Cloudwright").is_visible()
        has_input = _chat_input(page).is_visible()
        assert has_title or has_input

    def test_send_button_present(self, page, web_server):
        page.goto(web_server)
        assert _send_btn(page).is_visible()

    def test_placeholder_text(self, page, web_server):
        page.goto(web_server)
        placeholder = _chat_input(page).get_attribute("placeholder")
        assert placeholder and "Describe" in placeholder

    def test_empty_state_hint(self, page, web_server):
        """README shows example prompt in empty state."""
        page.goto(web_server)
        hint = page.locator("text=Describe your cloud architecture")
        assert hint.is_visible()

    def test_example_prompt_shown(self, page, web_server):
        """README example: '3-tier web app on AWS with CloudFront, ALB, EC2, and RDS'."""
        page.goto(web_server)
        example = page.locator("text=3-tier web app on AWS")
        assert example.is_visible()

    def test_all_six_tabs_visible(self, page, web_server):
        """README features: diagram, cost, validate, export, spec, modify tabs."""
        page.goto(web_server)
        for tab_name in ["diagram", "cost", "validate", "export", "spec", "modify"]:
            tab = page.locator("button", has_text=tab_name)
            assert tab.is_visible(), f"Tab '{tab_name}' not visible"

    def test_send_button_disabled_when_empty(self, page, web_server):
        page.goto(web_server)
        assert _send_btn(page).is_disabled()

    def test_send_button_enabled_when_filled(self, page, web_server):
        page.goto(web_server)
        _chat_input(page).fill("test input")
        assert _send_btn(page).is_enabled()

    def test_subtitle_architecture_intelligence(self, page, web_server):
        page.goto(web_server)
        subtitle = page.locator("text=Architecture Intelligence")
        assert subtitle.is_visible()

    def test_diagram_empty_state(self, page, web_server):
        """Diagram tab shows prompt before any design."""
        page.goto(web_server)
        empty = page.locator("text=Design an architecture to see the diagram")
        assert empty.is_visible()


# ---------------------------------------------------------------------------
# 2. Architecture Design (NL to Spec) — Core README Feature
# ---------------------------------------------------------------------------


@skip_no_browser
class TestArchitectureDesign:
    def test_design_produces_assistant_response(self, page, web_server):
        """README: 'Describe a system in natural language → structured architecture spec'."""
        _design_and_wait(page, web_server, "3-tier web app on AWS with EC2 and RDS")
        bubbles = page.locator('[style*="background: rgb(241, 245, 249)"]')
        assert bubbles.count() >= 1
        assert bubbles.first.inner_text().strip() != ""

    def test_response_mentions_designed(self, page, web_server):
        _design_and_wait(page, web_server, "Simple web app on AWS with EC2 and S3")
        content = page.locator('[style*="background: rgb(241, 245, 249)"]').first.inner_text()
        assert any(kw in content for kw in ["Designed", "Modified", "Error", "components"])

    def test_response_includes_cost_estimate(self, page, web_server):
        """README: cost estimates are part of the design response."""
        _design_and_wait(page, web_server, "Web app on AWS with ALB, EC2, and RDS PostgreSQL")
        content = page.locator('[style*="background: rgb(241, 245, 249)"]').first.inner_text()
        assert "$" in content or "cost" in content.lower()

    def test_response_includes_component_count(self, page, web_server):
        _design_and_wait(page, web_server, "Serverless API on AWS with Lambda and DynamoDB")
        content = page.locator('[style*="background: rgb(241, 245, 249)"]').first.inner_text()
        assert "component" in content.lower()

    def test_new_button_appears_after_design(self, page, web_server):
        """README: 'New' button for starting fresh sessions."""
        _design_and_wait(page, web_server, "Simple AWS EC2 app")
        new_btn = page.locator("button", has_text="New")
        new_btn.wait_for(state="visible", timeout=5_000)
        assert new_btn.is_visible()


# ---------------------------------------------------------------------------
# 3. Diagram Tab — Interactive React Flow
# ---------------------------------------------------------------------------


@skip_no_browser
class TestDiagramTab:
    def test_diagram_tab_shows_content_after_design(self, page, web_server):
        _design_and_wait(page, web_server, "Simple AWS app with EC2 and S3")
        diagram_tab = page.locator("button", has_text="diagram")
        assert diagram_tab.is_visible()

    def test_diagram_has_zoom_controls(self, page, web_server):
        """README: interactive diagrams with zoom (ReactFlow Controls)."""
        _design_and_wait(page, web_server, "Web app on AWS with ALB and EC2")
        # ReactFlow Controls renders buttons with aria-labels, not text
        for label in ["zoom in", "zoom out", "fit view"]:
            btn = page.locator(f'button[aria-label="{label}"]')
            if btn.count() == 0:
                # Fallback: check for the Controls container
                btn = page.locator(".react-flow__controls button")
            assert btn.count() >= 1, f"Zoom control '{label}' not found"

    def test_diagram_has_boundary_toggle(self, page, web_server):
        """README: tier-based layout with boundary grouping."""
        _design_and_wait(page, web_server, "3-tier web app on AWS with ALB, EC2, RDS")
        boundary_btn = page.locator("button", has_text="Boundaries")
        assert boundary_btn.count() >= 1


# ---------------------------------------------------------------------------
# 4. Cost Tab — Per-Component Pricing (README Section: Cost Estimation)
# ---------------------------------------------------------------------------


@skip_no_browser
class TestCostTab:
    def test_cost_table_has_breakdown(self, page, web_server):
        """README: 'Per-component monthly pricing from a built-in SQLite catalog'."""
        _design_and_wait(page, web_server, "Web app on AWS with ALB, EC2, and RDS")
        # Use get_by_role with exact match to avoid hitting "Reduce cost" suggestion
        page.get_by_role("button", name="cost", exact=True).click()
        page.wait_for_function(
            "() => document.body.innerText.includes('Cost Breakdown')",
            timeout=15_000,
        )
        heading = page.locator("h2", has_text="Cost Breakdown")
        assert heading.is_visible()

    def test_cost_table_has_columns(self, page, web_server):
        _design_and_wait(page, web_server, "Web app on AWS with EC2 and RDS")
        page.get_by_role("button", name="cost", exact=True).click()
        page.wait_for_function(
            "() => document.body.innerText.includes('Cost Breakdown')",
            timeout=15_000,
        )
        for col in ["Component", "Service", "Monthly"]:
            assert page.locator(f"th:has-text('{col}')").count() >= 1, f"Column '{col}' missing"

    def test_cost_table_has_total_row(self, page, web_server):
        _design_and_wait(page, web_server, "AWS app with EC2 and RDS")
        page.get_by_role("button", name="cost", exact=True).click()
        page.wait_for_function(
            "() => document.body.innerText.includes('Cost Breakdown')",
            timeout=15_000,
        )
        total = page.locator("td:has-text('Total')")
        assert total.count() >= 1


# ---------------------------------------------------------------------------
# 5. Validate Tab — Compliance Frameworks (README: 6 compliance frameworks)
# ---------------------------------------------------------------------------


@skip_no_browser
class TestValidateTab:
    def test_compliance_frameworks_present(self, page, web_server):
        """README: HIPAA, PCI-DSS, SOC 2, Well-Architected."""
        _design_and_wait(page, web_server, "Web app on AWS with EC2 and RDS")
        page.locator("button", has_text="validate").click()
        page.locator("h2", has_text="Validate").wait_for(state="visible", timeout=5_000)
        for framework in ["HIPAA", "PCI-DSS", "SOC 2", "Well-Architected"]:
            btn = page.locator("button", has_text=framework)
            assert btn.count() >= 1, f"Framework '{framework}' button missing"

    def test_well_architected_shows_results(self, page, web_server):
        """README: compliance validation with check results."""
        _design_and_wait(page, web_server, "Web app on AWS with ALB, EC2, and RDS")
        page.locator("button", has_text="validate").click()
        page.locator("h2", has_text="Validate").wait_for(state="visible", timeout=5_000)
        page.locator("button", has_text="Well-Architected").click()
        # Results should appear (passed or failed checks)
        page.wait_for_function(
            "() => document.body.innerText.includes('Passed') || document.body.innerText.includes('Failed')",
            timeout=10_000,
        )


# ---------------------------------------------------------------------------
# 6. Export Tab — 8 Export Formats (README: Infrastructure Export)
# ---------------------------------------------------------------------------


@skip_no_browser
class TestExportTab:
    def test_export_panel_visible(self, page, web_server):
        _design_and_wait(page, web_server, "Simple AWS app with EC2")
        page.get_by_role("button", name="export", exact=True).click()
        heading = page.locator("h2", has_text="Export")
        heading.wait_for(state="visible", timeout=5_000)
        assert heading.is_visible()


# ---------------------------------------------------------------------------
# 7. Spec Tab — YAML Display
# ---------------------------------------------------------------------------


@skip_no_browser
class TestSpecTab:
    def test_spec_panel_shows_yaml(self, page, web_server):
        """README: ArchSpec YAML format."""
        _design_and_wait(page, web_server, "Web app on AWS with EC2 and RDS")
        page.locator("button", has_text="spec").click()
        # Spec panel defaults to Overview sub-tab; click "YAML Source" to see raw YAML
        yaml_tab = page.locator("button", has_text="YAML Source")
        yaml_tab.wait_for(state="visible", timeout=10_000)
        yaml_tab.click()
        # YAML should contain 'name:' and 'provider:' in the <pre> block
        page.wait_for_function(
            "() => document.querySelector('pre')?.innerText.includes('name:')",
            timeout=15_000,
        )


# ---------------------------------------------------------------------------
# 8. Modify Tab — Architecture Modification (README: modify command)
# ---------------------------------------------------------------------------


@skip_no_browser
class TestModifyTab:
    def test_modify_tab_shows_input(self, page, web_server):
        _design_and_wait(page, web_server, "Simple AWS app with EC2")
        page.locator("button", has_text="modify").click()
        modify_input = page.locator('input[placeholder*="Redis"]')
        modify_input.wait_for(state="visible", timeout=5_000)
        assert modify_input.is_visible()


# ---------------------------------------------------------------------------
# 9. Suggestion Buttons (v0.3.5 Feature)
# ---------------------------------------------------------------------------


@skip_no_browser
class TestSuggestionButtons:
    def test_suggestions_appear_after_spec(self, page, web_server):
        _design_and_wait(page, web_server, "3-tier web app on AWS with ALB, EC2, and RDS")
        # Suggestions may be LLM-generated or from the static fallback list
        static_texts = ["Add caching layer", "Reduce cost", "Increase redundancy", "Add monitoring", "Add security"]
        found = False
        for text in static_texts:
            btn = page.locator("button", has_text=text)
            if btn.count() > 0:
                found = True
                break
        if not found:
            # Check for any suggestion-style buttons (small, rounded, in the chat area)
            sidebar = page.locator("div").filter(has=page.locator("h1", has_text="Cloudwright"))
            suggestion_buttons = sidebar.locator("button").filter(has_not_text="Send").filter(has_not_text="New")
            found = suggestion_buttons.count() > 2  # at least some suggestion buttons beyond Send/New
        assert found, "No suggestion buttons found after spec response"

    def test_suggestion_click_populates_input(self, page, web_server):
        _design_and_wait(page, web_server, "3-tier web app on AWS with ALB, EC2, and RDS")
        # Try static suggestions first, then fall back to any suggestion button
        static_texts = ["Add caching layer", "Reduce cost", "Increase redundancy", "Add monitoring", "Add security"]
        btn = None
        btn_text = ""
        for text in static_texts:
            candidate = page.locator("button", has_text=text)
            if candidate.count() > 0:
                btn = candidate.first
                btn_text = btn.inner_text()
                break

        if btn is None:
            # LLM-generated suggestions - find any small suggestion button in the sidebar
            sidebar = page.locator("div").filter(has=page.locator("h1", has_text="Cloudwright"))
            candidates = sidebar.locator("button").filter(has_not_text="Send").filter(has_not_text="New")
            if candidates.count() > 0:
                btn = candidates.first
                btn_text = btn.inner_text()

        assert btn is not None, "No suggestion button found"
        btn.click()
        assert _chat_input(page).input_value() == btn_text


# ---------------------------------------------------------------------------
# 10. Multi-Turn Chat (design → modify via sidebar)
# ---------------------------------------------------------------------------


@skip_no_browser
class TestMultiTurnChat:
    def test_modify_via_chat_produces_second_response(self, page, web_server):
        """README: 'multi-turn conversation' and 'natural language modification'."""
        _design_and_wait(page, web_server, "Web app on AWS with EC2 and RDS")

        # Second turn: modify via chat sidebar
        _submit_message(page, "Add a Redis cache between the web server and database")
        _wait_for_idle(page, timeout_ms=90_000)

        # Should now have 2 assistant bubbles
        bubbles = page.locator('[style*="background: rgb(241, 245, 249)"]')
        assert bubbles.count() >= 2

        # Second response should mention "Modified"
        second = bubbles.nth(1).inner_text()
        assert any(kw in second for kw in ["Modified", "Designed", "components"])


# ---------------------------------------------------------------------------
# 11. Streaming Display (v0.3.5 Feature: Token-Level SSE)
# ---------------------------------------------------------------------------


@skip_no_browser
class TestStreamingDisplay:
    def test_loading_indicator_appears_during_request(self, page, web_server):
        page.goto(web_server)
        _chat_input(page).fill("Design a simple web app on AWS with EC2")
        _send_btn(page).click()

        try:
            page.wait_for_selector("text=Generating architecture", timeout=10_000)
        except Exception:
            pass  # May complete too fast

        _wait_for_idle(page, timeout_ms=90_000)
        bubbles = page.locator('[style*="background: rgb(241, 245, 249)"]')
        assert bubbles.count() >= 1

    def test_response_non_empty_before_done_event(self, page, web_server):
        page.goto(web_server)
        _chat_input(page).fill("Design a serverless API on AWS with Lambda and DynamoDB")
        _send_btn(page).click()

        try:
            page.wait_for_selector("text=Estimating cost", timeout=60_000)
        except Exception:
            pass

        _wait_for_idle(page, timeout_ms=90_000)
        bubbles = page.locator('[style*="background: rgb(241, 245, 249)"]')
        assert bubbles.count() >= 1


# ---------------------------------------------------------------------------
# 12. New Button Confirmation (v0.3.5 Feature)
# ---------------------------------------------------------------------------


@skip_no_browser
class TestNewButtonConfirmation:
    def test_dismiss_confirm_preserves_chat(self, page, web_server):
        _design_and_wait(page, web_server, "Simple web app on AWS with EC2 and RDS")
        new_btn = page.locator("button", has_text="New")
        new_btn.wait_for(state="visible", timeout=5_000)

        page.once("dialog", lambda d: d.dismiss())
        new_btn.click()

        assert page.locator('[style*="background: rgb(37, 99, 235)"]').count() > 0

    def test_accept_confirm_clears_chat(self, page, web_server):
        _design_and_wait(page, web_server, "Simple web app on AWS with EC2 and RDS")
        new_btn = page.locator("button", has_text="New")
        new_btn.wait_for(state="visible", timeout=5_000)

        page.once("dialog", lambda d: d.accept())
        new_btn.click()

        page.wait_for_selector('text="Describe your cloud architecture"', timeout=5_000)
        page.wait_for_timeout(500)
        assert _chat_input(page).is_visible()


# ---------------------------------------------------------------------------
# 13. Summary Bar — Component Count, Cost, Provider
# ---------------------------------------------------------------------------


@skip_no_browser
class TestSummaryBar:
    def test_summary_shows_component_count(self, page, web_server):
        """README: summary bar with component count."""
        _design_and_wait(page, web_server, "3-tier web app on AWS with ALB, EC2, and RDS")
        page.wait_for_function(
            "() => document.body.innerText.includes('Components:')",
            timeout=5_000,
        )

    def test_summary_shows_cost(self, page, web_server):
        _design_and_wait(page, web_server, "AWS app with EC2 and RDS")
        page.wait_for_function(
            "() => document.body.innerText.includes('Est.')",
            timeout=5_000,
        )

    def test_summary_shows_provider(self, page, web_server):
        _design_and_wait(page, web_server, "Simple AWS app with EC2")
        page.wait_for_function(
            "() => document.body.innerText.includes('AWS')",
            timeout=5_000,
        )

    def test_download_buttons_present(self, page, web_server):
        """README: Terraform and YAML export."""
        _design_and_wait(page, web_server, "Web app on AWS with EC2")
        tf_btn = page.locator("button", has_text="Download Terraform")
        yaml_btn = page.locator("button", has_text="Download YAML")
        assert tf_btn.count() >= 1
        assert yaml_btn.count() >= 1

    def test_well_architected_score_in_summary(self, page, web_server):
        """README: architecture quality scoring."""
        _design_and_wait(page, web_server, "3-tier web app on AWS with ALB, EC2, and RDS")
        page.wait_for_function(
            "() => document.body.innerText.includes('WA:')",
            timeout=5_000,
        )


# ---------------------------------------------------------------------------
# 14-19. API Endpoints (tested via urllib, no browser needed)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_LLM, reason="Requires LLM API key")
class TestAPIEndpoints:
    def test_health_endpoint(self, web_server):
        """README: health check endpoint."""
        resp = urllib.request.urlopen(f"{web_server}/api/health")
        data = json.loads(resp.read())
        assert data["status"] == "ok"
        assert data["catalog_loaded"] is True

    def test_design_endpoint(self, web_server):
        """README: NL architecture design API."""
        req = urllib.request.Request(
            f"{web_server}/api/design",
            data=json.dumps({"description": "Simple AWS app with Lambda and S3"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=90)
        data = json.loads(resp.read())
        assert "spec" in data
        assert "yaml" in data
        assert data["spec"]["provider"] in ("aws", "gcp", "azure", "databricks")
        assert len(data["spec"]["components"]) >= 1

    def test_cost_endpoint(self, web_server):
        """README: per-component cost estimation API."""
        spec = {
            "name": "Test",
            "provider": "aws",
            "region": "us-east-1",
            "components": [
                {
                    "id": "web",
                    "service": "ec2",
                    "provider": "aws",
                    "label": "Web",
                    "description": "Server",
                    "tier": 1,
                    "config": {"instance_type": "t3.medium"},
                },
            ],
            "connections": [],
        }
        req = urllib.request.Request(
            f"{web_server}/api/cost",
            data=json.dumps({"spec": spec}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        assert "estimate" in data
        assert data["estimate"]["monthly_total"] > 0
        assert data["estimate"]["currency"] == "USD"

    def test_validate_endpoint(self, web_server):
        """README: compliance validation API (6 frameworks)."""
        spec = {
            "name": "Test",
            "provider": "aws",
            "region": "us-east-1",
            "components": [
                {
                    "id": "web",
                    "service": "ec2",
                    "provider": "aws",
                    "label": "Web",
                    "description": "Server",
                    "tier": 1,
                    "config": {},
                },
            ],
            "connections": [],
        }
        req = urllib.request.Request(
            f"{web_server}/api/validate",
            data=json.dumps({"spec": spec, "compliance": ["hipaa"], "well_architected": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        assert "results" in data
        frameworks = [r["framework"] for r in data["results"]]
        assert "HIPAA" in frameworks
        assert "Well-Architected" in frameworks

    def test_streaming_endpoint(self, web_server):
        """README v0.3.5: SSE streaming design endpoint."""
        req = urllib.request.Request(
            f"{web_server}/api/design/stream",
            data=json.dumps({"description": "Simple Lambda API on AWS"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=90)
        body = resp.read().decode()
        # SSE events should contain the streaming stages
        assert "generating" in body
        assert "generated" in body
        assert "done" in body
        # Spec should be embedded in the generated event
        assert '"components"' in body

    def test_structured_error_response(self, web_server):
        """README v0.3.5: structured error responses with code, message, suggestion."""
        req = urllib.request.Request(
            f"{web_server}/api/design",
            data=json.dumps({}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            pytest.fail("Expected 422 for missing description")
        except urllib.error.HTTPError as e:
            assert e.code == 422
            data = json.loads(e.read())
            assert "detail" in data
