# TUI

The TUI is the "AiPC-style" interface: a calm terminal UI built with `rich`, one `Live`
frame in the alternate screen buffer, redrawn only on events.

## Rendering rules

* **One frame, no flicker.** A single `rich.Live` frame is redrawn on key press, resize,
  refresh timer or background event. The terminal is restored on exit **and on crash**
  (try/finally). No leftover lines.
* **Header card.** A rounded card with the pixel logo (block characters, green gradient),
  the slogan and a status line:
  `mode: enforce   agent: claude-code ✓   project: <name>   lang: EN   last session: ✓ verified`.
  Status dot colors: green armed, amber degraded/warn-only, red tampered/paused, grey off.
  Colour is never the only signal — a symbol/text always accompanies it (accessibility).
* **Frameless numbered list.** Inline dim descriptions, blank-line group separators, the
  `❯` marker on the selection. Danger items (uninstall, pause, redact-in-place) turn red
  when selected. No fills anywhere.
* **One dim footer** with localized key hints.
* **Narrow windows (< ~80 cols)** automatically hide descriptions. The minimum supported
  width is 60 columns; below that the layout is a compact single column.
* **Themes:** `green` (default), `mono`, `amber`. `NO_COLOR` and dumb terminals are
  respected; `--ascii` (or auto-detection) switches to box-drawing-free/emoji-free output.
  CJK and combining-character width is handled via `wcwidth`.
* **Animation** is cheap and opt-in; disabled by `--no-anim` and in non-TTY mode.

## Controls

| key | action |
| --- | --- |
| `W`/`S`, `↑`/`↓` | move |
| `Home`/`End` | jump |
| `Enter` | open |
| digits `1`–`9` | quick-select |
| `Esc`/`Backspace` | back |
| `Q` | quit |
| `L` | cycle language (wraps) |
| `T` | cycle theme |
| `?` | help overlay |
| `/` | filter long lists |
| `R` | refresh |

**Layout independence:** non-Latin keyboards work by *physical key position*. `←W/S/Q/L/T`
map to the same actions even when the layout produces Cyrillic characters
(`ц/ы/й/д/е`). The map lives in `src/aiproof/tui/keys.py`; `aiproof keys` prints what the
terminal receives, as a keyboard test.

Mouse is optional and off by default.

## Screens

Each screen is a module under `src/aiproof/tui/screens/`, registered in `RENDERERS`. All
strings go through i18n.

1. **Dashboard / Status** — armed state, mode, pinned-config integrity, ledger chain
   status, detected agents + support level, last 5 sessions with verdict icons, counts
   (claims verified / false claims caught / secrets blocked / tamper attempts), and a
   one-line health summary.
2. **Live feed** (`aiproof watch`) — the most recent ledger events with verdict colors,
   bounded ring buffer (last 30), dangerous events highlighted red.
3. **Sessions** — date, agent, duration, verdict, claims count, findings; `Enter` opens
   detail.
4. **Session detail (the receipt)** — claims-vs-evidence table, tamper/secret findings,
   chain head hash, export actions (JSON/HTML/MD, badge snippet).
5. **Checks** — toggle each check, set strictness; changes to pinned keys trigger the
   human-confirmation flow.
6. **Secrets** — run a scan (diff / agent histories / instruction files); findings as
   type + location + fingerprint; add to allowlist; redact with backup after confirmation.
7. **Rules & Corrections** (Phase 2) — corrections and compiled rules with enable state,
   backtest action, and export to the `AGENTS.md` block. See `docs/LEARN.md`.
8. **Settings** — language, theme, strictness, test command override, protected paths,
   agents (connect/disconnect with dry-run preview), update channel, error policy.
9. **Doctor** — install integrity, PATH, hook installation, pin integrity, ledger chain,
   version, dependency versions, terminal capabilities; each line has ✓/!/✗ and a fix
   hint, plus a "run self-test" action that simulates a false "all tests pass" stop.
10. **Logs** — last N lines of `aiproof.log` (separate from the ledger), level filters.
11. **Check updates** — compares GitHub releases, shows the changelog, downloads only after
    an explicit Yes and a SHA-256 check.
12. **About** — logo, `AiProof <version> by SYSIK`, license, links.

Default menu order: Dashboard, Live feed, Sessions, Checks, Secrets, Rules & Corrections,
Settings, Doctor, Logs, Check updates, About, Exit — groups separated by blank lines.

## Non-interactive parity

Every TUI action exists as a plain command, all supporting `--json` where it makes sense and
exit codes suitable for CI:

```
aiproof status | watch | sessions | show <id> | checks | scan | learn | setup
        | doctor | logs | update | about | lang <code> | theme <name>
```

## Testing

`tests/test_tui.py` covers themes, layout-independent keys (including Cyrillic positions),
escape-sequence decoding, ASCII fallback, the logo/banner and screen rendering smoke tests.
Render snapshots use `rich`'s recording console. Known gaps: `/` filter and mouse handling
are stubbed; document them rather than claim them.

## Human-only actions

`pause`, `resume`, `pin`, `checks` (write), `learn enable|disable` and `off` require an
interactive TTY. `AIPROOF_NON_INTERACTIVE=1` or `CI` set refuses them, so an agent cannot
call them successfully (see `docs/THREAT_MODEL.md`).
