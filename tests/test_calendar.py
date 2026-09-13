import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.generate_calendar import generate


class CalendarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ics = generate()
        cls.source = json.loads((ROOT / "data/physics_olympiads.json").read_text(encoding="utf-8"))

    def test_rfc5545_shape_and_utf8(self):
        self.assertTrue(self.ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(self.ics.endswith("END:VCALENDAR\r\n"))
        self.assertNotIn("\n", self.ics.replace("\r\n", ""))
        self.assertIn("X-WR-CALNAME:Физические олимпиады", self.ics)
        self.assertNotRegex(self.ics, r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
        self.assertTrue(all(len(line.encode("utf-8")) <= 75 for line in self.ics.split("\r\n") if line))

    def test_event_count_matches_dated_source_records(self):
        expected = sum(len(item["events"]) for item in self.source["olympiads"])
        self.assertEqual(expected, 22)
        self.assertEqual(self.ics.count("BEGIN:VEVENT"), expected)
        self.assertEqual(self.ics.count("END:VEVENT"), expected)

    def test_uids_are_stable_and_unique(self):
        first = generate()
        second = generate()
        uids = re.findall(r"^UID:(.+)$", first, re.MULTILINE)
        self.assertEqual(first, second)
        self.assertEqual(len(uids), len(set(uids)))

    def test_known_dates(self):
        for day in ("20260916", "20260924", "20261002", "20261005", "20261014", "20261015", "20261021", "20261022", "20261004", "20261025", "20261108", "20261115", "20270314", "20261116", "20261229", "20270207"):
            self.assertIn(day, self.ics)

    def test_summary_and_description_format(self):
        unfolded = self.ics.replace("\r\n ", "")
        self.assertIn("SUMMARY:Олимпиада школьников «Физтех» | I тур", unfolded)
        self.assertIn("SUMMARY:ВСОШ ШЭ | Труд (Техника\\, технологии и техническое творчество)", unfolded)
        self.assertIn("DESCRIPTION:Уровень: I\\nКлассы: 9-11\\nСайт: https://olymp-online.mipt.ru/", unfolded)
        self.assertIn("SUMMARY:Национальная олимпиада по анализу данных DANO | Отборочный этап", unfolded)
        self.assertNotIn("Профили Высшей пробы", self.ics)
        self.assertNotIn("SUMMARY:Олимпиада школьников «Физтех» —", self.ics)

    def test_vysshaya_proba_profiles_have_no_events(self):
        vysshaya_proba = next(item for item in self.source["olympiads"] if item["id"] == "vysshaya-proba")
        self.assertEqual(vysshaya_proba["events"], [])
        self.assertIn("Журналистика (11 класс)", vysshaya_proba["description"])


if __name__ == "__main__":
    unittest.main()
