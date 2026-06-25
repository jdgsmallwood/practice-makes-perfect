"""E2E tests for TrickyBit detail page, SM-2 reset, and OMR manual tagging."""
import pytest
from playwright.sync_api import Page, expect

from omr.models import DetectedFeature, PassageAnalysis
from pieces.models import TrickyBit
from tests.factories import PieceFactory, PracticeLogFactory, TrickyBitFactory


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestTrickyBitDetail:
    def test_detail_page_loads(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, label="Tricky Coda")
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_role("heading", name="Tricky Coda")).to_be_visible()

    def test_shows_sm2_state(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, ease_factor=2.5, interval_days=6, repetitions=2)
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_text("2.50")).to_be_visible()   # ease factor
        expect(page.get_by_text("6d")).to_be_visible()      # interval

    def test_shows_practice_history(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        PracticeLogFactory(tricky_bit=bit, rating=3, interval_before=0, interval_after=1)
        PracticeLogFactory(tricky_bit=bit, rating=4, interval_before=1, interval_after=6)

        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_text("Good")).to_be_visible()
        expect(page.get_by_text("Easy")).to_be_visible()

    def test_shows_no_history_message_when_empty(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_text("No practice sessions recorded yet.")).to_be_visible()

    def test_piece_detail_links_to_bit_detail(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, label="High D Run")
        page.goto(live_server.url + f"/pieces/{piece.pk}/")
        page.get_by_role("link", name="View").first.click()
        expect(page).to_have_url(f"{live_server.url}/pieces/{piece.pk}/bits/{bit.pk}/")


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestSM2Reset:
    def test_reset_button_requires_confirmation(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, interval_days=15, repetitions=4)
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")

        # Confirm button is hidden until Reset is clicked
        expect(page.locator("[data-testid=confirm-reset]")).not_to_be_visible()
        page.get_by_role("button", name="Reset").click()
        expect(page.locator("[data-testid=confirm-reset]")).to_be_visible()

    def test_reset_restores_defaults(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(
            piece=piece,
            ease_factor=1.8,
            interval_days=20,
            repetitions=5,
        )
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")

        page.get_by_role("button", name="Reset").click()
        page.locator("[data-testid=confirm-reset]").click()
        page.wait_for_load_state("networkidle")

        bit.refresh_from_db()
        assert bit.ease_factor == 2.5
        assert bit.interval_days == 0
        assert bit.repetitions == 0
        assert bit.next_review_at is None

    def test_reset_redirects_back_to_detail(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, interval_days=10, repetitions=3)
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")

        page.get_by_role("button", name="Reset").click()
        page.locator("[data-testid=confirm-reset]").click()
        page.wait_for_url(f"{live_server.url}/pieces/{piece.pk}/bits/{bit.pk}/")


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestKeySignatureDisplay:
    def test_no_key_signature_hides_badge_and_card(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, key_signature="")
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_text("Key:", exact=False)).not_to_be_visible()
        expect(page.get_by_text("Key of", exact=False)).not_to_be_visible()

    def test_key_signature_badge_visible(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, key_signature="G")
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_text("Key: G major (1♯)")).to_be_visible()

    def test_key_signature_notation_card_visible(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, key_signature="Bb")
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_text("Key of B♭ major (2♭)")).to_be_visible()

    def test_flat_key_badge_shows_correct_label(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, key_signature="Eb")
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_text("Key: E♭ major (3♭)")).to_be_visible()

    def test_minor_key_badge_visible(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, key_signature="Am")
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.get_by_text("Key: A minor")).to_be_visible()


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestManualFeatureTagging:
    def test_analysis_tab_visible(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        expect(page.locator("[data-testid=analysis-tab]")).to_be_visible()

    def test_can_save_manual_features(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")

        page.locator("[data-testid=analysis-tab]").click()
        page.wait_for_timeout(200)

        # Check a feature checkbox
        page.locator("[name=features][value=register_high]").check()
        page.locator("[name=features][value=technique_trill]").check()
        page.locator("[data-testid=feature-form]").get_by_role("button", name="Save features").click()
        page.wait_for_load_state("networkidle")

        analysis = PassageAnalysis.objects.get(tricky_bit=bit)
        assert analysis.status == "complete"
        detected = {f.feature_type for f in analysis.detected_features.all()}
        assert "register_high" in detected
        assert "technique_trill" in detected

    def test_saved_features_are_pre_checked_on_reload(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        # Pre-create analysis with a feature
        from omr.service import run_analysis
        run_analysis(bit, provider_name="manual", features=["rhythm_triplets"])

        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        page.locator("[data-testid=analysis-tab]").click()
        page.wait_for_timeout(200)

        checkbox = page.locator("[name=features][value=rhythm_triplets]")
        expect(checkbox).to_be_checked()

    def test_saving_features_replaces_previous(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        from omr.service import run_analysis
        run_analysis(bit, provider_name="manual", features=["register_high", "technique_trill"])

        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/")
        page.locator("[data-testid=analysis-tab]").click()
        page.wait_for_timeout(200)

        # Uncheck one, save
        page.locator("[name=features][value=register_high]").uncheck()
        page.locator("[data-testid=feature-form]").get_by_role("button", name="Save features").click()
        page.wait_for_load_state("networkidle")

        analysis = PassageAnalysis.objects.get(tricky_bit=bit)
        detected = {f.feature_type for f in analysis.detected_features.all()}
        assert "register_high" not in detected
        assert "technique_trill" in detected
