# Contributing

Issues and pull requests are welcome.

1. Keep the server dependency-free unless a dependency is clearly justified.
2. Do not add direct reads or writes to `zotero.sqlite`.
3. Add or update tests for behavior changes.
4. Run `python -m unittest discover -s tests -v` before opening a pull request.
5. Never commit Zotero profiles, library exports, PDFs, tokens, or personal paths.
