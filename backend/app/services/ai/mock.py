import logging
from typing import TypeVar, Type, Optional, Dict, Any, Callable
from pydantic import BaseModel

from backend.app.services.ai.base import (
    AIProvider,
    AIError,
    AIQuotaExhaustedError,
    AIProviderUnavailableError,
    AISchemaValidationError,
)
from backend.app.services.ai.parser import RobustJSONParser

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class MockProvider(AIProvider):
    """
    Deterministic Mock AI Provider for robust automated testing without API keys.
    Supports simulated failures, quota exhaustion, malformed output testing,
    and custom response registration per schema.
    """

    def __init__(
        self,
        simulate_failure: bool = False,
        simulate_quota: bool = False,
        simulate_unavailable: bool = False,
        simulate_malformed: bool = False,
    ):
        self.simulate_failure = simulate_failure
        self.simulate_quota = simulate_quota
        self.simulate_unavailable = simulate_unavailable
        self.simulate_malformed = simulate_malformed
        self._custom_responses: Dict[str, Any] = {}
        self._custom_handlers: Dict[str, Callable] = {}
        self.call_history: list = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def register_response(self, key: str, response: Any):
        """Register a canned response for a schema name or prompt keyword."""
        self._custom_responses[key.lower()] = response

    def register_handler(self, schema_name: str, handler: Callable[[str], Any]):
        """Register a dynamic generator handler for a schema name."""
        self._custom_handlers[schema_name.lower()] = handler

    async def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        self.call_history.append({"prompt": prompt, "schema": schema.__name__})

        # 1. Error simulation
        if self.simulate_quota:
            raise AIQuotaExhaustedError("Simulated Mock AI quota exhaustion.")
        if self.simulate_unavailable:
            raise AIProviderUnavailableError("Simulated Mock AI service unavailable (503).")
        if self.simulate_failure:
            raise AIError("Simulated Mock AI general provider failure.")
        if self.simulate_malformed:
            return RobustJSONParser.parse_and_validate("<<<not-json>>>", schema)

        schema_key = schema.__name__.lower()

        # 2. Check custom handler
        if schema_key in self._custom_handlers:
            res = self._custom_handlers[schema_key](prompt)
            if isinstance(res, schema):
                return res
            return schema.model_validate(res)

        # 3. Check custom registered response
        if schema_key in self._custom_responses:
            res = self._custom_responses[schema_key]
            if isinstance(res, schema):
                return res
            return schema.model_validate(res)

        # 4. Check prompt keywords
        for k, v in self._custom_responses.items():
            if k in prompt.lower():
                if isinstance(v, schema):
                    return v
                return schema.model_validate(v)

        # 5. Deterministic fallback generators based on target schema name
        return self._generate_default_for_schema(prompt, schema)

    def _generate_default_for_schema(self, prompt: str, schema: Type[T]) -> T:
        schema_name = schema.__name__

        # Extract amounts or keywords from prompt if present
        is_digital_arrest = "arrest" in prompt.lower() or "warrant" in prompt.lower() or "cbi" in prompt.lower()
        amount = 95000.0 if "95,000" in prompt or "95000" in prompt else 85000.0

        if schema_name == "IncidentReconstructionOutput":
            data = {
                "summary": "Victim was targeted in an impersonation scheme threatening arrest and coerced into transferring funds.",
                "incident_type": "Financial Fraud & Law Enforcement Impersonation",
                "scam_category": "Digital Arrest / Law Enforcement Impersonation" if is_digital_arrest else "UPI Extortion Fraud",
                "severity_level": "critical",
                "financial_loss": amount,
                "currency": "INR",
                "modus_operandi": "Attacker impersonated investigative authorities via WhatsApp, presented forged warrants, and demanded urgent deposit via UPI under threat of physical arrest.",
                "timeline": [
                    {"timestamp_str": "Initial Contact", "event_description": "Suspect initiated contact claiming Aadhaar was compromised in illegal activities.", "source_evidence_id": "EV-001"},
                    {"timestamp_str": "Coercion & Demand", "event_description": "Suspect demanded security deposit of funds to reserve clearing account.", "source_evidence_id": "EV-002"}
                ],
                "indicators": [
                    {"indicator_type": "upi_id", "value": "clearing95@okhdfcbank", "confidence": "high", "verification_status": "supported", "source_evidence_id": "EV-001", "source_reference": "Extracted from message"},
                    {"indicator_type": "phone_number", "value": "+919876543210", "confidence": "high", "verification_status": "supported", "source_evidence_id": "EV-001", "source_reference": "Suspect caller"}
                ],
                "compromise": [
                    {"category": "financial_information", "status": "CONFIRMED", "details": f"Unauthorized debit of INR {amount:,.2f}", "recommended_action": "Request immediate freeze via 1930 / bank fraud cell.", "source_evidence_id": "EV-001"},
                    {"category": "remote_access", "status": "REQUESTED", "details": "Attacker instructed installation of AnyDesk.", "recommended_action": "Disconnect device from internet and uninstall AnyDesk immediately.", "source_evidence_id": "EV-002"}
                ],
                "recommended_immediate_actions": [
                    "Call 1930 Cyber Crime Helpline immediately to report the beneficiary UPI handle.",
                    "Notify bank to initiate transaction dispute and chargeback.",
                    "Disconnect any remote-access software sessions."
                ]
            }
            return schema.model_validate(data)

        elif schema_name == "TriageOutput":
            data = {
                "severity_level": "critical",
                "urgency_rating": "immediate_containment",
                "financial_loss_detected": True,
                "loss_amount": amount,
                "currency": "INR",
                "authority_impersonation": is_digital_arrest,
                "remote_access_risk": True,
                "credential_risk": False,
                "identity_exposure": True,
                "triage_summary": "High-urgency financial fraud with active extortion and remote access pressure.",
                "immediate_containment_steps": [
                    "Call national helpline 1930 within the golden hour.",
                    "Freeze bank account or dispute UPI transaction.",
                    "Audit device for unauthorized remote management apps."
                ]
            }
            return schema.model_validate(data)

        elif schema_name == "ScamIntelligenceOutput":
            data = {
                "scam_type": "Digital Arrest / Law Enforcement Impersonation" if is_digital_arrest else "Financial Coercion",
                "impersonated_entities": ["Supreme Court of India", "CBI / Cyber Cell"] if is_digital_arrest else ["Bank Fraud Desk"],
                "tactics_observed": ["Urgency Pressure", "Legal Intimidation", "Remote Access Request", "Confidential Clearance Pretext"],
                "psychological_triggers": ["Fear of immediate arrest", "False authority", "Time limit countdown"],
                "suspicious_indicators_found": [
                    {"indicator": "clearing95@okhdfcbank", "type": "upi_id", "context": "Demand beneficiary handle"},
                    {"indicator": "+919876543210", "type": "phone_number", "context": "Impersonator phone"}
                ],
                "threat_assessment": "Coercive digital extortion using fabricated legal authority."
            }
            return schema.model_validate(data)

        elif schema_name == "CompromiseAssessmentOutput":
            data = {
                "assessments": [
                    {
                        "category": "credentials",
                        "status": "REQUESTED",
                        "details": "Attacker requested account credentials and OTP but victim did not disclose.",
                        "recommended_action": "Do not share OTPs; change online banking password as precaution.",
                        "source_evidence_id": "EV-001"
                    },
                    {
                        "category": "remote_access",
                        "status": "REQUESTED",
                        "details": "Attacker requested victim to install AnyDesk.",
                        "recommended_action": "Ensure no remote management tools are running on device.",
                        "source_evidence_id": "EV-001"
                    },
                    {
                        "category": "financial_information",
                        "status": "CONFIRMED",
                        "details": f"Confirmed financial transfer of INR {amount:,.2f} occurred.",
                        "recommended_action": "Dispute transaction with bank immediately.",
                        "source_evidence_id": "EV-001"
                    },
                    {
                        "category": "identity_information",
                        "status": "DISCLOSED",
                        "details": "Victim verified Aadhaar number during call.",
                        "recommended_action": "Lock Aadhaar biometrics via UIDAI portal.",
                        "source_evidence_id": "EV-001"
                    }
                ],
                "overall_device_compromise": False,
                "summary": "Financial transfer confirmed; credentials requested but not confirmed compromised."
            }
            return schema.model_validate(data)

        elif schema_name == "NetworkIntelligenceOutput":
            data = {
                "nodes": [
                    {"entity_type": "upi_id", "value": "clearing95@okhdfcbank", "threat_score": 0.95, "notes": "Extortion payee handle"},
                    {"entity_type": "phone_number", "value": "+919876543210", "threat_score": 0.85, "notes": "Calling party"},
                    {"entity_type": "url", "value": "https://trai-verification-portal.xyz/kyc", "threat_score": 0.90, "notes": "Phishing portal"}
                ],
                "correlations": [
                    "Phone number matches pattern of VOIP forwarded scam calls.",
                    "Domain registrar registered within past 7 days."
                ],
                "disclaimer": "Indicators represent suspicious investigative artifacts; does not establish criminality of named individuals."
            }
            return schema.model_validate(data)

        elif schema_name == "EvidenceIntelligenceOutput":
            data = {
                "extracted_indicators": [
                    {"indicator_type": "upi_id", "value": "clearing95@okhdfcbank", "confidence": "high", "verification_status": "supported", "source_evidence_id": "EV-001", "source_reference": "Chat Message"},
                    {"indicator_type": "phone_number", "value": "+919876543210", "confidence": "high", "verification_status": "supported", "source_evidence_id": "EV-001", "source_reference": "Call log"}
                ],
                "extracted_financials": [
                    {"amount": amount, "currency": "INR", "description": "Demanded security deposit", "source_evidence_id": "EV-001"}
                ],
                "dates_mentioned": ["26/09/2026", "25/09/2026"],
                "entities_mentioned": ["Supreme Court of India", "CBI", "DCP Rajesh Sharma"]
            }
            return schema.model_validate(data)

        elif schema_name == "ResponsePackagesOutput":
            data = {
                "bank_dispute_subject": f"URGENT: Dispute of Unauthorized Fraudulent Transaction - INR {amount:,.2f}",
                "bank_dispute_body": (
                    f"To The Branch Manager / Fraud Cell,\n\n"
                    f"Subject: Dispute of Unauthorized Fraudulent Transaction\n\n"
                    f"I am reporting an unauthorized fraudulent debit of INR {amount:,.2f} originating on my account. "
                    f"I was subjected to deceptive coercion and extortion by imposters posing as legal authorities. "
                    f"In accordance with RBI Circular DBR.No.Leg.BC.78/09.07.005/2017-18 regarding Customer Protection and Limiting Liability in Unauthorized Electronic Banking Transactions, "
                    f"I am notifying you within the statutory notification window. Please freeze the beneficiary handle immediately and initiate chargeback recovery.\n\n"
                    f"Beneficiary Handle: clearing95@okhdfcbank\n\n"
                    f"Sincerely,\nVictim"
                ),
                "cybercrime_complaint_subject": f"Cyber Crime Complaint: Digital Arrest & Extortion - Loss INR {amount:,.2f}",
                "cybercrime_complaint_body": (
                    f"COMPLAINT FOR NATIONAL CYBER CRIME REPORTING PORTAL (1930 / cybercrime.gov.in)\n\n"
                    f"Incident Category: Impersonation / Digital Arrest Extortion\n"
                    f"Approximate Financial Loss: INR {amount:,.2f}\n"
                    f"Suspect Identifiers: clearing95@okhdfcbank, +919876543210\n\n"
                    f"Brief Narrative:\n"
                    f"The complainant received intimidating messages and calls falsely claiming an arrest warrant from the Supreme Court / CBI. "
                    f"The caller coerced the complainant into transferring INR {amount:,.2f} under duress. "
                    f"All evidence artifacts including screenshots and transaction IDs have been preserved."
                ),
                "emergency_advisory": (
                    "1. Call 1930 immediately to freeze funds before the scammer cashes out.\n"
                    "2. Submit formal dispute letter to your home branch.\n"
                    "3. Do not engage further with the suspect."
                )
            }
            return schema.model_validate(data)

        elif schema_name == "FollowUpAgentOutput":
            data = {
                "missing_information": [
                    "Exact 12-digit UTR transaction reference number for the bank transfer",
                    "Official bank account statement showing debit timestamp"
                ],
                "unanswered_questions": [
                    "Was AnyDesk actually installed or did the connection fail?",
                    "Did the victim share OTP directly via SMS or enter it on a website?"
                ],
                "evidence_gaps": [
                    "Missing screenshot of the bank transfer confirmation screen"
                ],
                "contradictions_detected": [],
                "recommended_additional_evidence": [
                    "Bank passbook / e-statement PDF for the incident date",
                    "Device application audit list to verify AnyDesk status"
                ]
            }
            return schema.model_validate(data)

        # Generic Pydantic fallback: instantiate with dummy schema values
        return schema.model_construct()

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        self.call_history.append({"prompt": prompt, "type": "text"})
        if self.simulate_failure:
            raise AIError("Simulated Mock AI text generation failure.")
        return f"Mock AI Response to: {prompt[:80]}"
