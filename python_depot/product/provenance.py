"""Release provenance and trusted-publisher assessments."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class ProvenanceAssessment: status:str; publisher:str|None; reasons:tuple[str,...]
def assess_provenance(*,attestation_valid:bool|None,publisher:str|None,expected_publisher:str|None,artifact_digest_matches:bool|None)->ProvenanceAssessment:
 reasons=[]
 if attestation_valid is False or artifact_digest_matches is False: return ProvenanceAssessment("INVALID",publisher,("signature or artifact digest invalid",))
 if publisher and expected_publisher and publisher!=expected_publisher: return ProvenanceAssessment("IDENTITY_CHANGED",publisher,("trusted publisher differs from prior identity",))
 if attestation_valid is None: return ProvenanceAssessment("UNKNOWN",publisher,("attestation source unavailable",))
 if not attestation_valid: return ProvenanceAssessment("UNATTESTED",publisher,("no valid attestation",))
 if artifact_digest_matches is not True: reasons.append("artifact digest not independently confirmed")
 return ProvenanceAssessment("VERIFIED",publisher,tuple(reasons))
