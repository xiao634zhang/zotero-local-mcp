# Zotero Local MCP

A small, dependency-free MCP plugin for importing verified paper metadata and official PDFs into a local [Zotero](https://www.zotero.org/) Desktop library.

## Features

- Check Zotero Local API and Connector readiness.
- Search top-level library items.
- Prevent exact-title duplicates.
- Import a paper and its PDF in one Zotero Connector session.
- Verify the resulting PDF attachment.
- Never modify `zotero.sqlite` directly.

## Requirements

- Zotero Desktop with **Settings → Advanced → Allow other applications on this computer to communicate with Zotero** enabled.
- Python 3.9 or later available as `python`.
- Codex or another MCP client that supports bundled stdio servers.

The default Zotero endpoint is `http://127.0.0.1:23119`. Override it with the `ZOTERO_LOCAL_BASE` environment variable when needed.

## Install in Codex

Add the repository as a plugin marketplace:

```shell
codex plugin marketplace add xiao634zhang/zotero-local-mcp
```

Restart the ChatGPT desktop app, open **Plugins**, select the repository marketplace, and install **Zotero Local MCP**. Start a new task after installation so the MCP tools are discovered.

Example prompt:

> Add these papers to Zotero with their official PDFs.

## Tools

- `zotero_status`
- `zotero_search`
- `zotero_list_attachments`
- `zotero_import_with_pdf`

## Important limitation

Zotero Connector can attach a PDF automatically only to an item created in the same save session. If a matching older item exists without a PDF, this plugin refuses to create a duplicate and reports that a one-time manual attachment is required.

## Privacy and security

- Library metadata is read from the local Zotero API.
- Writes go only through Zotero's Connector API.
- PDF files are downloaded from the URL supplied to the import tool.
- No telemetry, cloud service, API key, or direct SQLite access is included.
- Review PDF URLs before approving imports.

## Development

Run the standard-library test suite:

```shell
python -m unittest discover -s tests -v
```

The MCP server communicates over newline-delimited JSON-RPC on standard input/output.

## License

MIT. See [LICENSE](LICENSE).

This independent project is not affiliated with or endorsed by Zotero or OpenAI. Zotero is a trademark of the Corporation for Digital Scholarship.
