import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TypologyDefinition(BaseModel):
    category_id: str
    name: str
    primary_vector: str
    common_pretexts: List[str]
    typical_demands: List[str]
    known_remote_tools: List[str]
    statutory_reference: str
    i4c_guidance: str

# Curated reference knowledge of Indian cybercrime typologies (I4C / 1930 / RBI Guidelines)
SCAM_TYPOLOGIES: List[TypologyDefinition] = [
    TypologyDefinition(
        category_id="digital_arrest",
        name="Digital Arrest / Law Enforcement Impersonation",
        primary_vector="Impersonation of Police, CBI, ED, TRAI, or Supreme Court officials via voice or video calls",
        common_pretexts=[
            "Aadhaar number linked to 14 illegal SIM cards used in criminal extortion",
            "Narcotics or passport package intercepted by Customs at Mumbai/Delhi airport",
            "Money laundering investigation under PMLA with arrest warrant prepared by Supreme Court",
            "Demand to remain under 'digital surveillance' on Skype/WhatsApp video call"
        ],
        typical_demands=[
            "Transfer of 'security clearance deposit' to temporary RBI or Supreme Court holding account",
            "Payment via immediate IMPS/UPI to 'unfreeze' personal accounts",
            "Secrecy oath forbidding victim from contacting relatives or local police"
        ],
        known_remote_tools=["AnyDesk", "TeamViewer", "RustDesk", "QuickSupport"],
        statutory_reference="RBI Circular DBR.No.Leg.BC.78/09.07.005/2017-18; Sections 419, 420 IPC / 66D IT Act",
        i4c_guidance="No government agency or court ever conducts digital arrest or demands financial deposits for verification over WhatsApp or Skype."
    ),
    TypologyDefinition(
        category_id="remote_access_kyc",
        name="Fake KYC / Remote Access Support Scam",
        primary_vector="Phishing SMS or calls threatening imminent SIM card deactivation or bank account suspension",
        common_pretexts=[
            "Your SIM card will be blocked in 24 hours due to incomplete TRAI KYC",
            "Your bank account is frozen; download verification utility to complete re-KYC",
            "Electricity bill payment pending; power will be disconnected tonight"
        ],
        typical_demands=[
            "Install remote desktop application (AnyDesk, TeamViewer, QuickSupport) or custom APK",
            "Make nominal transaction (₹10 or ₹1) to verify account while remote screen share is active",
            "Read out OTP sent via SMS"
        ],
        known_remote_tools=["AnyDesk", "TeamViewer", "QuickSupport", "AirDroid", "RustDesk"],
        statutory_reference="RBI Master Direction on Digital Payment Security Controls; Section 43/66 IT Act",
        i4c_guidance="Banks and telecom operators never ask customers to install remote access utilities to complete KYC."
    ),
    TypologyDefinition(
        category_id="upi_qr_phishing",
        name="UPI QR Code / Collect Request Fraud",
        primary_vector="Online marketplace (OLX, Quikr) or payment reversal deception",
        common_pretexts=[
            "Buyer agrees to purchase item and sends QR code claiming 'scan to receive payment'",
            "Pretends money was mistakenly credited to victim and demands immediate refund via QR code"
        ],
        typical_demands=[
            "Scan QR code and enter UPI MPIN to 'receive money'",
            "Accept pending UPI collect request"
        ],
        known_remote_tools=[],
        statutory_reference="NPCI Unified Payments Interface Procedural Guidelines",
        i4c_guidance="Entering UPI PIN always debits funds from the account. PIN is never required to receive money."
    ),
    TypologyDefinition(
        category_id="task_investment_scam",
        name="Part-Time Job / Telegram Investment Scam",
        primary_vector="Unsolicited WhatsApp/Telegram message offering daily earnings for simple online tasks",
        common_pretexts=[
            "Earn ₹3000 daily by liking YouTube videos or reviewing Google Maps hotels",
            "Initial small payouts (₹150 to ₹500) disbursed to build psychological trust",
            "Invitation to VIP Telegram crypto trading group with guaranteed 300% returns"
        ],
        typical_demands=[
            "Prepaid task deposit to unlock high-tier commission rewards",
            "Additional fee payments to withdraw 'accumulated earnings' on fictitious trading dashboards"
        ],
        known_remote_tools=[],
        statutory_reference="Banning of Unregulated Deposit Schemes Act, 2019 (BUDS Act)",
        i4c_guidance="Legitimate job opportunities do not require candidates to deposit advance security money."
    )
]

# Known high-risk remote access tools and signatures
KNOWN_REMOTE_TOOLS = {
    "anydesk": "Legitimate remote desktop utility frequently weaponized by scammers to intercept OTPs.",
    "teamviewer": "Remote desktop management software weaponized to control victim devices.",
    "rustdesk": "Open-source remote desktop software exploited for unauthorized remote screen control.",
    "quicksupport": "TeamViewer QuickSupport mobile client used to view SMS OTPs in real-time.",
    "airdroid": "Device remote management utility used to access notifications and contacts."
}

class GroundingService:
    """
    Provides regulatory and forensic knowledge grounding for specialized AI agents.
    Strictly separates external reference knowledge from verified case evidence.
    """

    @classmethod
    def get_grounding_context(cls, evidence_text: str) -> Dict[str, Any]:
        """
        Analyze text signals to retrieve relevant external typologies and regulatory references.
        Returns clean structured grounding without hardcoding case conclusions.
        """
        lower = evidence_text.lower()
        matched_typologies = []

        for typo in SCAM_TYPOLOGIES:
            # Check for keyword matches in pretext or tools
            if (
                any(kw in lower for kw in ["arrest", "warrant", "cbi", "supreme court", "trai", "customs", "illegal sim"])
                and typo.category_id == "digital_arrest"
            ):
                matched_typologies.append(typo.model_dump())
            elif (
                any(kw in lower for kw in ["kyc", "sim block", "electricity", "bill", "disconnect"])
                and typo.category_id == "remote_access_kyc"
            ):
                matched_typologies.append(typo.model_dump())
            elif (
                any(kw in lower for kw in ["qr code", "olx", "receive money", "scan to receive", "collect request"])
                and typo.category_id == "upi_qr_phishing"
            ):
                matched_typologies.append(typo.model_dump())
            elif (
                any(kw in lower for kw in ["task", "telegram", "like youtube", "crypto", "vip group", "daily income"])
                and typo.category_id == "task_investment_scam"
            ):
                matched_typologies.append(typo.model_dump())

        # If no specific typology matched, include digital arrest and remote KYC as standard references
        if not matched_typologies:
            matched_typologies = [SCAM_TYPOLOGIES[0].model_dump(), SCAM_TYPOLOGIES[1].model_dump()]

        detected_tool_notes = []
        for tool, note in KNOWN_REMOTE_TOOLS.items():
            if tool in lower:
                detected_tool_notes.append({"tool": tool, "grounding_note": note})

        return {
            "external_typologies": matched_typologies,
            "detected_tool_grounding": detected_tool_notes,
            "disclaimer": (
                "NOTE: External knowledge grounding provided for analytical context only. "
                "All factual determinations must be substantiated directly by case evidence."
            )
        }
