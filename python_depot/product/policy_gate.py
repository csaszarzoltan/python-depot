"""SBOM policy evaluation with expiring waivers and private catalog scope."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class PolicyRule: id:str; field:str; denied_value:str
@dataclass(frozen=True)
class PolicyEvaluation: outcome:str; violations:tuple[str,...]; waived:tuple[str,...]
class PolicyGate:
 def __init__(self,rules:list[PolicyRule]): self.rules=tuple(rules)
 def evaluate(self,sbom:dict,*,waivers:list[dict]|None=None,now:float)->PolicyEvaluation:
  components=sbom.get('components')
  if not isinstance(components,list): raise ValueError("POLICY_SBOM_SCHEMA_INVALID")
  active={w.get('rule_id') for w in (waivers or []) if isinstance(w.get('expires_at'),(int,float)) and w['expires_at']>=now}
  violations=[]; waived=[]
  for component in components:
   name=component.get('name','unknown')
   for rule in self.rules:
    if component.get(rule.field)==rule.denied_value:
     item=f"{rule.id}:{name}"
     (waived if rule.id in active else violations).append(item)
  return PolicyEvaluation("FAIL" if violations else ("WARN" if waived else "PASS"),tuple(violations),tuple(waived))
 def filter_private_catalog(self,packages:list[dict],organization_id:str)->list[dict]:
  return [p for p in packages if not p.get('private') or p.get('organization_id')==organization_id]
