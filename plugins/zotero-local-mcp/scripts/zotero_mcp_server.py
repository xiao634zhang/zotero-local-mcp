#!/usr/bin/env python3
"""Dependency-free MCP server for Zotero Desktop's Local API and Connector."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("ZOTERO_LOCAL_BASE", "http://127.0.0.1:23119").rstrip("/")
API = f"{BASE}/api/users/0"
MAX_PDF_BYTES = 250 * 1024 * 1024


def http(method: str, url: str, body=None, headers=None, timeout=120):
    data = None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return {"status": response.status}
            text = raw.decode("utf-8", errors="replace")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"status": response.status, "text": text}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach Zotero at {BASE}: {exc.reason}") from exc


def http_bytes(method: str, url: str, data=None, headers=None, timeout=240):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_PDF_BYTES + 1)
            if len(raw) > MAX_PDF_BYTES:
                raise RuntimeError(f"Response from {url} exceeds 250 MiB")
            return response.status, raw, dict(response.headers)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach {url}: {exc.reason}") from exc


def download_pdf(url: str):
    _status, raw, response_headers = http_bytes(
        "GET",
        url,
        headers={"Accept": "application/pdf", "User-Agent": "Zotero-Local-MCP/0.1"},
    )
    if not raw.startswith(b"%PDF-"):
        content_type = response_headers.get("Content-Type", "unknown")
        raise RuntimeError(f"PDF URL returned non-PDF content ({content_type})")
    return raw


def api_get(path: str):
    return http("GET", f"{API}{path}", headers={"Zotero-API-Version": "3"})


def normalize_item(obj):
    data = obj.get("data", obj)
    creators = []
    for creator in data.get("creators", []):
        name = creator.get("name") or " ".join(
            value for value in [creator.get("firstName"), creator.get("lastName")] if value
        )
        if name:
            creators.append(name)
    return {
        "key": data.get("key") or obj.get("key"),
        "itemType": data.get("itemType"),
        "title": data.get("title"),
        "creators": creators,
        "year": (data.get("date") or "")[:4],
        "doi": data.get("DOI"),
        "url": data.get("url"),
        "parentItem": data.get("parentItem"),
        "contentType": data.get("contentType"),
        "filename": data.get("filename"),
    }


def search_library(query: str):
    encoded = urllib.parse.urlencode(
        {"q": query, "qmode": "titleCreatorYear", "itemType": "-attachment"}
    )
    return [normalize_item(item) for item in api_get(f"/items/top?{encoded}")]


def list_attachments(parent_key: str):
    items = api_get(f"/items/{urllib.parse.quote(parent_key)}/children")
    normalized = [normalize_item(item) for item in items]
    return [item for item in normalized if item.get("itemType") == "attachment"]


def tool_status(_args):
    root = http("GET", f"{BASE}/api/")
    connector = http("GET", f"{BASE}/connector/ping")
    return {
        "api": "ok",
        "connector": "ok",
        "zotero": root,
        "connector_response": connector,
    }


def tool_search(args):
    return {"items": search_library(args["query"])}


def tool_list_attachments(args):
    return {
        "parent_key": args["parent_key"],
        "attachments": list_attachments(args["parent_key"]),
    }


def to_creator(creator):
    return {
        "creatorType": creator.get("creator_type", "author"),
        "firstName": creator.get("first_name", ""),
        "lastName": creator["last_name"],
    }


def tool_import_with_pdf(args):
    matches = search_library(args["title"])
    exact = [
        item
        for item in matches
        if (item.get("title") or "").casefold() == args["title"].casefold()
    ]
    if exact:
        parent = exact[0]
        attachments = list_attachments(parent["key"])
        pdfs = [item for item in attachments if item.get("contentType") == "application/pdf"]
        if pdfs:
            return {
                "status": "skipped",
                "reason": "Exact item and PDF already exist",
                "item": parent,
                "attachments": pdfs,
            }
        return {
            "status": "existing-without-pdf",
            "reason": "Zotero Connector cannot attach a file to an item created outside its current save session.",
            "item": parent,
            "requires_manual_attachment": True,
        }

    pdf = download_pdf(args["pdf_url"])
    item_type = args.get("item_type", "journalArticle")
    item = {
        "id": f"mcp-{uuid.uuid4().hex}",
        "itemType": item_type,
        "title": args["title"],
        "creators": [to_creator(creator) for creator in args["creators"]],
        "date": str(args["year"]),
        "url": args.get("url", ""),
        "DOI": args.get("doi", ""),
        "tags": [{"tag": tag} for tag in args.get("tags", [])],
    }
    venue = args.get("publication_title", "")
    if item_type == "conferencePaper":
        item["proceedingsTitle"] = venue
    else:
        item["publicationTitle"] = venue

    session_id = f"zotero-local-mcp-{uuid.uuid4().hex}"
    payload = {
        "items": [item],
        "uri": args.get("url") or args["pdf_url"],
        "sessionID": session_id,
    }
    connector_headers = {"X-Zotero-Connector-API-Version": "3"}
    http("POST", f"{BASE}/connector/saveItems", payload, connector_headers, timeout=240)

    metadata = json.dumps(
        {
            "sessionID": session_id,
            "parentItemID": item["id"],
            "title": args.get("pdf_title") or "Full Text PDF",
            "url": args["pdf_url"],
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    http_bytes(
        "POST",
        f"{BASE}/connector/saveAttachment",
        data=pdf,
        headers={
            "Content-Type": "application/pdf",
            "Content-Length": str(len(pdf)),
            "X-Metadata": metadata,
            **connector_headers,
        },
    )

    for _ in range(20):
        time.sleep(0.5)
        found = search_library(args["title"])
        exact = [
            candidate
            for candidate in found
            if (candidate.get("title") or "").casefold() == args["title"].casefold()
        ]
        if exact:
            parent = exact[0]
            attachments = list_attachments(parent["key"])
            if any(item.get("contentType") == "application/pdf" for item in attachments):
                return {"status": "created", "item": parent, "attachments": attachments}
    return {"status": "created-pending-attachment", "items": search_library(args["title"])}


TOOLS = {
    "zotero_status": (
        {"type": "object", "properties": {}},
        tool_status,
        "Check Zotero Local API and Connector readiness.",
    ),
    "zotero_search": (
        {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        tool_search,
        "Search top-level Zotero items by title, creator, or year.",
    ),
    "zotero_list_attachments": (
        {
            "type": "object",
            "properties": {"parent_key": {"type": "string"}},
            "required": ["parent_key"],
        },
        tool_list_attachments,
        "List child attachments for a Zotero item.",
    ),
    "zotero_import_with_pdf": (
        {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "creators": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "creator_type": {"type": "string"},
                        },
                        "required": ["last_name"],
                    },
                },
                "year": {"type": ["string", "integer"]},
                "item_type": {
                    "type": "string",
                    "enum": ["journalArticle", "conferencePaper", "preprint"],
                },
                "publication_title": {"type": "string"},
                "doi": {"type": "string"},
                "url": {"type": "string"},
                "pdf_url": {"type": "string"},
                "pdf_title": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "creators", "year", "pdf_url"],
        },
        tool_import_with_pdf,
        "Import a new paper and upload its PDF in the same official Zotero Connector session, with duplicate checks.",
    ),
}


def respond(message):
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "zotero-local-mcp", "version": "0.1.0"},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        tools = [
            {"name": name, "description": description, "inputSchema": schema}
            for name, (schema, _function, description) in TOOLS.items()
        ]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
    if method == "tools/call":
        params = message.get("params", {})
        name = params.get("name")
        if name not in TOOLS:
            raise ValueError(f"Unknown tool: {name}")
        result = TOOLS[name][1](params.get("arguments") or {})
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": text}],
                "structuredContent": result,
            },
        }
    if method and method.startswith("notifications/"):
        return None
    if request_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return None


def main():
    for raw in sys.stdin:
        try:
            message = json.loads(raw)
            output = respond(message)
            if output is not None:
                sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            request_id = (
                locals().get("message", {}).get("id")
                if isinstance(locals().get("message"), dict)
                else None
            )
            error = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(exc)},
            }
            sys.stdout.write(json.dumps(error, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
