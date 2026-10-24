"""Manual review checklists. Outcomes are stored separately and always labelled 'manual'."""
from __future__ import annotations

CHECKLIST = [
    {"id": "kbd-reach", "area": "Keyboard", "check": "Every interactive element can be reached and operated with Tab / Shift+Tab / Enter / Space / arrows."},
    {"id": "kbd-trap", "area": "Keyboard", "check": "No keyboard trap: you can always move focus away (modals can be closed with Esc)."},
    {"id": "kbd-order", "area": "Keyboard", "check": "Tab order follows the visual and logical reading order."},
    {"id": "kbd-skip", "area": "Keyboard", "check": "A 'skip to main content' link is available and works."},
    {"id": "focus-visible", "area": "Focus", "check": "Focus indicator is always clearly visible (not removed with outline:none)."},
    {"id": "focus-manage", "area": "Focus", "check": "Focus moves sensibly after dialogs open/close, route changes and inline errors."},
    {"id": "sr-headings", "area": "Screen reader", "check": "Headings and landmarks give a sensible outline (NVDA/JAWS/VoiceOver rotor)."},
    {"id": "sr-names", "area": "Screen reader", "check": "Links, buttons and form fields announce meaningful name, role and state."},
    {"id": "sr-images", "area": "Screen reader", "check": "Informative images have accurate alt text; decorative images are silent."},
    {"id": "sr-live", "area": "Screen reader", "check": "Dynamic updates and form errors are announced (aria-live / role=alert)."},
    {"id": "zoom-reflow", "area": "Visual", "check": "At 200% zoom / 320px width content reflows without loss or horizontal scroll."},
    {"id": "contrast", "area": "Visual", "check": "Text and UI component contrast meets 4.5:1 / 3:1."},
]
OUTCOMES = ["pass", "fail", "not applicable", "not tested"]
