import pytest
from playwright.sync_api import Page, expect

from tests.factories import PieceFactory, TrickyBitFactory


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestDashboard:
    def test_dashboard_loads(self, page: Page, live_server):
        page.goto(live_server.url + "/")
        expect(page).to_have_title("Dashboard — Practice Makes Perfect")

    def test_dashboard_shows_zero_due_with_no_data(self, page: Page, live_server):
        page.goto(live_server.url + "/")
        due = page.locator("[data-testid=due-count]")
        expect(due).to_have_text("0")

    def test_dashboard_counts_due_bits_from_active_pieces(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, next_review_at=None)  # always due
        TrickyBitFactory(piece=piece, next_review_at=None)

        page.goto(live_server.url + "/")
        expect(page.locator("[data-testid=due-count]")).to_have_text("2")

    def test_inactive_piece_bits_not_counted(self, page: Page, live_server):
        piece = PieceFactory(is_active=False)
        TrickyBitFactory(piece=piece, next_review_at=None)

        page.goto(live_server.url + "/")
        expect(page.locator("[data-testid=due-count]")).to_have_text("0")

    def test_start_practice_button_visible_when_due(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece)

        page.goto(live_server.url + "/")
        start_btn = page.get_by_role("link", name="Start Practice")
        expect(start_btn).to_be_visible()


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestPieceList:
    def test_piece_list_page_loads(self, page: Page, live_server):
        page.goto(live_server.url + "/pieces/")
        expect(page).to_have_title("My Pieces — Practice Makes Perfect")

    def test_empty_state_shown_with_no_pieces(self, page: Page, live_server):
        page.goto(live_server.url + "/pieces/")
        expect(page.get_by_text("No pieces yet.")).to_be_visible()

    def test_pieces_appear_in_list(self, page: Page, live_server):
        PieceFactory(name="Syrinx", composer="Debussy")
        page.goto(live_server.url + "/pieces/")
        expect(page.get_by_text("Syrinx")).to_be_visible()
        expect(page.get_by_text("Debussy")).to_be_visible()


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestAddPiece:
    def test_add_piece_form_submission(self, page: Page, live_server):
        page.goto(live_server.url + "/pieces/add/")
        page.fill("[name=name]", "Partita in A minor")
        page.fill("[name=composer]", "J.S. Bach")
        page.click("[type=submit]")

        # Redirected to piece detail — title should contain piece name
        expect(page).to_have_title("Partita in A minor — Practice Makes Perfect")

    def test_add_piece_requires_name(self, page: Page, live_server):
        page.goto(live_server.url + "/pieces/add/")
        page.click("[type=submit]")
        # Form should not redirect; stays on add page
        expect(page).to_have_url(f"{live_server.url}/pieces/add/")


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestActiveToggle:
    def test_toggle_deactivates_active_piece(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        page.goto(live_server.url + "/pieces/")

        toggle = page.locator(f"[data-testid=toggle-{piece.pk}]")
        expect(toggle).to_contain_text("Active")

        toggle.click()
        page.wait_for_load_state("networkidle")
        expect(toggle).to_contain_text("Inactive")

    def test_toggle_activates_inactive_piece(self, page: Page, live_server):
        piece = PieceFactory(is_active=False)
        page.goto(live_server.url + "/pieces/")

        toggle = page.locator(f"[data-testid=toggle-{piece.pk}]")
        expect(toggle).to_contain_text("Inactive")

        toggle.click()
        page.wait_for_load_state("networkidle")
        expect(toggle).to_contain_text("Active")
