# TUI

The TUI is the "AiPC-style" interface: a calm terminal UI built with `rich`, one `Live`
frame in the alternate screen buffer, redrawn on key press. The CLI is the non-interactive
parity layer; where a screen is still read-only, it says so below.

## Rendering rules

* **One frame, no flicker.** A single `rich.Live` frame is redrawn on key press. The
  terminal is restored on exit **and on crash** (try/finally). No leftover lines.
* **No background refresh today.** Screens are rebuilt from the ledger on every key press;
  there is no timer, no spinner and no partial repaint. `--no-anim` is accepted for forward
  compatibility but is a no-op.
* **Header card.** A rounded card with the pixel logo (block characters, green gradient),
  the slogan and a status line: armed state, mode, agent, project and the last verdict.
  Status dots are always paired with text (accessibility).
* **Frameless numbered list.** Inline dim descriptions and the `❯` marker on the selection.
  There are **no group separators and no danger items** yet (see gaps below).
* **One dim footer** with localized key hints.
* **Narrow windows (< ~80 cols)** hide the menu descriptions. There is no separate
  compact layout, and the 60-column minimum is a recommendation, not enforced.
* **Themes:** `green` (default), `mono`, `amber`. `NO_COLOR` and dumb terminals are
  respected; `--ascii` (or auto-detection on non-UTF-8 Windows) switches the logo/banner,
  selection marker, status glyphs, help overlay and table borders to ASCII equivalents.
* **Non-TTY runs** print the menu once instead of entering the alternate screen.

## Controls

| key | action |
| --- | --- |
| `W`/`S`, `↑`/`↓` | move |
| `Home`/`End` | jump |
| `Enter` | open the selected menu item |
| digits `1`–`9` | quick-select |
| `Esc`/`Backspace` | back |
| `Q` | quit |
| `L` | cycle language (wraps) |
| `T` | cycle theme |
| `?` | help overlay |
| `R` | redraw (the frame is rebuilt on every key, so this is effectively a no-op) |
| `/` | **not implemented** — reserved for list filtering |

**Layout independence:** non-Latin keyboards work by *physical key position*. `W/S/Q/L/T`
map to the same actions even when the layout produces Cyrillic characters (`ц/ы/й/д/е`).
The map lives in `src/aiproof/tui/keys.py`; `aiproof keys` prints what the terminal
receives, as a keyboard test. Multi-byte UTF-8 keys are read completely (not one byte).

Mouse is optional and off by default (**not implemented**).

## Screens — implemented today

Each screen is a module under `src/aiproof/tui/screens/`, registered in `RENDERERS`. All
strings go through i18n.

| # | screen | shows today |
| --- | --- | --- |
| 1 | Dashboard | armed state, mode, pinned-config status, ledger chain status, detected agents, session count, data dir |
| 2 | Live feed | the last 30 ledger events with verdict colors; dangerous events in red |
| 3 | Sessions | index, session id and event count (last 50) |
| 4 | Session detail | Markdown receipt for the **latest** session |
| 5 | Checks | the check list with on/off glyphs and the strictness value (read-only) |
| 6 | Secrets | one diff scan showing type + location + fingerprint (read-only) |
| 7 | Rules & Corrections | recorded corrections and compiled rules with enable state/severity (read-only) |
| 8 | Settings | language, available languages, theme, strictness, error policy, test command, agent message language (read-only) |
| 9 | Doctor | the same probes as `aiproof doctor`, each with a ✓/!/✗ mark and a hint |
| 10 | Logs | the last 40 lines of `aiproof.log` (no level filter) |
| 11 | Check updates | static hint; the network is only used by `aiproof update --check` |
| 12 | About | logo, `AiProof <version> by SYSIK`, tagline, license |

## Known gaps (not implemented in the TUI)

These exist in the CLI (`status`, `sessions`, `show`, `checks`, `scan`, `learn`, `setup`,
`doctor`, `logs`, `update`, `lang`, `theme`) but not as interactive TUI actions:

* Dashboard: last-5-sessions table, claim/secret/tamper counters, one-line health summary.
* Sessions: date/agent/duration/verdict columns and `Enter` → detail for the selected
  session (the detail screen always opens the latest session).
* Toggling checks or strictness; pinned keys would require the human-confirmation flow.
* Secrets actions (allowlist, redact-in-place with backup).
* Rules: enable/disable, backtest stats, export to `AGENTS.md`.
* Settings editing, protected-path editing, agent connect/disconnect, update channel.
* Doctor "run self-test" action.
* Log level filters.
* Update download/replace (same as the CLI: not implemented anywhere yet).
* `/` filtering and mouse support. `R` only triggers the normal key-press redraw.

Writes that exist in the CLI remain protected there: `pause`, `resume`, `pin`, `checks`
(write), `learn enable|disable` and `off` require an interactive TTY.
`AIPROOF_NON_INTERACTIVE=1` or `CI` set refuses them, so an agent cannot call them
successfully (see `docs/THREAT_MODEL.md`).

## Testing

`tests/test_tui.py` covers themes, layout-independent keys (including Cyrillic positions),
multi-byte key reads, escape-sequence decoding, ASCII fallback (symbols, marker and table
borders), the logo/banner and screen rendering smoke tests.