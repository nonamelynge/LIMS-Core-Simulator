from enum import Enum

class AnalysisStatus(Enum):
    PENDING = "Pending"
    PASSED = "Passed"
    OOS = "OOS"

class SampleStatus(Enum):
    REGISTERED = "Registered"
    IN_PROGRESS = "In Progress"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class SampleType(Enum):
    RM = "Raw Material"
    DS = "Drug Substance"
    DP = "Drug Product"
    IHR = "In House Reference"
