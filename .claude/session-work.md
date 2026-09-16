# Session Work — hermes-agent

_Maintained by `/close` and the M4 gateway closeout. Top zone regenerates each run; the log appends.
On opening this project, read this file to rehydrate._

## Current State
_updated: 2026-09-16 13:50 (M4 gateway closeout)_

- **Project**: hermes-agent · branch `main` · `dfd3de3` — feat(desktop): honor per-profile display.sections visibility in chat
- **Working tree**: clean
- **Preflight**: not run — skipped by the work order
- **Where to test**: Hermes Desktop app (native, not a website) — open a Bot Chat for cali/link/scout/scribe/switch after RCKT Bot restarts the app from the freshly packaged bundle at /Users/m4/.hermes/hermes-agent/apps/desktop/release/mac-arm64/Hermes.app — local native app on this machine, no login/password involved
- **Next step**: The interpretation of what counts as 'activity/progress scaffold' on Desktop (mapped to the composer status stack's background-process rows only, not the goal indicator) since the work order didn't enumerate exact desktop UI elements — worth a quick visual check against the original screenshot evidence.

### Mid-finished / blockers
- [ ] SessionControlSections (Goal Mode heartbeat/loop ambient notices) was deliberately left ungated — out of evidenced scope, low usage by these simple bot profiles, and it already shows an error banner that must stay visible regardless.
- [ ] The goal indicator group in the composer status stack is intentionally NOT gated by display.sections.activity (a regression run against the existing goal-indicator/session-control test suite showed it's treated as primary Goal Mode status, not ambient meta, in existing product behavior) — flagging in case product intent differs from what the existing tests assume.

### Decisions (don't re-litigate)
- none yet

---

## Session log

### 2026-09-16 13:50 — M4 gateway job (completed)
- Desktop now honors per-profile display.show_reasoning / display.tool_progress / display.details_mode / display.sections.{thinking,tools,subagents,activity} by resolving them client-side (mirroring the TUI's existing domain/details.ts precedence) into a new $displaySections store, then gating the reasoning disclosure, ordinary tool-call rows, and the composer status stack's subagent roster and background-process rows so hidden sections render no DOM at all — live streaming and resumed transcript history alike — while clarify prompts, failed/dangling tool calls, approvals, the goal indicator, and the final reply stay visible.
- Verified: Reproduced the root cause: tui_gateway already streams every reasoning/tool-progress event to Desktop regardless of display config (only the CLI/TUI filtered client-side), confirmed against tui_gateway/agent_callbacks.py and server.py. Wrote 19 new focused invariant tests (display-sections.test.ts resolver precedence incl. the exact cali/link/scout/scribe/switch profile shape; message-parts-display-sections.test.tsx for hidden-live/hidden-settled reasoning, hidden ordinary tool rows vs. preserved error/clarify rows, and final text staying visible; display-sections.test.tsx for the composer status stack's subagent/background hiding) — all pass. Ran the full targeted sweep (src/components/assistant-ui, src/app/chat/composer/status-stack, src/app/session/hooks, src/store — 278 files / 3031 tests): only 2 pre-existing, unrelated voice-prefs.test.ts failures remain, confirmed identical on a clean checkout via git stash. `npm run typecheck` (all three tsconfigs) and `npm run build` both pass clean. `npm run pack` produced release/mac-arm64/Hermes.app successfully (unsigned/no notarization, as expected without Apple credentials in this environment). Copied the verified bundle into /Users/m4/.hermes/hermes-agent/apps/desktop/release/mac-arm64/Hermes.app via ditto + atomic swap; confirmed via `ps aux` that the running Hermes.app (PID 6380) and its hermes serve backend (PID 4811) are both still running untouched, unaware of the swap until their next restart.
- Pushed to `main`
