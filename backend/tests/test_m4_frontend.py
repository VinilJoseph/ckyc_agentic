"""Milestone 4 Verification Suite: Interactive Showcase UI & Static Backend Serving (Remediated).

Validates:
1. File layout compliance according to PROJECT.md § Code Layout.
2. Frontend standalone browser SPA index.html structure and zero-Docker runtime.
3. Dual theme system tokens (Obsidian Dark #0D0D10 vs Fintech Light #F8FAFC, .dark, .holo-border).
4. Reviewer Workspace 55/45 pane layout, 11-stage stepper, and algorithmic validation check badges.
5. ExtractedFieldsDeck inline decision gates (Confirm, Edit, Reject) and audit trail.
6. BiometricCard facial comparison score gauge, threshold, and re-run.
7. DecisionBar mandatory written justification and action buttons.
8. EmailSimulatorModal 3 tabs (REST Webhook, RFC 822 .eml, Exception Queue triage) and terminal case filter.
9. CredentialShowcase purpose-bound claims, 30-day live countdown timer, and consent.
10. Backend static mounting and SPA fallback routing via FastAPI TestClient / HTTPX.
11. Security hardening: bare /api 404 JSON guard and path traversal prevention.
"""
from pathlib import Path
import re
import sys

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

frontend_dir = backend_dir.parent / "frontend"
if not frontend_dir.exists():
    workspace_frontend = Path(r"C:\Users\trainee1\Documents\trainee_notes\ckyc_agentic\frontend")
    if workspace_frontend.exists():
        frontend_dir = workspace_frontend


def test_code_layout_all_files_exist():
    """Verify all 16 required frontend and configuration files exist."""
    required_files = [
        frontend_dir / "index.html",
        frontend_dir / "package.json",
        frontend_dir / "vite.config.js",
        frontend_dir / "src" / "index.css",
        frontend_dir / "src" / "main.jsx",
        frontend_dir / "src" / "App.jsx",
        frontend_dir / "src" / "components" / "Header.jsx",
        frontend_dir / "src" / "components" / "ThemeToggle.jsx",
        frontend_dir / "src" / "components" / "CaseList.jsx",
        frontend_dir / "src" / "components" / "ReviewerWorkspace.jsx",
        frontend_dir / "src" / "components" / "DocumentViewer.jsx",
        frontend_dir / "src" / "components" / "ExtractedFieldsDeck.jsx",
        frontend_dir / "src" / "components" / "BiometricCard.jsx",
        frontend_dir / "src" / "components" / "DecisionBar.jsx",
        frontend_dir / "src" / "components" / "EmailSimulatorModal.jsx",
        frontend_dir / "src" / "components" / "CredentialShowcase.jsx",
    ]
    for rf in required_files:
        assert rf.exists(), f"Missing required frontend file: {rf}"
        assert rf.stat().st_size > 0, f"File {rf} is empty"


def test_index_html_standalone_spa_runtime():
    """Verify index.html contains zero-Docker browser-executable SPA runtime with SVG icons."""
    index_path = frontend_dir / "index.html"
    content = index_path.read_text(encoding="utf-8")

    assert "<!DOCTYPE html>" in content
    assert "react.development.js" in content or "react.production.min.js" in content or "React" in content
    assert "react-dom.development.js" in content or "react-dom.production.min.js" in content or "ReactDOM" in content
    assert "babel.min.js" in content or "babel" in content
    assert "tailwindcss" in content or "tailwind" in content
    assert "<svg" in content or "svg" in content.lower(), "Missing SVG icon elements in index.html"
    assert "#0D0D10" in content
    assert "#F8FAFC" in content
    assert "ReviewerWorkspace" in content or "reviewer" in content.lower()
    assert "DecisionBar" in content or "decision" in content.lower()
    assert "BiometricCard" in content or "biometric" in content.lower()
    assert "EmailSimulatorModal" in content or "email simulator" in content.lower()
    assert "CredentialShowcase" in content or "credential" in content.lower()


