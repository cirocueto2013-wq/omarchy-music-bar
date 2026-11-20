# Music Bar

The user pinned Omarchy's own visual system and a monochrome YouTube Music service mark beside the weather. A click opens the same native KeyboardPanel used by shell popovers. The panel is 410 logical pixels wide, with search at the top, Recent/Results tabs, a scrollable track list, and a compact audio transport below.

Use qs.Ui and qs.Commons for colors, type, border geometry, rounding, focus, animation and spacing. Every dynamic label is Text.PlainText; shared tooltips contain only translated static text. English and Spanish catalogs follow Omarchy's live language selection.

Version 2 removes the browser/account/library integration. Public search and mpv playback operate independently of Chrome. Recent means local playback history, never a user's private account history.
