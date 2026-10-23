import json
from pathlib import Path
import tempfile
import unittest

from scinet.evidence import seal, verify, validate_review, digest

class EvidenceTests(unittest.TestCase):
    def test_modified_evidence_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p / 'data.txt').write_text('original')
            seal(p); self.assertEqual(verify(p), [])
            (p / 'data.txt').write_text('changed')
            self.assertTrue(any('data.txt' in e for e in verify(p)))

    def test_deleted_file_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p / 'data.txt').write_text('original'); seal(p)
            (p / 'data.txt').unlink()
            self.assertTrue(verify(p))

    def test_missing_evidence_reference_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as d:
            review = {'summary': 'x', 'findings': [{'id': 'F1', 'claim_id': 'C1', 'status': 'qualified', 'title': 'x', 'explanation': 'x', 'evidence': [{'path': 'missing.txt', 'locator': 'p3'}]}], 'limitations': ['x']}
            with self.assertRaises(ValueError): validate_review(review, Path(d), {})

    def test_review_must_match_current_input_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'paper.txt').write_text('v1'); old=digest(p/'paper.txt')
            (p/'paper.txt').write_text('v2')
            review={'summary':'x','findings':[{'id':'F1','claim_id':'C1','status':'supported','title':'x','explanation':'x','evidence':[{'path':'paper.txt','locator':'p3'}]}], 'limitations':['x']}
            with self.assertRaises(ValueError): validate_review(review,p,{'paper.txt':old})

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            review={'summary':'x','findings':[{'id':'F1','claim_id':'C1','status':'supported','title':'x','explanation':'x','evidence':[{'path':'../outside.txt','locator':'p3'}]}], 'limitations':['x']}
            with self.assertRaises(ValueError): validate_review(review,Path(d),{'../outside.txt':'fake'})

    def test_ai_must_address_all_four_claims(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p/'paper.txt').write_text('evidence')
            review = {'summary':'x', 'limitations':['x'], 'findings':[
                {'id':'F1','claim_id':'C1','status':'supported','title':'x','explanation':'x',
                 'evidence':[{'path':'paper.txt','locator':'p3'}]}]}
            with self.assertRaises(ValueError):
                validate_review(review,p,{'paper.txt':digest(p/'paper.txt')})

if __name__ == '__main__': unittest.main()
