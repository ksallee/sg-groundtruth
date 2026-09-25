"""python -m unittest experiments/retrieval/test_score.py

The scorer read no Search door after #84 split the family per call, and no endpoint door at all on
its first run against #56's generated doors. Both times recall read as falling while the corpus
had lost nothing, so a call the tasks name must resolve to a door that holds it.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402


def rules_door(text):
    return {"kind": "rules", "text": text, "members": set()}


class DoorName(unittest.TestCase):
    def test_a_door_is_found_by_the_call_its_heading_names(self):
        doors = {"endpoints-anything": rules_door("# `POST /entity/<type>/_search`\n\n- rule\n")}
        self.assertEqual(score.door_name("POST /entity/<type>/_search", doors),
                         "endpoints-anything")

    def test_a_call_inside_a_family_door(self):
        doors = {"endpoints-records-get": rules_door(
            "# Endpoints — Records, GET\n\n## `GET /entity/<type>`\n\n## `GET /entity/<type>/<id>`\n")}
        self.assertEqual(score.door_name("GET /entity/<type>/<id>", doors), "endpoints-records-get")

    def test_a_call_named_only_in_a_rule_is_not_its_door(self):
        doors = {"endpoints-a": rules_door("# `GET /x`\n\n- see `POST /y`\n"),
                 "endpoints-b": rules_door("# `POST /y`\n")}
        self.assertEqual(score.door_name("POST /y", doors), "endpoints-b")

    def test_the_built_form_by_its_blocks(self):
        doors = {"endpoints-Search": {"kind": "endpoints", "header": "",
                                      "blocks": [{"call": "POST /entity/<type>/_search"}]}}
        self.assertEqual(score.door_name("POST /entity/<type>/_search", doors), "endpoints-Search")

    def test_no_door_holds_the_call(self):
        self.assertIsNone(score.door_name("GET /nowhere", {"endpoints-a": rules_door("# `GET /x`\n")}))

    def test_every_call_a_task_names_has_a_door_on_disk(self):
        entries = score.load_entries()
        doors, _, _ = score.read_doors(entries)
        tasks = json.loads((score.HERE / "tasks.json").read_text())
        calls = {c for t in tasks for c in t["plan"]["calls"]}
        cards = {e["endpoint"] for e in entries.values() if e["group"] == "endpoint"}
        missing = sorted(c for c in calls & cards if score.door_name(c, doors) is None)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
