import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from directory_claim import DirectoryClaim,expired_job


def compete(path,barrier,results):
    barrier.wait()
    claim=DirectoryClaim(path)
    results.put(claim.acquire())
    # Retain the directory until every contender has attempted mkdir.
    barrier.wait()
    if claim.owned:claim.release()


class ClaimTests(unittest.TestCase):
    def test_nine_contenders_one_winner(self):
        with tempfile.TemporaryDirectory() as d:
            context=multiprocessing.get_context('fork')
            barrier=context.Barrier(9);results=context.Queue()
            children=[context.Process(target=compete,args=(str(Path(d)/'claim'),barrier,results)) for _ in range(9)]
            for child in children:child.start()
            values=[results.get(timeout=10) for _ in children]
            for child in children:child.join(timeout=10);self.assertEqual(child.exitcode,0)
            self.assertEqual(sum(values),1)

    def test_unknown_owner_never_reclaimed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'claim';path.mkdir()
            self.assertFalse(DirectoryClaim(path).acquire())

    def test_live_job_never_reclaimed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'claim';path.mkdir()
            (path/'owner.json').write_text(json.dumps({'job':'123','token':'old'}))
            with patch('directory_claim.expired_job',return_value=False):
                self.assertFalse(DirectoryClaim(path).acquire())

    def test_expired_job_reclaimed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'claim';path.mkdir()
            (path/'owner.json').write_text(json.dumps({'job':'123','token':'old'}))
            with patch('directory_claim.expired_job',return_value=True):
                with DirectoryClaim(path):pass
            self.assertEqual(len(list(Path(d).glob('claim.expired.*'))),1)

    def test_slurm_failure_is_not_expiration(self):
        with patch('directory_claim.subprocess.run',side_effect=OSError):
            self.assertFalse(expired_job({'job':'123'}))


if __name__=='__main__':unittest.main()