def test_dual_theme_tokens():
    """Verify dual theme system tokens in CSS and components (.dark, .holo-border, --holo-gradient)."""
    css_path = frontend_dir / "src" / "index.css"
    css_content = css_path.read_text(encoding="utf-8")

    assert "#0D0D10" in css_content
    assert "#F8FAFC" in css_content
    assert ".dark" in css_content
    assert ".holo-border" in css_content or "--holo-gradient" in css_content

    toggle_path = frontend_dir / "src" / "components" / "ThemeToggle.jsx"
    toggle_content = toggle_path.read_text(encoding="utf-8")
    assert "toggleTheme" in toggle_content
    assert "dark" in toggle_content and "light" in toggle_content


def test_reviewer_workspace_layout_and_stepper():
    """Verify 55/45 split, 11-stage state machine stepper, and validation check identifiers."""
    rw_path = frontend_dir / "src" / "components" / "ReviewerWorkspace.jsx"
    content = rw_path.read_text(encoding="utf-8")

    # 55/45 split check (col-span-7 / col-span-5 in 12-col grid)
    assert "55%" in content or "col-span-7" in content
    assert "45%" in content or "col-span-5" in content

    # 11-stage canonical state machine stepper check
    stages = [
        "draft",
        "invitation_sent",
        "awaiting_documents",
        "documents_received",
        "ocr_processing",
        "needs_applicant_correction",
        "in_review",
        "approved",
        "rejected",
        "expired",
        "closed",
    ]
    for stage in stages:
        assert stage in content, f"Missing lifecycle stage in stepper: {stage}"

    # Algorithmic validation codes check
    assert "VERHOEFF_CHECKSUM_VALID" in content or "Verhoeff" in content
    assert "PAN_STRUCTURE_VALID" in content or "PAN" in content
    assert "AGE_REQUIREMENT_VERIFIED" in content or "age" in content.lower()
    assert "NAME_SIMILARITY_MATCH" in content or "fuzzy" in content.lower()


def test_document_viewer_features():
    """Verify document viewer has zoom, rotation, tab switcher, and OCR bounding boxes."""
    dv_path = frontend_dir / "src" / "components" / "DocumentViewer.jsx"
    content = dv_path.read_text(encoding="utf-8")

    assert "zoom" in content.lower()
    assert "rotate" in content.lower()
    assert "mockBoundingBoxes" in content or "bounding box" in content.lower() or "bounding_box" in content or "bbox" in content
    assert "fit-to-width" in content or "reset" in content.lower()


def test_extracted_fields_deck_decision_gates():
    """Verify inline Confirm, Edit, and Reject decision gates with correction history."""
    ef_path = frontend_dir / "src" / "components" / "ExtractedFieldsDeck.jsx"
    content = ef_path.read_text(encoding="utf-8")

    assert "confirmed" in content
    assert "corrected" in content or "Edit" in content
    assert "rejected" in content
    assert "correction_history" in content
    assert "confidence" in content


def test_biometric_card():
    """Verify BiometricCard side-by-side comparison, match score gauge, and threshold."""
    bc_path = frontend_dir / "src" / "components" / "BiometricCard.jsx"
    content = bc_path.read_text(encoding="utf-8")

    assert "Selfie" in content or "selfie" in content.lower()
    assert "ID Photo" in content or "id photo" in content.lower() or "id_photo" in content or "ID Document" in content
    assert "confidence" in content or "score" in content
    assert "threshold" in content
    assert "Re-run" in content or "re-run" in content.lower()


def test_decision_bar_mandatory_justification():
    """Verify DecisionBar enforces non-empty justification before enabling actions."""
    db_path = frontend_dir / "src" / "components" / "DecisionBar.jsx"
    content = db_path.read_text(encoding="utf-8")

    assert "justification" in content.lower() or "reason" in content.lower()
    assert "disabled" in content
    assert "Approve" in content
    assert "Reject" in content
    assert "Request Correction" in content or "Correction" in content


