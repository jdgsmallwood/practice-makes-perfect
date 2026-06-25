"""End-to-end browser tests for the articulation practice section."""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestArticulationHome:
    def test_home_page_loads(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/articulation/")
        expect(page).to_have_title("Articulation — Practice")

    def test_three_track_radio_buttons(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/articulation/")
        expect(page.locator("input[name=track]")).to_have_count(3)

    def test_exercise_preview_appears_on_single_tongue_select(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/articulation/")
        page.click("input[name=track][value=single]")
        page.wait_for_timeout(300)
        preview = page.locator("[x-show='track'] ol")
        expect(preview.get_by_text("Air Only")).to_be_visible()
        expect(preview.get_by_text("Speed Ladder")).to_be_visible()

    def test_exercise_preview_updates_for_double_tongue(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/articulation/")
        page.click("input[name=track][value=double]")
        page.wait_for_timeout(300)
        preview = page.locator("[x-show='track'] ol")
        expect(preview.get_by_text("Ku Only")).to_be_visible()
        expect(preview.get_by_text("Speed Build")).to_be_visible()

    def test_sidebar_nav_link_present(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/articulation/")
        expect(page.get_by_role("link", name="Articulation").first).to_be_visible()


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestArticulationSession:
    def _start(self, page: Page, live_server, track="single"):
        page.goto(live_server.url + "/articulation/")
        page.click(f"input[name=track][value={track}]")
        page.click("button[type=submit]")
        page.wait_for_url(f"{live_server.url}/articulation/session/")

    def test_first_st_exercise_is_air_only(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.get_by_role("heading", name="Air Only")).to_be_visible()

    def test_coaching_cue_box_present(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.locator("text=Coaching Cue")).to_be_visible()

    def test_tension_check_banner_present(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.locator("text=Tension check")).to_be_visible()

    def test_metronome_pre_set_to_60_bpm_for_air_only(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        page.wait_for_timeout(600)
        expect(page.get_by_text("60 bpm", exact=True)).to_be_visible()

    def test_subdivision_buttons_visible(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.locator("button", has_text="♩").first).to_be_visible()

    def test_five_rating_forms(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.locator("form[action*='session/log']")).to_have_count(5)

    def test_rating_advances_to_next_exercise(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        page.locator("form[action*='session/log']").nth(3).locator("button").click()
        page.wait_for_url(f"{live_server.url}/articulation/session/")
        expect(page.get_by_role("heading", name="Ghost Touch")).to_be_visible()

    def test_metronome_bpm_updates_between_exercises(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        page.wait_for_timeout(400)
        # ST_1 is 60 bpm; rate it and ST_4 (Steady Eighths) should be 80 bpm
        for _ in range(3):
            page.locator("form[action*='session/log']").nth(3).locator("button").click()
            page.wait_for_url(f"{live_server.url}/articulation/session/")
        page.wait_for_timeout(600)
        expect(page.locator("text=80 bpm")).to_be_visible()

    def test_skip_defers_exercise(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        page.locator("text=Skip (come back later)").click()
        page.wait_for_url(f"{live_server.url}/articulation/session/")
        expect(page.get_by_role("heading", name="Ghost Touch")).to_be_visible()

    def test_completing_double_session_reaches_complete_page(self, page: Page, live_server, with_profile):
        self._start(page, live_server, track="double")
        for _ in range(4):
            page.locator("form[action*='session/log']").nth(3).locator("button").click()
            page.wait_for_load_state("networkidle")
        expect(page).to_have_url(f"{live_server.url}/articulation/complete/")
        expect(page.get_by_text("Done!")).to_be_visible()

    def test_progress_counter_decrements(self, page: Page, live_server, with_profile):
        self._start(page, live_server, track="double")
        expect(page.locator("text=4 / 4")).to_be_visible()
        page.locator("form[action*='session/log']").nth(3).locator("button").click()
        page.wait_for_url(f"{live_server.url}/articulation/session/")
        expect(page.locator("text=3 / 4")).to_be_visible()


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestArticulationComplete:
    def _complete_session(self, page: Page, live_server, track="double"):
        page.goto(live_server.url + "/articulation/")
        page.click(f"input[name=track][value={track}]")
        page.click("button[type=submit]")
        page.wait_for_url(f"{live_server.url}/articulation/session/")
        count = 4 if track == "double" else 5
        for _ in range(count):
            page.locator("form[action*='session/log']").nth(3).locator("button").click()
            page.wait_for_load_state("networkidle")

    def test_complete_page_shows_done(self, page: Page, live_server, with_profile):
        self._complete_session(page, live_server)
        expect(page.get_by_text("Done!")).to_be_visible()

    def test_complete_page_shows_track_name(self, page: Page, live_server, with_profile):
        self._complete_session(page, live_server)
        expect(page.get_by_text("Double Tongue")).to_be_visible()

    def test_complete_page_shows_exercise_names(self, page: Page, live_server, with_profile):
        self._complete_session(page, live_server)
        expect(page.get_by_text("Ku Only")).to_be_visible()
        expect(page.get_by_text("Speed Build")).to_be_visible()

    def test_go_again_link_returns_to_home(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/articulation/complete/")
        page.get_by_role("link", name="Go again").click()
        expect(page).to_have_url(f"{live_server.url}/articulation/")
