"""Review evidence and conflict-safe moderation."""
from __future__ import annotations
import json,uuid
from dataclasses import dataclass
from pathlib import Path
from ._sqlite import connect
@dataclass(frozen=True)
class TrustedReview: id:str; package:str; author:str; body:str; status:str
class ReviewModerationStore:
 def __init__(self,path:str|Path):
  self.path=str(path)
  with connect(path) as db: db.executescript("CREATE TABLE IF NOT EXISTS trusted_reviews(id TEXT PRIMARY KEY,package TEXT,author TEXT,body TEXT,evidence TEXT,status TEXT); CREATE TABLE IF NOT EXISTS moderation_events(id INTEGER PRIMARY KEY,review_id TEXT,actor TEXT,action TEXT,reason TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);")
 def submit(self,package:str,author:str,body:str,*,evidence:dict)->TrustedReview:
  if not body.strip() or not evidence.get('lock_hash'): raise ValueError("REVIEW_EVIDENCE_INVALID")
  rid=uuid.uuid4().hex
  with connect(self.path) as db: db.execute("INSERT INTO trusted_reviews VALUES (?,?,?,?,?,'VERIFIED_USER')",(rid,package,author,body,json.dumps(evidence,sort_keys=True)))
  return TrustedReview(rid,package,author,body,"VERIFIED_USER")
 def moderate(self,rid:str,*,actor:str,action:str,actor_packages:set[str],reason:str='')->TrustedReview:
  with connect(self.path) as db:
   row=db.execute("SELECT package,author,body,status FROM trusted_reviews WHERE id=?",(rid,)).fetchone()
   if not row: raise KeyError(rid)
   if row[0] in actor_packages or actor==row[1]: raise PermissionError("REVIEW_SELF_PROMOTION")
   target={'HIDE':'HIDDEN','RESTORE':'RESTORED','REJECT':'REJECTED'}.get(action)
   if not target: raise ValueError("REVIEW_MODERATION_CONFLICT")
   db.execute("UPDATE trusted_reviews SET status=? WHERE id=?",(target,rid)); db.execute("INSERT INTO moderation_events(review_id,actor,action,reason) VALUES (?,?,?,?)",(rid,actor,action,reason))
  return TrustedReview(rid,row[0],row[1],row[2],target)
