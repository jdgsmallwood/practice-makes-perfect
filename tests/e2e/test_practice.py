from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect

from pieces.models import PracticeLog, TrickyBit
from tests.factories import PieceFactory, TrickyBitFactory


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestPracticeSession:
    def test_no_due_bits_redirects_to_complete(self, page: Page, live_server):
        page.goto(live_server.url + "/practice/")
        expect(page).to_have_url(f"{live_server.url}/practice/complete/")

    def test_inactive_piece_not_in_queue(self, page: Page, live_server):
        piece = PieceFactory(is_active=False)
        TrickyBitFactory(piece=piece)
        page.goto(live_server.url + "/practice/")
        expect(page).to_have_url(f"{live_server.url}/practice/complete/")

    def test_due_bit_shown_in_session(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece, label="The Hard Bit", next_review_at=None)
        page.goto(live_server.url + "/practice/")
        expect(page.get_by_role("heading", name="The Hard Bit")).to_be_visible()

    def test_piece_name_shown_above_label(self, page: Page, live_server):
        piece = PieceFactory(name="Syrinx", is_active=True)
        TrickyBitFactory(piece=piece, next_review_at=None)
        page.goto(live_server.url + "/practice/")
        expect(page.get_by_text("Syrinx")).to_be_visible()

    def test_four_rating_buttons_visible(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece)
        page.goto(live_server.url + "/practice/")

        rating_form = page.locator("[data-testid=rating-form]")
        expect(rating_form.get_by_role("button", name="Again")).to_be_visible()
        expect(rating_form.get_by_role("button", name="Hard")).to_be_visible()
        expect(rating_form.get_by_role("button", name="Good")).to_be_visible()
        expect(rating_form.get_by_role("button", name="Easy")).to_be_visible()

    def test_rating_again_creates_practice_log(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=rating-form]").get_by_role("button", name="Again").click()
        page.wait_for_load_state("networkidle")

        assert PracticeLog.objects.filter(tricky_bit=bit, rating=1).count() == 1

    def test_rating_good_advances_interval(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece, next_review_at=None)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=rating-form]").get_by_role("button", name="Good").click()
        page.wait_for_load_state("networkidle")

        bit.refresh_from_db()
        assert bit.interval_days == 1
        assert bit.repetitions == 1
        assert bit.next_review_at is not None

    def test_rating_easy_increases_ease_factor(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece, next_review_at=None)
        original_ease = bit.ease_factor
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=rating-form]").get_by_role("button", name="Easy").click()
        page.wait_for_load_state("networkidle")

        bit.refresh_from_db()
        assert bit.ease_factor > original_ease

    def test_rating_again_resets_interval(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        # Simulate a bit that was previously reviewed (has interval)
        bit = TrickyBitFactory(
            piece=piece,
            interval_days=10,
            repetitions=3,
            ease_factor=2.5,
            next_review_at=None,
        )
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=rating-form]").get_by_role("button", name="Again").click()
        page.wait_for_load_state("networkidle")

        bit.refresh_from_db()
        assert bit.interval_days == 1
        assert bit.repetitions == 0

    def test_after_all_bits_rated_redirects_to_complete(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, next_review_at=None)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=rating-form]").get_by_role("button", name="Good").click()
        page.wait_for_url(f"{live_server.url}/practice/complete/")
        expect(page.get_by_text("Session complete!")).to_be_visible()


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestSkipButton:
    def test_skip_button_visible(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece)
        page.goto(live_server.url + "/practice/")
        expect(page.locator("[data-testid=skip-form]")).to_be_visible()

    def test_skip_defers_bit_not_rates_it(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece, next_review_at=None)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=skip-form]").get_by_role("button").click()
        page.wait_for_load_state("networkidle")

        # No PracticeLog should be created
        assert PracticeLog.objects.filter(tricky_bit=bit).count() == 0
        # SM-2 state unchanged
        bit.refresh_from_db()
        assert bit.repetitions == 0
        assert bit.next_review_at is None

    def test_skipped_bit_reappears_after_others(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit_a = TrickyBitFactory(piece=piece, label="Bit A", next_review_at=None)
        bit_b = TrickyBitFactory(piece=piece, label="Bit B", next_review_at=None)
        page.goto(live_server.url + "/practice/")

        # Skip the first bit that appears
        page.locator("[data-testid=skip-form]").get_by_role("button").click()
        page.wait_for_load_state("networkidle")

        # The other bit should now be shown (or we're still in the queue)
        # Eventually the skipped bit will reappear — session should not be complete
        expect(page).not_to_have_url(f"{live_server.url}/practice/complete/")

    def test_skip_shows_skipped_count(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, label="Bit A", next_review_at=None)
        TrickyBitFactory(piece=piece, label="Bit B", next_review_at=None)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=skip-form]").get_by_role("button").click()
        page.wait_for_load_state("networkidle")

        # After skipping one bit, the skip form should mention the count
        skip_form = page.locator("[data-testid=skip-form]")
        expect(skip_form).to_contain_text("1")


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestPracticeComplete:
    def test_complete_page_loads(self, page: Page, live_server):
        page.goto(live_server.url + "/practice/complete/")
        expect(page).to_have_title("Session Complete — Practice Makes Perfect")
        expect(page.get_by_text("Session complete!")).to_be_visible()

    def test_complete_page_shows_reviewed_count(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece, next_review_at=None)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=rating-form]").get_by_role("button", name="Good").click()
        page.wait_for_url(f"{live_server.url}/practice/complete/")

        expect(page.get_by_text("1 passage today")).to_be_visible()

    def test_complete_page_back_to_dashboard_link(self, page: Page, live_server):
        page.goto(live_server.url + "/practice/complete/")
        page.get_by_role("link", name="Back to Dashboard").click()
        expect(page).to_have_url(f"{live_server.url}/")
