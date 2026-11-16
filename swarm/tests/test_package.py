import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_portable_manifest_and_compatibility_overlay_agree(self):
        portable = json.loads((ROOT / 'plugin.json').read_text())
        legacy = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())
        self.assertEqual(portable['$schema'],
                         'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json')
        for key in ('name', 'version', 'description'):
            self.assertEqual(portable[key], legacy[key])
        interface = portable['extensions']['com.openai']['interface']
        self.assertEqual(interface, legacy['interface'])
        self.assertLessEqual(len(interface['shortDescription']), 30)
        self.assertEqual(interface['category'], 'Developer Tools')
        self.assertTrue((ROOT / legacy['skills']).is_dir())
        self.assertRegex(portable['version'], r'^\d+\.\d+\.\d+$')

    def test_skill_supporting_links_are_contained_and_exist(self):
        skills = sorted((ROOT / 'skills').glob('*/SKILL.md'))
        self.assertEqual(len(skills), 2)
        for skill in skills:
            text = skill.read_text()
            self.assertTrue(text.startswith('---\n'))
            self.assertIn('name: ' + skill.parent.name + '\n', text)
            self.assertLess(skill.stat().st_size, 1024 * 1024)
            for target in re.findall(r'\]\(([^)]+)\)', text):
                resolved = (skill.parent / target).resolve()
                self.assertTrue(resolved.is_relative_to(ROOT))
                self.assertTrue(resolved.is_file(), str(resolved))


if __name__ == '__main__':
    unittest.main()
