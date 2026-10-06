"""Controles de invariantes del motor."""
from dataclasses import dataclass
from .electoral import valid_votes
@dataclass(frozen=True)
class AuditCheck:
    name:str; status:str; detail:str
def audit_constituency(votes,seats,blank_votes,allocated):
    try: vv=valid_votes(votes,blank_votes)
    except Exception as e: return [AuditCheck("VALID_VOTES","FAIL",str(e))]
    return [
        AuditCheck("VALID_VOTES","PASS",str(vv)),
        AuditCheck("SEATS","PASS" if sum(allocated.values())==seats else "FAIL",f"{sum(allocated.values())}/{seats}"),
        AuditCheck("NONNEGATIVE","PASS" if all(isinstance(v,int) and v>=0 for v in allocated.values()) else "FAIL","allocation"),
    ]
def audit_congress(seats_by_constituency):
    total=sum(seats_by_constituency.values())
    return AuditCheck("CONGRESS_350","PASS" if total==350 else "FAIL",str(total))
