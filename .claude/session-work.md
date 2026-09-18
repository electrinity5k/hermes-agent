# Session Work — hermes-agent

_Maintained by `/close` and the M4 gateway closeout. Top zone regenerates each run; the log appends.
On opening this project, read this file to rehydrate._

## Current State
_updated: 2026-09-18 13:34 (M4 gateway closeout)_

- **Project**: hermes-agent · branch `main` · `bd9c88e` — fix(desktop): hide grouped tool summaries and inter-agent notices when tools section is hidden
- **Working tree**: clean
- **Preflight**: not run — skipped by the work order
- **Where to test**: Hermes Desktop app (native) — packaged bundle already swapped into /Users/m4/.hermes/hermes-agent/apps/desktop/release/mac-arm64/Hermes.app; open RCKT Bot's Bot Chat after the app's next natural relaunch — local native app on this machine, no login/password
- **Next step**: Live visual re-check inside the running Hermes Desktop app once it is next relaunched (not done here per the no-restart constraint) to confirm historical Bot Chat transcript renders clean after the swapped bundle takes effect.

### Mid-finished / blockers
- none
### Decisions (don't re-litigate)
- none yet

---

## Session log

### 2026-09-18 13:34 — M4 gateway job (completed)
- Extended the Desktop display.sections gating so hidden grouped tool-run summaries (Explored/Ran/Loaded skill) and the two dedicated inter-agent chrome paths (incoming "Message from X" card, outgoing "Replied to X" collapse) render no DOM when tools are hidden, while errors/dangling calls and the assistant's real reply text stay visible.
- Verified: New focused tests proven red on pre-fix code via git stash, green after fix (6/6). Full display-sections/tool/thread suites 106/106 pass. Full `vitest run`: 10307 passed, 3 pre-existing unrelated failures (electron ssh-updater + voice-prefs localStorage) confirmed identical on unmodified tree. tsc --noEmit and eslint clean. `npm run build` + `npm run builder -- --dir --publish never` succeeded.
- Pushed to `main`
### 2026-09-16 13:50 — M4 gateway job (completed)
- Desktop now honors per-profile display.show_reasoning / display.tool_progress / display.details_mode / display.sections.{thinking,tools,subagents,activity} by resolving them client-side (mirroring the TUI's existing domain/details.ts precedence) into a new $displaySections store, then gating the reasoning disclosure, ordinary tool-call rows, and the composer status stack's subagent roster and background-process rows so hidden sections render no DOM at all — live streaming and resumed transcript history alike — while clarify prompts, failed/dangling tool calls, approvals, the goal indicator, and the final reply stay visible.
- Verified: Reproduced the root cause: tui_gateway already streams every reasoning/tool-progress event to Desktop regardless of display config (only the CLI/TUI filtered client-side), confirmed against tui_gateway/agent_callbacks.py and server.py. Wrote 19 new focused invariant tests (display-sections.test.ts resolver precedence incl. the exact cali/link/scout/scribe/switch profile shape; message-parts-display-sections.test.tsx for hidden-live/hidden-settled reasoning, hidden ordinary tool rows vs. preserved error/clarify rows, and final text staying visible; display-sections.test.tsx for the composer status stack's subagent/background hiding) — all pass. Ran the full targeted sweep (src/components/assistant-ui, src/app/chat/composer/status-stack, src/app/session/hooks, src/store — 278 files / 3031 tests): only 2 pre-existing, unrelated voice-prefs.test.ts failures remain, confirmed identical on a clean checkout via git stash. `npm run typecheck` (all three tsconfigs) and `npm run build` both pass clean. `npm run pack` produced release/mac-arm64/Hermes.app successfully (unsigned/no notarization, as expected without Apple credentials in this environment). Copied the verified bundle into /Users/m4/.hermes/hermes-agent/apps/desktop/release/mac-arm64/Hermes.app via ditto + atomic swap; confirmed via `ps aux` that the running Hermes.app (PID 6380) and its hermes serve backend (PID 4811) are both still running untouched, unaware of the swap until their next restart.
- Pushed to `main`
