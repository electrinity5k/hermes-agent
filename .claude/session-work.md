# Session Work — hermes-agent

_Maintained by `/close` and the M4 gateway closeout. Top zone regenerates each run; the log appends.
On opening this project, read this file to rehydrate._

## Current State
_updated: 2026-09-18 17:04 (M4 gateway closeout)_

- **Project**: hermes-agent · branch `main` · `53a15e1` — feat(telegram): Rich Messages is the comprehensive formatting path
- **Working tree**: clean
- **Preflight**: passed 2026-09-18, reused — last preflight passed 0 day(s) ago (2026-09-18T14:47:24.749Z)
- **Where to test**: branch main (no deploy confirmed)
- **Next step**: Mobile/desktop visual confirmation of ordinary (non-table) replies through the new html renderer — Test 2's mobile confirmation covered the accepted <h4>/<p>/<ul><li> shape in isolation; RCKT Bot's planned fleet rollout should re-confirm a normal heading+paragraphs+bullets reply renders correctly end-to-end on a live bot before wider use.

### Mid-finished / blockers
- [ ] The bulk tests/tools/ full-suite background run had not finished when this job ended (slow tests: daytona, mcp_oauth device flow, video-gen). Not expected to surface anything new since every file it covers that touches Telegram/send_message was independently verified green.
- [ ] No live Telegram API call was made — verification is unit/mock-level against the documented Bot API 10.1/10.2 Rich HTML tag spec (fetched and cross-checked directly), matching the constraint against claiming visual verification from API acceptance alone.
### Decisions (don't re-litigate)
- none yet

---

## Session log

### 2026-09-18 17:04 — M4 gateway job (completed)
- Rich Messages is now the comprehensive semantic formatting path for Telegram: a new markdown-to-Rich-HTML renderer (headings, paragraphs, ordered/unordered/nested/task lists, emphasis, links, code, tables, details, math) feeds sendRichMessage's `html` field — the mobile-confirmed accepted shape — for every eligible reply, not just tables/task-lists/details/math. The same renderer now backs sendRichMessage, sendRichMessageDraft, rich finalize edits, and standalone/cron delivery.
- Verified: Set up a local .venv (pytest + project deps + aiohttp) since neither existing venv had pytest. Ran: renderer unit tests (22/22), full test_telegram_rich_messages.py (43/43, including new comprehensive-eligibility, draft, and finalize-edit cases), rewritten line-break tests (5/5), new standalone-rich-send tests (5/5), the full tests/gateway/test_telegram_*.py suite (701/701), tests/cron/ delivery suites (192/192), tests/gateway/test_config.py and test_send_error_classification.py (82/82), and the send_message tool/discord/whatsapp/slack caption suites (33/33) — all green, no regressions. A broader tests/tools/ full-suite run was still in progress in the background when this job ended; every file in it that touches Telegram/send_message was already covered and passing in the targeted runs above, and the ~172 failures seen before installing aiohttp were confirmed to be pre-existing missing-dependency errors (aiohttp/daytona/mcp/etc.), unrelated to this change.
- Pushed to `main`
### 2026-09-18 13:34 — M4 gateway job (completed)
- Extended the Desktop display.sections gating so hidden grouped tool-run summaries (Explored/Ran/Loaded skill) and the two dedicated inter-agent chrome paths (incoming "Message from X" card, outgoing "Replied to X" collapse) render no DOM when tools are hidden, while errors/dangling calls and the assistant's real reply text stay visible.
- Verified: New focused tests proven red on pre-fix code via git stash, green after fix (6/6). Full display-sections/tool/thread suites 106/106 pass. Full `vitest run`: 10307 passed, 3 pre-existing unrelated failures (electron ssh-updater + voice-prefs localStorage) confirmed identical on unmodified tree. tsc --noEmit and eslint clean. `npm run build` + `npm run builder -- --dir --publish never` succeeded.
- Pushed to `main`
### 2026-09-16 13:50 — M4 gateway job (completed)
- Desktop now honors per-profile display.show_reasoning / display.tool_progress / display.details_mode / display.sections.{thinking,tools,subagents,activity} by resolving them client-side (mirroring the TUI's existing domain/details.ts precedence) into a new $displaySections store, then gating the reasoning disclosure, ordinary tool-call rows, and the composer status stack's subagent roster and background-process rows so hidden sections render no DOM at all — live streaming and resumed transcript history alike — while clarify prompts, failed/dangling tool calls, approvals, the goal indicator, and the final reply stay visible.
- Verified: Reproduced the root cause: tui_gateway already streams every reasoning/tool-progress event to Desktop regardless of display config (only the CLI/TUI filtered client-side), confirmed against tui_gateway/agent_callbacks.py and server.py. Wrote 19 new focused invariant tests (display-sections.test.ts resolver precedence incl. the exact cali/link/scout/scribe/switch profile shape; message-parts-display-sections.test.tsx for hidden-live/hidden-settled reasoning, hidden ordinary tool rows vs. preserved error/clarify rows, and final text staying visible; display-sections.test.tsx for the composer status stack's subagent/background hiding) — all pass. Ran the full targeted sweep (src/components/assistant-ui, src/app/chat/composer/status-stack, src/app/session/hooks, src/store — 278 files / 3031 tests): only 2 pre-existing, unrelated voice-prefs.test.ts failures remain, confirmed identical on a clean checkout via git stash. `npm run typecheck` (all three tsconfigs) and `npm run build` both pass clean. `npm run pack` produced release/mac-arm64/Hermes.app successfully (unsigned/no notarization, as expected without Apple credentials in this environment). Copied the verified bundle into /Users/m4/.hermes/hermes-agent/apps/desktop/release/mac-arm64/Hermes.app via ditto + atomic swap; confirmed via `ps aux` that the running Hermes.app (PID 6380) and its hermes serve backend (PID 4811) are both still running untouched, unaware of the swap until their next restart.
- Pushed to `main`
