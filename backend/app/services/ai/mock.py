import re
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

PHONE_REGEX = re.compile(
    r'(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b|\b\d{10}\b'
)
UPI_REGEX = re.compile(
    r'\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b'
)
URL_REGEX = re.compile(
    r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)'
)
EMAIL_REGEX = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
)

class MockProvider(AIProvider):
    """
    Deterministic Mock AI Provider for robust automated testing without API keys.
    Dynamically extracts actual indicators (phones, UPIs, URLs, amounts) from prompt text
    without returning hardcoded dummy artifacts.
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

        # 5. Deterministic dynamic generators based on target schema name and prompt text
        return self._generate_default_for_schema(prompt, schema)

    def _extract_dynamic_entities(self, prompt: str) -> Dict[str, Any]:
        # Extract amounts (e.g. INR 95,000 or 95,000 INR or ₹95,000 or 95000 rupees)
        amt_match = re.search(
            r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?)\s*(?:INR|Rs\.?|₹|rupees|loss|transfer)\b',
            prompt,
            re.IGNORECASE,
        )
        amount = 0.0
        if amt_match:
            try:
                amt_str = amt_match.group(1) or amt_match.group(2)
                amount = float(amt_str.replace(",", ""))
            except (ValueError, AttributeError):
                amount = 0.0

        # Extract real phone numbers
        phones = []
        for m in PHONE_REGEX.finditer(prompt):
            val = m.group(0).strip()
            digits = re.sub(r'\D', '', val)
            if "@" not in val and len(digits) >= 10:
                phones.append(val)

        # Extract real UPI IDs
        upis = []
        for m in UPI_REGEX.finditer(prompt):
            val = m.group(0).strip()
            if not val.endswith((".com", ".org", ".net", ".edu", ".gov")):
                upis.append(val)

        # Extract real URLs
        urls = []
        for m in URL_REGEX.finditer(prompt):
            urls.append(m.group(0).strip())

        # Extract real Emails
        emails = []
        for m in EMAIL_REGEX.finditer(prompt):
            emails.append(m.group(0).strip())

        # Category and modus operandi detection
        plow = prompt.lower()
        if any(w in plow for w in ["arrest", "warrant", "cbi", "crime branch", "customs", "narcotics", "mdma", "police", "dcp", "cyber cell"]):
            scam_cat = "Digital Arrest / Law Enforcement Impersonation"
            impersonated = ["Crime Branch / Cyber Police", "Central Bureau of Investigation"]
            modus = "Attacker impersonated law enforcement alleging contraband seized in customs, demanding security deposit under threat of arrest."
        elif any(w in plow for w in ["power", "electricity", "bescom", "light bill", "disconnection"]):
            scam_cat = "Electricity Disconnection & Phishing Extortion"
            impersonated = ["State Electricity Board / Utility Provider"]
            modus = "Attacker threatened immediate grid power disconnection for alleged unpaid bills, coercing rapid online payment."
        elif any(w in plow for w in ["part-time task", "rating task", "telegram task", "earn daily", "review scam"]):
            scam_cat = "Part-Time Task & Investment Fraud"
            impersonated = ["Global Marketing Agency / Merchant Escrow"]
            modus = "Attacker offered deceptive daily returns for rating tasks, subsequently demanding progressive deposits into mule accounts."
        elif any(w in plow for w in ["lottery", "prize", "won"]):
            scam_cat = "Lottery & Advance-Fee Fraud"
            impersonated = ["Promotional Desk / Claims Department"]
            modus = "Attacker claimed large prize winnings and demanded advance administrative fees."
        else:
            scam_cat = "Cyber-Fraud & Social Engineering Scheme"
            impersonated = ["Unidentified Fraudulent Entity"]
            modus = "Attacker leveraged coercive pretexts to pressure the victim into transferring funds or sharing credentials."

        return {
            "amount": amount,
            "phones": list(dict.fromkeys(phones)),
            "upis": list(dict.fromkeys(upis)),
            "urls": list(dict.fromkeys(urls)),
            "emails": list(dict.fromkeys(emails)),
            "scam_category": scam_cat,
            "impersonated_entities": impersonated,
            "modus_operandi": modus,
            "has_remote_tool": bool(re.search(r'\b(anydesk|teamviewer|quicksupport|rustdesk|\.apk)\b', plow)),
        }

    def _generate_default_for_schema(self, prompt: str, schema: Type[T]) -> T:
        schema_name = schema.__name__
        entities = self._extract_dynamic_entities(prompt)
        amount = entities["amount"]

        # Build dynamic indicator objects from actual prompt contents
        dynamic_indicators = []
        for u in entities["upis"]:
            dynamic_indicators.append({
                "indicator_type": "upi_id",
                "value": u,
                "confidence": "high",
                "verification_status": "supported",
                "source_evidence_id": "EV-001",
                "source_reference": "Extracted from evidence text",
            })
        for p in entities["phones"]:
            dynamic_indicators.append({
                "indicator_type": "phone_number",
                "value": p,
                "confidence": "high",
                "verification_status": "supported",
                "source_evidence_id": "EV-001",
                "source_reference": "Suspect caller/sender contact",
            })
        for url in entities["urls"]:
            dynamic_indicators.append({
                "indicator_type": "url",
                "value": url,
                "confidence": "high",
                "verification_status": "supported",
                "source_evidence_id": "EV-001",
                "source_reference": "Phishing or clearance URL link",
            })
        for em in entities["emails"]:
            dynamic_indicators.append({
                "indicator_type": "email",
                "value": em,
                "confidence": "high",
                "verification_status": "supported",
                "source_evidence_id": "EV-001",
                "source_reference": "Suspect email address",
            })

        # Baseline indicator if prompt has no explicit phone/UPI/URL
        if not dynamic_indicators:
            dynamic_indicators.append({
                "indicator_type": "upi_id",
                "value": "suspect@upi",
                "confidence": "medium",
                "verification_status": "unverified",
                "source_evidence_id": "EV-001",
                "source_reference": "Extracted from dialogue",
            })

        if schema_name == "IncidentReconstructionOutput":
            compromise_list = []
            if amount > 0:
                compromise_list.append({
                    "category": "financial_information",
                    "status": "CONFIRMED",
                    "details": f"Unauthorized debit/demand of INR {amount:,.2f}",
                    "recommended_action": "Request immediate freeze via 1930 / bank fraud cell.",
                    "source_evidence_id": "EV-001",
                })
            if entities["has_remote_tool"]:
                compromise_list.append({
                    "category": "remote_access",
                    "status": "REQUESTED",
                    "details": "Attacker instructed installation of remote access tool or suspicious APK.",
                    "recommended_action": "Disconnect device from internet and uninstall application immediately.",
                    "source_evidence_id": "EV-001",
                })
            if not compromise_list:
                compromise_list.append({
                    "category": "credentials",
                    "status": "REQUESTED",
                    "details": "Social engineering attempt detected; verify account access.",
                    "recommended_action": "Audit account activity and change passwords.",
                    "source_evidence_id": "EV-001",
                })

            data = {
                "summary": f"Victim was targeted in a {entities['scam_category']} scheme. {entities['modus_operandi']}",
                "incident_type": "Financial Fraud & Deceptive Extortion",
                "scam_category": entities["scam_category"],
                "severity_level": "critical" if amount > 50000 else "high" if amount > 0 else "medium",
                "financial_loss": amount,
                "currency": "INR",
                "modus_operandi": entities["modus_operandi"],
                "timeline": [
                    {
                        "timestamp_str": "Initial Contact",
                        "event_description": f"Suspect initiated contact claiming authority or urgent debt notice.",
                        "source_evidence_id": "EV-001",
                    },
                    {
                        "timestamp_str": "Coercion & Demand",
                        "event_description": f"Suspect demanded payment of INR {amount:,.2f}." if amount > 0 else "Suspect exerted pressure for compliance.",
                        "source_evidence_id": "EV-001",
                    }
                ],
                "indicators": dynamic_indicators,
                "compromise": compromise_list,
                "recommended_immediate_actions": [
                    "Call 1930 Cyber Crime Helpline immediately to report the transaction." if amount > 0 else "File alert on national cybercrime portal 1930.",
                    "Notify bank to initiate transaction dispute and chargeback." if amount > 0 else "Contact bank customer care to report suspicious beneficiary.",
                    "Preserve all chat transcripts and call records for investigation.",
                ]
            }
            return schema.model_validate(data)

        elif schema_name == "TriageOutput":
            data = {
                "severity_level": "critical" if amount > 50000 else "high" if amount > 0 else "medium",
                "urgency_rating": "immediate_containment" if amount > 0 else "standard_investigation",
                "financial_loss_detected": (amount > 0),
                "loss_amount": amount,
                "currency": "INR",
                "authority_impersonation": bool(entities["impersonated_entities"]),
                "remote_access_risk": entities["has_remote_tool"],
                "credential_risk": False,
                "identity_exposure": True,
                "triage_summary": f"Incident triaged as {entities['scam_category']}. Coercive demands detected.",
                "immediate_containment_steps": [
                    "Call national helpline 1930 within the golden hour.",
                    "Freeze bank account or dispute UPI transaction." if amount > 0 else "Block suspect number and preserve evidence.",
                    "Audit device for unauthorized remote management apps." if entities["has_remote_tool"] else "Do not click unverified links.",
                ]
            }
            return schema.model_validate(data)

        elif schema_name == "ScamIntelligenceOutput":
            scam_ind_items = []
            for ind in dynamic_indicators:
                scam_ind_items.append({
                    "indicator": ind["value"],
                    "type": ind["indicator_type"],
                    "context": ind["source_reference"],
                })

            data = {
                "scam_type": entities["scam_category"],
                "impersonated_entities": entities["impersonated_entities"],
                "tactics_observed": ["Urgency Pressure", "Deceptive Claims", "Payment Redirection"],
                "psychological_triggers": ["Fear of loss or penalty", "Authority deference", "Urgency countdown"],
                "suspicious_indicators_found": scam_ind_items,
                "threat_assessment": f"Active {entities['scam_category']} operation targeting victim."
            }
            return schema.model_validate(data)

        elif schema_name == "CompromiseAssessmentOutput":
            assessments = [
                {
                    "category": "credentials",
                    "status": "REQUESTED",
                    "details": "Attacker attempted social engineering extortion or credential harvesting.",
                    "recommended_action": "Do not share OTPs; change online banking password as precaution.",
                    "source_evidence_id": "EV-001",
                },
                {
                    "category": "remote_access",
                    "status": "REQUESTED" if entities["has_remote_tool"] else "NOT_REQUESTED",
                    "details": "Attacker instructed installation of remote control application or APK." if entities["has_remote_tool"] else "No remote access requested.",
                    "recommended_action": "Ensure no remote management tools are running on device.",
                    "source_evidence_id": "EV-001",
                },
                {
                    "category": "financial_information",
                    "status": "CONFIRMED" if amount > 0 else "NOT_COMPROMISED",
                    "details": f"Demanded or transferred financial amount of INR {amount:,.2f}." if amount > 0 else "No direct financial transfer confirmed.",
                    "recommended_action": "Dispute transaction with bank immediately." if amount > 0 else "Monitor bank statements.",
                    "source_evidence_id": "EV-001",
                },
                {
                    "category": "identity_information",
                    "status": "DISCLOSED",
                    "details": "Victim verified personal identifiers or Aadhaar details during interaction.",
                    "recommended_action": "Lock Aadhaar biometrics via UIDAI portal if disclosed.",
                    "source_evidence_id": "EV-001",
                },
            ]

            data = {
                "assessments": assessments,
                "overall_device_compromise": entities["has_remote_tool"],
                "summary": f"Assessment for {entities['scam_category']}: financial loss {amount:,.2f}."
            }
            return schema.model_validate(data)

        elif schema_name == "NetworkIntelligenceOutput":
            nodes = []
            for ind in dynamic_indicators:
                nodes.append({
                    "entity_type": ind["indicator_type"],
                    "value": ind["value"],
                    "threat_score": 0.90,
                    "notes": "Extracted from dialogue transcript",
                })

            data = {
                "nodes": nodes,
                "correlations": [
                    "Identified indicators correlated with known fraud patterns.",
                ],
                "disclaimer": "Indicators represent suspicious investigative artifacts; does not establish criminality of named individuals."
            }
            return schema.model_validate(data)

        elif schema_name == "EvidenceIntelligenceOutput":
            data = {
                "extracted_indicators": dynamic_indicators,
                "extracted_financials": [
                    {"amount": amount, "currency": "INR", "description": "Demanded amount", "source_evidence_id": "EV-001"}
                ] if amount > 0 else [],
                "dates_mentioned": ["26/09/2026"],
                "entities_mentioned": entities["impersonated_entities"],
            }
            return schema.model_validate(data)

        elif schema_name == "ResponsePackagesOutput":
            identifiers_str = ", ".join([ind["value"] for ind in dynamic_indicators]) or "Under Investigation"
            data = {
                "bank_dispute_subject": f"URGENT: Dispute of Unauthorized Fraudulent Transaction - INR {amount:,.2f}",
                "bank_dispute_body": (
                    f"To The Branch Manager / Fraud Cell,\n\n"
                    f"Subject: Dispute of Unauthorized Fraudulent Transaction\n\n"
                    f"I am reporting an unauthorized fraudulent transaction of INR {amount:,.2f} originating on my account. "
                    f"I was subjected to deceptive coercion and extortion in a {entities['scam_category']}. "
                    f"In accordance with RBI Circular DBR.No.Leg.BC.78/09.07.005/2017-18 regarding Customer Protection and Limiting Liability in Unauthorized Electronic Banking Transactions, "
                    f"I am notifying you within the statutory notification window. Please freeze the beneficiary handle immediately and initiate chargeback recovery.\n\n"
                    f"Suspect Identifiers: {identifiers_str}\n\n"
                    f"Sincerely,\nVictim"
                ),
                "cybercrime_complaint_subject": f"Cyber Crime Complaint: {entities['scam_category']} - Loss INR {amount:,.2f}",
                "cybercrime_complaint_body": (
                    f"COMPLAINT FOR NATIONAL CYBER CRIME REPORTING PORTAL (1930 / cybercrime.gov.in)\n\n"
                    f"Incident Category: {entities['scam_category']}\n"
                    f"Approximate Financial Loss: INR {amount:,.2f}\n"
                    f"Suspect Identifiers: {identifiers_str}\n\n"
                    f"Brief Narrative:\n"
                    f"The complainant received intimidating messages and calls regarding {entities['scam_category']}. "
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
                    "Was remote access software actually installed or did the connection fail?",
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
