"""Canonical fail-closed error registry for REINA-SEEC."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Severity(str, Enum):
    BLOCKING="BLOCKING"
    WARNING="WARNING"
    INFO="INFO"

@dataclass(frozen=True)
class ErrorSpec:
    code:str
    severity:Severity
    rule:str

ERRORS={
"PRIMARY_BINARY_NOT_REPOSITORY_PINNED":ErrorSpec("PRIMARY_BINARY_NOT_REPOSITORY_PINNED",Severity.BLOCKING,"The canonical primary binary is not stored in versioned binary-capable storage."),
"PRIMARY_HASH_MISMATCH":ErrorSpec("PRIMARY_HASH_MISMATCH",Severity.BLOCKING,"The primary source bytes do not match the immutable SHA-256."),
"ANCHOR_MANIFEST_MISMATCH":ErrorSpec("ANCHOR_MANIFEST_MISMATCH",Severity.BLOCKING,"The anchor manifest identity disagrees with the canonical contract."),
"PRIMARY_RECONCILIATION":ErrorSpec("PRIMARY_RECONCILIATION",Severity.BLOCKING,"Primary and retained replica do not reconcile within the registered tolerance."),
"SEEC_PRODUCTION_EXECUTION":ErrorSpec("SEEC_PRODUCTION_EXECUTION",Severity.BLOCKING,"Certified SEEC posterior evidence is missing or invalid."),
"OOS_CALIBRATION":ErrorSpec("OOS_CALIBRATION",Severity.BLOCKING,"Expanding-window out-of-sample calibration has not passed."),
"EXTERNAL_AUDIT":ErrorSpec("EXTERNAL_AUDIT",Severity.BLOCKING,"Independent external audit evidence is absent."),
"ABSOLUTE_TIE":ErrorSpec("ABSOLUTE_TIE",Severity.BLOCKING,"A legally unresolved absolute tie prevents deterministic allocation."),
"INVALID_VALID_VOTES":ErrorSpec("INVALID_VALID_VOTES",Severity.BLOCKING,"Candidate votes plus blank votes do not reconcile to valid votes."),
"SEAT_CONSERVATION":ErrorSpec("SEAT_CONSERVATION",Severity.BLOCKING,"Allocated seats do not equal the legally defined seat total."),
"FUTURE_INFORMATION":ErrorSpec("FUTURE_INFORMATION",Severity.BLOCKING,"A validation input was not available at the prediction cutoff."),
"METHODOLOGY_DRIFT":ErrorSpec("METHODOLOGY_DRIFT",Severity.BLOCKING,"Execution differs from the canonical methodology contract."),
"SEED_DRIFT":ErrorSpec("SEED_DRIFT",Severity.BLOCKING,"The canonical RNG or seed changed without a versioned methodology change."),
"UNVERSIONED_DATA":ErrorSpec("UNVERSIONED_DATA",Severity.BLOCKING,"A data input lacks immutable version/hash provenance."),
"INVENTED_TERRITORIALITY":ErrorSpec("INVENTED_TERRITORIALITY",Severity.BLOCKING,"Territorial votes were invented or silently imputed."),
"MANUAL_RESULT_OVERRIDE":ErrorSpec("MANUAL_RESULT_OVERRIDE",Severity.BLOCKING,"Votes, seats or model output were manually overridden."),
"NONDETERMINISTIC_EXECUTION":ErrorSpec("NONDETERMINISTIC_EXECUTION",Severity.BLOCKING,"Repeated execution under identical inputs did not reproduce the same result."),
}

def is_blocking(code:str)->bool:
    return code in ERRORS and ERRORS[code].severity is Severity.BLOCKING

def validate_code(code:str)->None:
    if code not in ERRORS:
        raise ValueError(f"UNKNOWN_ERROR_CODE:{code}")
