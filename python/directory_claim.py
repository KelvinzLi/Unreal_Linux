"""Cross-node claims using atomic mkdir, never age-based lock stealing."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid


def expired_job(owner):
    job = str(owner.get('job') or '')
    if not job.isdigit():
        return False
    try:
        result = subprocess.run(['squeue','-h','-j',job,'-o','%T'],
                                capture_output=True,text=True,timeout=5)
    except (OSError,subprocess.TimeoutExpired):
        return False
    # Configuration/network errors never authorize reclaiming a live claim.
    return result.returncode == 0 and not result.stdout.strip() and not result.stderr.strip()


class DirectoryClaim:
    def __init__(self,path):
        self.path=Path(path)
        self.token=uuid.uuid4().hex
        self.owned=False

    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        # Serialize acquisition with stale-owner inspection: otherwise a new
        # owner could replace a released claim between inspection and rename.
        guard=self.path.with_name(self.path.name+'.reaping')
        try:
            guard.mkdir()
        except FileExistsError:
            return False
        try:
            return self._acquire_guarded()
        finally:
            guard.rmdir()

    def _acquire_guarded(self):
        try:
            self.path.mkdir()
        except FileExistsError:
            if not self.reclaim_expired():
                return False
            try:
                self.path.mkdir()
            except FileExistsError:
                return False
        owner=dict(token=self.token,job=os.environ.get('SLURM_JOB_ID'),
                   pid=os.getpid(),host=socket.gethostname(),created=time.time())
        # Missing/malformed owner files are fail-closed, not automatically removed.
        (self.path/'owner.json').write_text(json.dumps(owner))
        self.owned=True
        return True

    def reclaim_expired(self):
        # Caller holds the acquisition guard.
        try:
            owner=json.loads((self.path/'owner.json').read_text())
            if not isinstance(owner,dict) or time.time()-float(owner.get('created',0))<120:
                return False
        except (OSError,ValueError,TypeError):
            return False
        if not expired_job(owner):
            return False
        archive=self.path.with_name(self.path.name+'.expired.'+uuid.uuid4().hex)
        self.path.rename(archive)
        return True

    def release(self):
        if not self.owned:
            return
        owner=json.loads((self.path/'owner.json').read_text())
        if owner.get('token') != self.token:
            raise RuntimeError(f'Claim ownership changed: {self.path}')
        (self.path/'owner.json').unlink()
        self.path.rmdir()
        self.owned=False

    def __enter__(self):
        if not self.owned and not self.acquire():
            raise BlockingIOError(f'Claim busy: {self.path}')
        return self

    def __exit__(self,*_):
        self.release()
