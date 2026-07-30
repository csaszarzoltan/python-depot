"""Auditable package comparison workspaces."""
from __future__ import annotations
import hashlib,json,uuid
from dataclasses import dataclass
from pathlib import Path
from ._sqlite import connect
@dataclass(frozen=True)
class DecisionRecord: workspace_id:str; selected:str; rationale:str; evidence_digest:str
class DecisionWorkspaceStore:
 def __init__(self,path:str|Path):
  self.path=str(path)
  with connect(path) as db: db.executescript("CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY,purpose TEXT,state TEXT,candidates TEXT); CREATE TABLE IF NOT EXISTS candidate_snapshots(workspace_id TEXT,candidate TEXT,evidence TEXT,observed_at REAL,PRIMARY KEY(workspace_id,candidate)); CREATE TABLE IF NOT EXISTS decisions(workspace_id TEXT PRIMARY KEY,selected TEXT,rationale TEXT,evidence_digest TEXT);")
 def create(self,purpose:str,candidates:list[str])->str:
  cleaned=sorted(set(x.strip() for x in candidates if x.strip()))
  if len(cleaned)!=len(candidates): raise ValueError("DECIDE_DUPLICATE_CANDIDATE")
  if not purpose.strip() or len(cleaned)<2: raise ValueError("DECIDE_MISSING_EVIDENCE")
  wid=uuid.uuid4().hex
  with connect(self.path) as db: db.execute("INSERT INTO workspaces VALUES (?,?,?,?)",(wid,purpose,"DRAFT",json.dumps(cleaned)))
  return wid
 def add_snapshot(self,wid:str,candidate:str,evidence:dict,*,observed_at:float)->None:
  if not evidence: raise ValueError("DECIDE_MISSING_EVIDENCE")
  with connect(self.path) as db:
   row=db.execute("SELECT candidates,state FROM workspaces WHERE id=?",(wid,)).fetchone()
   if not row or candidate not in json.loads(row[0]) or row[1]=="DECIDED": raise ValueError("invalid workspace candidate or state")
   db.execute("INSERT OR REPLACE INTO candidate_snapshots VALUES (?,?,?,?)",(wid,candidate,json.dumps(evidence,sort_keys=True),observed_at)); db.execute("UPDATE workspaces SET state='EVALUATING' WHERE id=?",(wid,))
 def decide(self,wid:str,selected:str,rationale:str)->DecisionRecord:
  with connect(self.path) as db:
   rows=db.execute("SELECT candidate,evidence,observed_at FROM candidate_snapshots WHERE workspace_id=? ORDER BY candidate",(wid,)).fetchall(); workspace=db.execute("SELECT candidates FROM workspaces WHERE id=?",(wid,)).fetchone()
   if not workspace or len(rows)!=len(json.loads(workspace[0])) or selected not in {r[0] for r in rows}: raise ValueError("DECIDE_MISSING_EVIDENCE")
   digest=hashlib.sha256(json.dumps([tuple(r) for r in rows],sort_keys=True).encode()).hexdigest(); db.execute("INSERT INTO decisions VALUES (?,?,?,?)",(wid,selected,rationale,digest)); db.execute("UPDATE workspaces SET state='DECIDED' WHERE id=?",(wid,))
  return DecisionRecord(wid,selected,rationale,digest)
