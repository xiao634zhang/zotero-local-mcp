import importlib.util
import json
from pathlib import Path
import unittest


SERVER = (
    Path(__file__).parents[1]
    / "plugins"
    / "zotero-local-mcp"
    / "scripts"
    / "zotero_mcp_server.py"
)
SPEC = importlib.util.spec_from_file_location("zotero_mcp_server", SERVER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ServerTests(unittest.TestCase):
    def test_tools_are_exposed(self):
        response = MODULE.respond({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "zotero_status",
                "zotero_search",
                "zotero_list_attachments",
                "zotero_import_with_pdf",
            },
        )

    def test_normalize_item(self):
        item = MODULE.normalize_item(
            {
                "data": {
                    "key": "ABCD1234",
                    "itemType": "journalArticle",
                    "title": "Example",
                    "date": "2026-08-10",
                    "creators": [{"firstName": "Ada", "lastName": "Lovelace"}],
                }
            }
        )
        self.assertEqual(item["key"], "ABCD1234")
        self.assertEqual(item["year"], "2026")
        self.assertEqual(item["creators"], ["Ada Lovelace"])

    def test_initialize_is_valid_json_rpc(self):
        response = MODULE.respond({"jsonrpc": "2.0", "id": 7, "method": "initialize"})
        json.dumps(response)
        self.assertEqual(response["id"], 7)
        self.assertEqual(response["result"]["serverInfo"]["name"], "zotero-local-mcp")


if __name__ == "__main__":
    unittest.main()
