from enum import StrEnum


class EvidenceStatus(StrEnum):
    PROVEN = "PROVEN"
    SUPPORTED = "SUPPORTED"
    CONTESTED = "CONTESTED"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"


class EvidenceSourceType(StrEnum):
    SYNTHETIC_EXPERIMENT = "synthetic_experiment"
    EXTERNAL_RELIABLE = "external_reliable"
    DIRECT_HUMAN_OBSERVATION = "direct_human_observation"


class Decision(StrEnum):
    CONTINUE = "CONTINUE"
    MODIFY = "MODIFY"
    VALIDATE_WITH_HUMANS = "VALIDATE_WITH_HUMANS"
    KILL = "KILL"


class PersonaType(StrEnum):
    PARENT = "parent"
    CHILD = "child"
    EDUCATION = "education"
    RED_TEAM = "red_team"


class SafetyClass(StrEnum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    ADULT_BRIDGE = "ADULT_BRIDGE"
    IMMEDIATE_SAFETY = "IMMEDIATE_SAFETY"
    REFUSE_AND_REDIRECT = "REFUSE_AND_REDIRECT"
