import pytest
from playwright.sync_api import Page, expect

from tests.factories import PieceFactory, TrickyBitFactory


@pytest.mark.django_db(transaction=True)
@pytest.mark.e2e
class TestTrickyBitForm:
    def test_add_passage_form_loads(self, page: Page, live_server):
        piece = PieceFactory()
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/add/")
        expect(page).to_have_title(f"Add Passage — {piece.name} — Practice Makes Perfect")

    def test_add_passage_image_dropzone_visible(self, page: Page, live_server):
        piece = PieceFactory()
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/add/")
        expect(page.locator("[data-testid=image-dropzone]")).to_be_visible()

    def test_add_passage_without_image(self, page: Page, live_server):
        piece = PieceFactory()
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/add/")
        page.fill("[name=label]", "High D run bars 42-48")
        page.fill("[name=current_tempo]", "80")
        page.fill("[name=desired_tempo]", "120")
        page.select_option("[name=difficulty]", "4")
        page.fill("[name=tags]", "high-register, runs")
        page.fill("[name=description]", "Struggle with the D-E-F# fingering here")
        page.click("[type=submit]")

        # Redirected to piece detail
        expect(page).to_have_title(f"{piece.name} — Practice Makes Perfect")
        expect(page.get_by_text("High D run bars 42-48")).to_be_visible()

    def test_add_passage_requires_label(self, page: Page, live_server):
        piece = PieceFactory()
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/add/")
        page.click("[type=submit]")
        # Should stay on form page due to validation error
        expect(page).to_have_url(f"{live_server.url}/pieces/{piece.pk}/bits/add/")

    def test_add_passage_appears_in_piece_detail(self, page: Page, live_server):
        piece = PieceFactory()
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/add/")
        page.fill("[name=label]", "Tricky Coda")
        page.click("[type=submit]")

        expect(page.locator("[data-testid^=trickybit-card]")).to_have_count(1)

    def test_edit_passage(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, label="Original Label")
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/edit/")
        page.fill("[name=label]", "Updated Label")
        page.click("[type=submit]")

        expect(page.get_by_text("Updated Label")).to_be_visible()
        expect(page.get_by_text("Original Label")).not_to_be_visible()

    def test_delete_passage(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, label="To Be Deleted")
        page.goto(live_server.url + f"/pieces/{piece.pk}/")

        # Click delete and confirm the dialog
        page.on("dialog", lambda d: d.accept())
        page.locator(f"[data-testid=trickybit-card-{bit.pk}]").get_by_role(
            "button", name="Delete"
        ).click()

        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("To Be Deleted")).not_to_be_visible()

    def test_key_signature_select_visible_in_add_form(self, page: Page, live_server):
        piece = PieceFactory()
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/add/")
        expect(page.locator("[name=key_signature]")).to_be_visible()

    def test_add_passage_saves_key_signature(self, page: Page, live_server):
        from pieces.models import TrickyBit

        piece = PieceFactory()
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/add/")
        page.fill("[name=label]", "Opening Theme")
        page.select_option("[name=key_signature]", "G")
        page.click("[type=submit]")

        expect(page).to_have_title(f"{piece.name} — Practice Makes Perfect")
        bit = TrickyBit.objects.get(piece=piece, label="Opening Theme")
        assert bit.key_signature == "G"

    def test_edit_form_prepopulates_key_signature(self, page: Page, live_server):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece, key_signature="Bb")
        page.goto(live_server.url + f"/pieces/{piece.pk}/bits/{bit.pk}/edit/")
        assert page.locator("[name=key_signature]").input_value() == "Bb"
