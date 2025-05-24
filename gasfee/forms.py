from django import forms
from .models import Crypto

class CryptoForm(forms.ModelForm):
    class Meta:
        model = Crypto
        fields = ['name', 'symbol', 'coingecko_id', 'network', 'logo']  # Include logo
        widgets = {
            'network': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500'}),
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500'}),
            'symbol': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500'}),
            'coingecko_id': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500'}),
            'logo': forms.FileInput(attrs={'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['logo'].required = False  # Make logo optional