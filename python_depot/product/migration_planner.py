"""Project-wide Python compatibility planning."""
from __future__ import annotations
import re
from dataclasses import dataclass
@dataclass(frozen=True)
class Blocker: package:str; constraint:str; path:tuple[str,...]
@dataclass(frozen=True)
class MigrationPlan: target_python:str; status:str; blockers:tuple[Blocker,...]; steps:tuple[str,...]
def _supports(constraint:str,target:str)->bool:
 t=tuple(map(int,target.split('.')[:2]))
 for op,v in re.findall(r'(<=|>=|<|>|==)\s*(\d+(?:\.\d+)?)',constraint or ''):
  x=tuple(map(int,v.split('.'))); x=x+(0,)*(2-len(x))
  if {'<':t<x,'<=':t<=x,'>':t>x,'>=':t>=x,'==':t==x}[op] is False: return False
 return True
class MigrationPlanner:
 def plan(self,*,target_python:str,dependencies:dict[str,dict])->MigrationPlan:
  incoming={k:[] for k in dependencies}
  for parent,meta in dependencies.items():
   for child in meta.get('depends_on',[]): incoming.setdefault(child,[]).append(parent)
  blockers=[]
  for name,meta in dependencies.items():
   c=meta.get('requires_python','')
   if not _supports(c,target_python): blockers.append(Blocker(name,c,tuple(incoming.get(name,[])+[name])))
  steps=tuple(f"Upgrade or replace {b.package} ({b.constraint}) before targeting Python {target_python}" for b in blockers)
  return MigrationPlan(target_python,"BLOCKED" if blockers else "PLAN_READY",tuple(blockers),steps or (f"Validate tests on Python {target_python}",))