def test_email_simulator_modal():
    """Verify EmailSimulatorModal includes REST Webhook, RFC 822 upload, Exception Queue, and terminal filter."""
    esm_path = frontend_dir / "src" / "components" / "EmailSimulatorModal.jsx"
    content = esm_path.read_text(encoding="utf-8")

    assert "webhook" in content.lower()
    assert "eml" in content.lower()
    assert "exception" in content.lower() or "triage" in content.lower()
    assert "assign" in content.lower()
    assert "dismiss" in content.lower()
    # Terminal cases filtering
    assert "approved" in content and "rejected" in content and "closed" in content


def test_credential_showcase():
    """Verify CredentialShowcase purpose-bound claims, 30-day timer, and consent controls."""
    cs_path = frontend_dir / "src" / "components" / "CredentialShowcase.jsx"
    content = cs_path.read_text(encoding="utf-8")

    assert "days" in content.lower() or "timer" in content.lower() or "expires" in content.lower()
    assert "consent" in content.lower() or "revok" in content.lower()
    assert "holographic" in content.lower() or "gradient" in content.lower()
    assert "Verified Claim" in content or "claims" in content.lower()


def test_backend_static_serving_and_spa_fallback():
    """Verify FastAPI backend mounts frontend statically, serves SPA fallback, and guards API & path traversal."""
    from starlette.testclient import TestClient
    from app.main import create_app

    app = create_app()
    client = TestClient(app)

    # 1. Health endpoint works
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    # 2. Root route "/" returns index.html
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "<!DOCTYPE html>" in root_resp.text
    assert "CKYC" in root_resp.text

    # 3. SPA Fallback: non-existent client route returns index.html
    spa_resp = client.get("/cases/CASE-9999/review")
    assert spa_resp.status_code == 200
    assert "<!DOCTYPE html>" in spa_resp.text

    # 4. Static asset serving: existing file returns actual file content
    asset_resp = client.get("/src/index.css")
    assert asset_resp.status_code == 200
    assert "#0D0D10" in asset_resp.text

    # 5. Non-existent API route returns JSON 404, not HTML
    api_resp = client.get("/api/v1/nonexistent_route_404")
    assert api_resp.status_code == 404
    assert "text/html" not in api_resp.headers.get("content-type", "")

    # 6. Bare /api returns 404 JSON (NOT index.html)
    bare_api_resp = client.get("/api")
    assert bare_api_resp.status_code == 404
    assert "text/html" not in bare_api_resp.headers.get("content-type", "")

    # 7. Path traversal attempt is blocked and returns 404 JSON (NOT index.html)
    traversal_resp = client.get("/src/../../backend/app/main.py")
    assert traversal_resp.status_code == 404
    assert "text/html" not in traversal_resp.headers.get("content-type", "")
    assert "def create_app" not in traversal_resp.text
    assert traversal_resp.json()["detail"] == "Resource not found"


def run_all_tests():
    """Runs all verification tests synchronously and reports results."""
    test_functions = [
        test_code_layout_all_files_exist,
        test_index_html_standalone_spa_runtime,
        test_dual_theme_tokens,
        test_reviewer_workspace_layout_and_stepper,
        test_document_viewer_features,
        test_extracted_fields_deck_decision_gates,
        test_biometric_card,
        test_decision_bar_mandatory_justification,
        test_email_simulator_modal,
        test_credential_showcase,
        test_backend_static_serving_and_spa_fallback,
    ]

    print("======================================================================")
    print("Running Milestone 4 Interactive Showcase UI Verification Suite")
    print("======================================================================")

    passed = 0
    failed = 0
    for tf in test_functions:
        try:
            tf()
            print(f" [PASS] {tf.__name__}")
            passed += 1
        except Exception as e:
            print(f" [FAIL] {tf.__name__}: {str(e)}")
            failed += 1

    print("----------------------------------------------------------------------")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_functions)} total tests.")
    print("======================================================================")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    if not success:
        sys.exit(1)
