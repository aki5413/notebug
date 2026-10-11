# Contributing / 기여 / 貢献

- **Bugs and ideas** — open an [issue](https://github.com/aki5413/notebug/issues).
  Please include the code you ran in `%%notebug` and a screenshot if possible.
  (한국어·日本語 OK)
- **Code** — fork, make a branch, and open a pull request. Run the tests first:

  ```bash
  pip install -e ".[test]"
  python -m pytest tests
  ```

- **UI text** lives in `src/notebug/assets/i18n.js` and colours in `src/notebug/assets/ui.css`;
  adding a language only needs a new block in `i18n.js`.
