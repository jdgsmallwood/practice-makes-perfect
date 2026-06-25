"""End-to-end browser tests for the long tones practice section."""
import pytest
from playwright.sync_api import Page, expect

from longtones.utils import FOCUS_CHOICES, session_notes_for_date


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestLongTonesHome:
    def test_home_page_loads(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        expect(page).to_have_title("Long Tones — Practice")

    def test_todays_notes_section_visible(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        expect(page.locator("text=Today's notes")).to_be_visible()

    def test_note_chips_rendered(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        note_count = len(session_notes_for_date())
        # Each note renders as a chip span with font-mono class
        chips = page.locator("span.font-mono.font-semibold")
        expect(chips).to_have_count(note_count)

    def test_five_focus_radio_buttons(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        expect(page.locator("input[name=focus]")).to_have_count(len(FOCUS_CHOICES))

    def test_focus_preview_appears_on_selection(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        page.click("input[name=focus][value=steadiness]")
        page.wait_for_timeout(300)
        expect(page.locator("[x-show='focus']")).to_be_visible()

    def test_focus_preview_shows_prompt_text(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        page.click("input[name=focus][value=body_scan]")
        page.wait_for_timeout(300)
        # Body scan prompt mentions "scan"
        expect(page.locator("[x-show='focus']")).to_contain_text("scan")

    def test_drone_checkbox_present(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        expect(page.locator("input[name=use_drone]")).to_be_visible()

    def test_start_button_shows_note_count(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        note_count = len(session_notes_for_date())
        expect(page.get_by_role("button", name=f"Start Session — {note_count} note")).to_be_visible()

    def test_sidebar_nav_link_present(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        expect(page.get_by_role("link", name="Long Tones").first).to_be_visible()


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestLongTonesSession:
    def _start(self, page: Page, live_server, focus="steadiness", use_drone=False):
        page.goto(live_server.url + "/long-tones/")
        page.click(f"input[name=focus][value={focus}]")
        if not use_drone:
            checkbox = page.locator("input[name=use_drone]")
            if checkbox.is_checked():
                checkbox.uncheck()
        page.click("button[type=submit]")
        page.wait_for_url(f"{live_server.url}/long-tones/session/")

    def test_session_page_loads(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page).to_have_url(f"{live_server.url}/long-tones/session/")

    def test_note_name_shown(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        first_note = session_notes_for_date()[0]
        from longtones.utils import MIDI_NAMES
        expected_name = MIDI_NAMES[first_note]
        expect(page.get_by_role("heading", name=expected_name)).to_be_visible()

    def test_hz_value_shown(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.locator("text=Hz")).to_be_visible()

    def test_focus_prompt_visible(self, page: Page, live_server, with_profile):
        self._start(page, live_server, focus="crescendo")
        expect(page.locator("text=Crescendo")).to_be_visible()

    def test_five_rating_forms(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.locator("form[action*='session/log']")).to_have_count(5)

    def test_skip_link_visible(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.locator("text=Skip (come back later)")).to_be_visible()

    def test_metronome_controls_visible(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        expect(page.locator("text=Metronome")).to_be_visible()

    def test_drone_button_hidden_when_use_drone_off(self, page: Page, live_server, with_profile):
        self._start(page, live_server, use_drone=False)
        expect(page.locator("text=Drone Off")).not_to_be_visible()

    def test_drone_button_visible_when_use_drone_on(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/")
        page.click("input[name=focus][value=steadiness]")
        checkbox = page.locator("input[name=use_drone]")
        if not checkbox.is_checked():
            checkbox.check()
        page.click("button[type=submit]")
        page.wait_for_url(f"{live_server.url}/long-tones/session/")
        expect(page.locator("text=Drone Off")).to_be_visible()

    def test_rating_advances_to_next_note(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        notes = session_notes_for_date()
        from longtones.utils import MIDI_NAMES
        second_note_name = MIDI_NAMES[notes[1]]
        page.locator("form[action*='session/log']").nth(3).locator("button").click()
        page.wait_for_url(f"{live_server.url}/long-tones/session/")
        expect(page.get_by_role("heading", name=second_note_name)).to_be_visible()

    def test_skip_defers_to_next_note(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        notes = session_notes_for_date()
        from longtones.utils import MIDI_NAMES
        second_note_name = MIDI_NAMES[notes[1]]
        page.locator("text=Skip (come back later)").click()
        page.wait_for_url(f"{live_server.url}/long-tones/session/")
        expect(page.get_by_role("heading", name=second_note_name)).to_be_visible()

    def test_progress_counter_decrements_on_rating(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        total = len(session_notes_for_date())
        expect(page.locator(f"text={total} / {total}")).to_be_visible()
        page.locator("form[action*='session/log']").nth(3).locator("button").click()
        page.wait_for_url(f"{live_server.url}/long-tones/session/")
        expect(page.locator(f"text={total - 1} / {total}")).to_be_visible()

    def test_completing_all_notes_reaches_complete_page(self, page: Page, live_server, with_profile):
        self._start(page, live_server)
        total = len(session_notes_for_date())
        for _ in range(total):
            page.locator("form[action*='session/log']").nth(3).locator("button").click()
            page.wait_for_load_state("networkidle")
        expect(page).to_have_url(f"{live_server.url}/long-tones/complete/")
        expect(page.get_by_text("Done!")).to_be_visible()


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestLongTonesComplete:
    def _complete_session(self, page: Page, live_server, focus="steadiness"):
        page.goto(live_server.url + "/long-tones/")
        page.click(f"input[name=focus][value={focus}]")
        checkbox = page.locator("input[name=use_drone]")
        if checkbox.is_checked():
            checkbox.uncheck()
        page.click("button[type=submit]")
        page.wait_for_url(f"{live_server.url}/long-tones/session/")
        total = len(session_notes_for_date())
        for _ in range(total):
            page.locator("form[action*='session/log']").nth(3).locator("button").click()
            page.wait_for_load_state("networkidle")

    def test_complete_shows_done(self, page: Page, live_server, with_profile):
        self._complete_session(page, live_server)
        expect(page.get_by_text("Done!")).to_be_visible()

    def test_complete_shows_focus_name(self, page: Page, live_server, with_profile):
        self._complete_session(page, live_server, focus="intonation")
        expect(page.get_by_text("Intonation")).to_be_visible()

    def test_complete_shows_average_rating(self, page: Page, live_server, with_profile):
        self._complete_session(page, live_server)
        expect(page.locator("text=Average rating")).to_be_visible()

    def test_complete_shows_per_note_summary(self, page: Page, live_server, with_profile):
        self._complete_session(page, live_server)
        expect(page.locator("text=This session")).to_be_visible()
        # Each note should appear as a row with its name
        notes = session_notes_for_date()
        from longtones.utils import MIDI_NAMES
        first_note_name = MIDI_NAMES[notes[0]]
        expect(page.locator(f"text={first_note_name}")).to_be_visible()

    def test_go_again_link_returns_to_home(self, page: Page, live_server, with_profile):
        page.goto(live_server.url + "/long-tones/complete/")
        page.get_by_role("link", name="Go again").click()
        expect(page).to_have_url(f"{live_server.url}/long-tones/")
