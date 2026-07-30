"""Dependency portfolio snapshots and deduplicated risk alerts."""
from __future__ import annotations
import hashlib,json,uuid
from dataclasses import dataclass
from pathlib import Path
from ._sqlite import connect
@dataclass(frozen=True)
class SnapshotResult: portfolio_id:str; digest:str; changed:bool; changes:tuple[str,...]
class PortfolioStore:
 def __init__(self,path:str|Path):
  self.path=str(path)
  with connect(path) as db: db.executescript("CREATE TABLE IF NOT EXISTS portfolios(id TEXT PRIMARY KEY,name TEXT); CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY,portfolio_id TEXT,digest TEXT,payload TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY,portfolio_id TEXT,digest TEXT,message TEXT,state TEXT,UNIQUE(portfolio_id,digest,message));")
 def create(self,name:str)->str:
  pid=uuid.uuid4().hex
  with connect(self.path) as db: db.execute("INSERT INTO portfolios VALUES (?,?)",(pid,name))
  return pid
 def record_snapshot(self,pid:str,dependencies:dict)->SnapshotResult:
  payload=json.dumps(dependencies,sort_keys=True,separators=(",",":")); digest=hashlib.sha256(payload.encode()).hexdigest()
  with connect(self.path) as db:
   prev=db.execute("SELECT digest,payload FROM snapshots WHERE portfolio_id=? ORDER BY id DESC LIMIT 1",(pid,)).fetchone(); changed=not prev or prev[0]!=digest; changes=()
   if prev and changed:
    old=json.loads(prev[1]); changes=tuple(sorted(k for k in set(old)|set(dependencies) if old.get(k)!=dependencies.get(k)))
   db.execute("INSERT INTO snapshots(portfolio_id,digest,payload) VALUES (?,?,?)",(pid,digest,payload))
   for package in changes: db.execute("INSERT OR IGNORE INTO alerts(portfolio_id,digest,message,state) VALUES (?,?,?,'ALERT_PENDING')",(pid,digest,f"risk changed:{package}"))
  return SnapshotResult(pid,digest,changed,changes)
 def pending_alerts(self,pid:str)->list[str]:
  with connect(self.path) as db: return [r[0] for r in db.execute("SELECT message FROM alerts WHERE portfolio_id=? AND state='ALERT_PENDING'",(pid,))]
