# Changelog

## 0.5.0 — 2026-10-11
- **Renamed from BugCatcher to NoteBug** (package `notebug`, cell magic `%%notebug`),
  because the name "BugCatcher" is already used by other software. Functionality is unchanged.
- First public release on GitHub, with tests on Python 3.10–3.13, citation metadata and a demo notebook.

## 0.4.0 — 2026-09-30
- numpy / pandas / matplotlib support: DataFrame table preview, shape and dtype labels,
  change highlighting for arrays and frames, plots shown in the output panel and from the console.
- Functions called back by libraries (`DataFrame.apply`, `np.vectorize`, …) run as a single step.
- Notebook-like behaviour: the value of the last line and `display(...)` appear in the output panel;
  `%magics` and `!shell` lines are accepted in `%%notebug` cells.
- Long programs: recording stops at `max_steps` but the program runs to the end.

## 0.3.0
- Multi-line console (`for`, `if`, …) with auto-indent, history and IME-safe Enter.
- Themes (night, light, darcula, high contrast), adjustable font size, per-colour overrides.

## 0.2.0
- Packaged as an importable module (`notebug.run`, `run_file`, `save_html`, `config`) and a CLI.
- Removed the level/XP system; achievements can be switched off.

## 0.1.x
- First classroom version for Google Colab: breakpoints, stepping, time travel, variables,
  call stack, console, pets, power mode, sound. Fixes for Colab's output sandbox.
