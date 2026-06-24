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

    def test_achieved_tempo_input_visible_when_no_ladder(self, page: Page, live_server):
        # Bit with no tempo → no ladder → rating form + tempo input immediately visible
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece)   # no tempo → no ladder
        page.goto(live_server.url + "/practice/")
        expect(page.locator("[data-testid=achieved-tempo-input]")).to_be_visible()

    def test_achieved_tempo_updates_on_rating(self, page: Page, live_server):
        # Use a bit without tempo so rating form is immediate (no ladder)
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece, next_review_at=None)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=achieved-tempo-input]").fill("95")
        page.locator("[data-testid=rating-form]").get_by_role("button", name="Good").click()
        page.wait_for_load_state("networkidle")

        bit.refresh_from_db()
        assert bit.current_tempo == 95

    def test_blank_achieved_tempo_leaves_current_unchanged(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece, current_tempo=80, next_review_at=None)
        page.goto(live_server.url + "/practice/")

        # Skip the ladder so rating form is visible
        page.locator("[data-testid=skip-to-rating]").click()
        page.wait_for_timeout(150)

        page.locator("[data-testid=achieved-tempo-input]").clear()
        page.locator("[data-testid=rating-form]").get_by_role("button", name="Good").click()
        page.wait_for_load_state("networkidle")

        bit.refresh_from_db()
        assert bit.current_tempo == 80   # unchanged


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


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestTempoLadder:
    def test_ladder_shown_when_tempos_set(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, current_tempo=80, desired_tempo=120)
        page.goto(live_server.url + "/practice/")
        expect(page.locator("[data-testid=tempo-ladder]")).to_be_visible()

    def test_rating_form_hidden_while_ladder_active(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, current_tempo=80, desired_tempo=120)
        page.goto(live_server.url + "/practice/")
        expect(page.locator("[data-testid=rating-form]")).not_to_be_visible()

    def test_no_ladder_without_tempos(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece)   # no tempo fields
        page.goto(live_server.url + "/practice/")
        expect(page.locator("[data-testid=tempo-ladder]")).not_to_be_visible()
        expect(page.locator("[data-testid=rating-form]")).to_be_visible()

    def test_got_it_advances_to_next_step_or_rating(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, current_tempo=80, desired_tempo=120)
        page.goto(live_server.url + "/practice/")

        # Click through all "Got it" buttons until ladder finishes
        for _ in range(10):  # ladder is at most ~4 steps
            got_it = page.locator("[data-testid=got-it-btn]")
            if not got_it.is_visible():
                break
            got_it.click()
            page.wait_for_timeout(100)

        # Rating form should now be visible
        expect(page.locator("[data-testid=rating-form]")).to_be_visible()

    def test_too_fast_shows_rating_immediately(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, current_tempo=80, desired_tempo=120)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=too-fast-btn]").click()
        page.wait_for_timeout(100)

        expect(page.locator("[data-testid=rating-form]")).to_be_visible()
        expect(page.locator("[data-testid=tempo-ladder]")).not_to_be_visible()

    def test_skip_to_rating_shows_form(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, current_tempo=80, desired_tempo=120)
        page.goto(live_server.url + "/practice/")

        page.locator("[data-testid=skip-to-rating]").click()
        page.wait_for_timeout(100)

        expect(page.locator("[data-testid=rating-form]")).to_be_visible()

    def test_completing_ladder_prefills_achieved_tempo(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        TrickyBitFactory(piece=piece, current_tempo=80, desired_tempo=120)
        page.goto(live_server.url + "/practice/")

        # Click "Got it" on every step
        for _ in range(10):
            btn = page.locator("[data-testid=got-it-btn]")
            if not btn.is_visible():
                break
            btn.click()
            page.wait_for_timeout(100)

        # The achieved BPM input should be filled with the last ladder tempo
        val = page.locator("[data-testid=achieved-tempo-input]").input_value()
        assert val != ""
        assert int(val) > 80   # should have reached push step above current

    def test_completing_ladder_and_rating_updates_current_tempo(self, page: Page, live_server):
        piece = PieceFactory(is_active=True)
        bit = TrickyBitFactory(piece=piece, current_tempo=80, desired_tempo=120, next_review_at=None)
        page.goto(live_server.url + "/practice/")

        # Click "Got it" through all steps
        for _ in range(10):
            btn = page.locator("[data-testid=got-it-btn]")
            if not btn.is_visible():
                break
            btn.click()
            page.wait_for_timeout(100)

        page.locator("[data-testid=rating-form]").get_by_role("button", name="Good").click()
        page.wait_for_load_state("networkidle")

        bit.refresh_from_db()
        assert bit.current_tempo is not None
        assert bit.current_tempo > 80   # ladder pushed beyond starting tempo
