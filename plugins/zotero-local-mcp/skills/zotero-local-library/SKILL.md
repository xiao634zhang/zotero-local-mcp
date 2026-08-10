---
name: zotero-local-library
description: Operate Zotero Desktop through the Zotero Local MCP. Use when the user asks to search Zotero, add papers, import DOI or arXiv records, prevent duplicates, include official PDFs, or check PDF attachments.
---

# Zotero Local Library

Use the `zotero-local` MCP tools. Never manipulate Zotero's SQLite database.

## Workflow

1. Call `zotero_status` before writes.
2. Resolve the exact paper from an official publisher, DOI, or arXiv page.
3. Call `zotero_search` with the full title to check for duplicates.
4. For a new paper, call `zotero_import_with_pdf` with complete, verified metadata and the official direct PDF URL.
5. If an exact item already exists without a PDF, do not create a duplicate. Explain that Zotero Connector cannot attach a file to an item created outside its current save session.
6. Call `zotero_list_attachments` to verify that Zotero stored the PDF.

Treat imports as writes. Proceed without another question when the user explicitly asked to add the named records. Never invent authors, DOI, venue, year, or PDF URLs.

Report the Zotero item key and attachment key. Explain that a Zotero item key is different from a BibTeX citation key when both appear.
