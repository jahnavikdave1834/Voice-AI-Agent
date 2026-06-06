import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import importlib.util

slot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dialogue_management', 'slot_extractor.py'))
spec = importlib.util.spec_from_file_location('slot_extractor', slot_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SlotExtractor = mod.SlotExtractor

se = SlotExtractor(api_key=None)

slots = {"service_type": None, "date": None, "time": None, "name": None, "contact": None, "email": None}

print('email:', se._extract_email_from_text('J-A-H-N-A-V-I-K-D-A-V-E 1834 at gmail.com'))
print('fallback date:', se._fallback_extract('7 June', slots.copy(), current_field='date'))
print('fallback time pm:', se._fallback_extract('6 p.m.', slots.copy(), current_field='time'))

# Debug o'clock matching details
print("--- o'clock debug ---")
text = "10 o'clock"
print('raw:', text)
print('normalize_time_text:', se._normalize_time_text(text))
# Try pattern matching as used in fallback
import re
patterns = [
	r"\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b",
	r"\b([1-9]|1[0-2])\s?(?:a\.m\.|p\.m\.|am|pm)\b",
	r"\b([1-9]|1[0-2])(:[0-5][0-9])?\s?(?:a\.m\.|p\.m\.|am|pm)\b",
	r"\b([1-9]|1[0-2])\s?(?:o'clock|o’clock|oclock)\b",
]
time_source = text.lower().replace('.', '')
time_source = re.sub(r"o['’]?clock", 'oclock', time_source)
print('time_source for matching:', time_source)
for p in patterns:
	m = re.search(p, time_source)
	print('pattern:', p, 'match:', bool(m), 'group:', m.group() if m else None)
	if m:
		norm = se._normalize_time_text(m.group())
		print('normalized match ->', norm)
		try:
			import dateparser
			parsed = dateparser.parse(norm)
		except Exception as e:
			parsed = f'error: {e}'
		print('dateparser.parse ->', parsed)

print("fallback time o'clock:", se._fallback_extract("10 o'clock", slots.copy(), current_field='time'))
