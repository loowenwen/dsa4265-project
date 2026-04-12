APPROVE_THRESHOLD = 0.30
REJECT_THRESHOLD = 0.50
ANOMALY_REVIEW_THRESHOLD = 0.1173

REASON_CODES = {
    "INCOMPLETE_DATA": "Missing or unidentifiable required fields",
    "SUSPICIOUS_INPUT": "Suspicious or out-of-range applicant inputs",
    "POLICY_HARD_STOP": "Policy hard stop triggered",
    "POLICY_REVIEW_TRIGGER": "Policy review required",
    "HIGH_DEFAULT_RISK": "Default probability exceeds reject threshold",
    "ELEVATED_ANOMALY": "Anomaly score above review threshold",
    "OUT_OF_DISTRIBUTION": "Input detected as out-of-distribution",
    "LOW_RISK_CLEAR_POLICY": "Low default risk with clear policy and data",
}
