import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('policy',Path(__file__).resolve().parents[1]/'scripts/version_policy.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
class SemanticVersionPolicyTests(unittest.TestCase):
    def test_minor_changes_reset_patch(self):
        for category in ('added','removed'):
            self.assertEqual(policy.next_version('1.8.4',{'id':'one','category':category}),'1.9.0')
    def test_patch_changes(self):
        for category in ('improved','other'):
            self.assertEqual(policy.next_version('1.8.4',{'id':'one','category':category}),'1.8.5')
    def test_major_requires_architecture(self):
        change={'id':'one','category':'added','majorArchitectureChange':True}
        with self.assertRaises(ValueError):policy.next_version('1.8.4',change)
        change['architectureRationale']='Move sessions to independently hosted processes.'
        self.assertEqual(policy.next_version('1.8.4',change),'2.0.0')
        change['category']='improved'
        with self.assertRaises(ValueError):policy.next_version('1.8.4',change)
    def test_reject_multiple_changes(self):
        for change in ([{'id':'a'},{'id':'b'}],{'id':['a','b'],'category':'added'},{'id':'a','category':'feature'}):
            with self.assertRaises(ValueError):policy.next_version('1.0.0',change)
    def test_trilingual_order(self):
        record={'titles':{l:'Title' for l in policy.LANGUAGES},'noteCategories':['added','other'],'notes':{l:[f'[{policy.CATEGORIES[c][i]}] Description.' for c in ('added','other')] for i,l in enumerate(policy.LANGUAGES)}}
        policy.validate_notes(record)
        record['notes']['en'].reverse()
        with self.assertRaises(ValueError):policy.validate_notes(record)
    def test_version_format(self):
        for value in ('v1.0.0','1.0','01.0.0','1.0.0-beta',None):
            with self.assertRaises(ValueError):policy.version_tuple(value)
if __name__=='__main__':unittest.main()
