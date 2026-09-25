# ManakMitra — UI/Interaction Fixes

Updated from `phase17_math_voice_fixed_AUDITED.zip`.

Implemented:
1. Left sidebar `Home` renamed to `Dashboard`.
2. Ask AI layout made viewport-contained to prevent outer-page blank/scroll bleed at the end of chat.
3. My Documents hover/tilt effects reduced to a restrained 2px hover.
4. Chat queries are persisted server-side per authenticated conversation: user message is inserted immediately, assistant reply after generation; History refreshes automatically.
5. Standards Save now persists selected standard numbers in browser storage and the Saved page shows only standards actually saved. Standard downloads now create a real PDF catalogue record.
6. My Documents download cards now generate real PDF files for the three requested items; they are clearly marked as ManakMitra reference downloads, not official BIS publications.
7. Voice assistant now supports Record, Pause, Send voice, Cancel, and Stop speaking. Voice input no longer auto-submits as soon as recognition ends.
8. Sidebar has a collapse/expand control that slides module labels away and restores them.
9. Authenticated sidebar action displays `Logout` and uses the existing Supabase sign-out flow.

Validation:
- `node --check` passed for modified frontend JS files.
- Python compile check passed for `backend/app/api/routes/chat.py`.
