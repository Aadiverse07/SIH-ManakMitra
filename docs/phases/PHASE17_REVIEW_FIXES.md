# Phase 17 review fixes

Found while checking the 9 requested changes; fixed in this zip.

1. `api/api.js` never exposed the saved/download helpers, so `MM_DATA.downloadStandardPdf`, `MM_DATA.downloadResourcePdf`, `MM_DATA.isStandardSaved`, `MM_DATA.toggleStandardSaved`, `MM_DATA.getSavedStandards` and `MM_DATA.removeStandard` were undefined (items 5 and 6 failed; standards detail panel also errored). `js/app.js` now attaches them to `window.MM_DATA`.
2. `js/nav.js`: the sidebar toggle was bound before the sidebar existed, so it did nothing (item 8). `renderSidebar()` now binds it, and also calls `refreshAuthUI()` so Logout/Log in and its click handler are correct (item 9).
3. `js/auth.js`: `mmGetChatHistory` returned the OLDEST 100 messages; it now returns the latest 100 in chronological order (item 4).
4. `css/style.css`: My Documents cards still showed the glow / scanning-grid overlay on hover; now suppressed (items 3, 6). Mobile sidebar layout restored to a horizontal row.
5. `js/assistant.js` / `assistant.html`: sent voice question no longer lingers in the recorder buffer; speech stops when a new question is sent.
6. `js/app.js`: generated PDFs had a corrupt xref table (binary header byte-length mismatch); header is now ASCII so the PDFs are valid.

## Round 2 (History hover + scroll blanking)

7. History page (`history.html`, `.history-page` in `css/style.css`): removed the 3-D tilt, glow and scanning-grid hover from the big list card, and gave the query rows a light hover (faint background + 2px shift). The tilt was warping long lists (rows skewed/scaled while scrolling) and the card carried a large `backdrop-filter`, which can make tiles blank out on tall layers.
8. `js/app.js`: tilt is now skipped for any card taller than 520px on every page.
9. Ask AI (`.chat-scroll`, `.chat-input-bar`): `overscroll-behavior: contain` so scroll does not chain out at the end, `100dvh` so mobile browser bars do not cut the bottom, input bar no longer uses `backdrop-filter`, and on phones the chat fills the space left under the sidebar row instead of assuming 64px.
