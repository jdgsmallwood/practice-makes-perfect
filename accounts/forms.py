from django import forms

from .models import Profile

_INPUT = "bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder-gray-500"
_SELECT = "bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["name", "instrument"]
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "e.g. Flute"}),
            "instrument": forms.Select(attrs={"class": _SELECT}),
        }
