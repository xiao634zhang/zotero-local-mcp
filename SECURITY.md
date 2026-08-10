# Security policy

## Supported versions

Security fixes are applied to the latest release.

## Reporting a vulnerability

Please use GitHub's private security advisory feature for this repository. Do not include private Zotero library data, API credentials, or copyrighted PDFs in a report.

## Security model

This plugin is local-first. It connects to Zotero on loopback by default and downloads PDFs from user-approved URLs. It does not include authentication because Zotero's Local API is intended for applications running on the same computer. Do not expose port `23119` directly to the public internet.
