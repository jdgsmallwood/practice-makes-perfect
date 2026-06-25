from django import forms

from .models import Piece, TrickyBit

_INPUT = "bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder-gray-500"
_SELECT = "bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
_TEXTAREA = "bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none placeholder-gray-500"


class PieceForm(forms.ModelForm):
    class Meta:
        model = Piece
        fields = ["name", "composer", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "e.g. Syrinx"}),
            "composer": forms.TextInput(attrs={"class": _INPUT, "placeholder": "e.g. Debussy"}),
            "is_active": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded accent-indigo-500"}
            ),
        }


class TrickyBitForm(forms.ModelForm):
    class Meta:
        model = TrickyBit
        fields = [
            "label",
            "image",
            "description",
            "desired_tempo",
            "current_tempo",
            "difficulty",
            "key_signature",
            "tags",
        ]
        widgets = {
            "label": forms.TextInput(
                attrs={"class": _INPUT, "placeholder": "e.g. bars 42-48, high D run"}
            ),
            "image": forms.FileInput(
                attrs={
                    "id": "id_image",
                    "class": "hidden",
                    "accept": "image/*",
                }
            ),
            "description": forms.Textarea(
                attrs={"class": _TEXTAREA, "rows": 3, "placeholder": "Notes on this passage…"}
            ),
            "desired_tempo": forms.NumberInput(
                attrs={"class": _INPUT, "placeholder": "120", "min": 1, "max": 999}
            ),
            "current_tempo": forms.NumberInput(
                attrs={"class": _INPUT, "placeholder": "80", "min": 1, "max": 999}
            ),
            "difficulty": forms.Select(attrs={"class": _SELECT}),
            "key_signature": forms.Select(attrs={"class": _SELECT}),
            "tags": forms.TextInput(
                attrs={"class": _INPUT, "placeholder": "legato, high-register, thirds"}
            ),
        }
