# CounterPulse AI — Master Project Specification

> **Hackathon**: Build for Billions Hackathon  
> **Team**: The Valiente  
> **Track**: Agentic AI For Billions  
> **Institution**: Mangalore Institute of Technology and Engineering (MITE), Moodbidri  
> **Version**: 1.0.0 (Foundation Release)  
> **Status**: Active Reference Specification  

---

## 1. Product Overview

- **Product Name**: CounterPulse AI
- **Tagline**: Turn panic into an actionable fraud case.
- **One-Line Description**: CounterPulse AI is an evidence-first, agentic AI digital companion that helps cyber-fraud victims reconstruct what happened, understand what may be compromised, organize messy multimodal evidence, and prepare recovery actions while keeping the human firmly in control.
- **Core Principle**: CounterPulse is **NOT** a simple scam detector. It is an AI-powered incident-response and recovery orchestration platform. It converts chaotic, stressful situations into a structured, verifiable, and legally actionable case.

### Core Questions CounterPulse Answers:
1. What happened, and when did key events occur?
2. What evidence exists to support each fact?
3. What specific indicators (UPI IDs, phone numbers, URLs, transaction IDs, names) can be extracted?
4. What accounts, credentials, or devices may have been compromised?
5. What emergency containment steps should the victim take immediately?
6. What formal documents/reports are needed for banks and cyber police?
7. What critical evidence is still missing?
8. What recovery packages can be prepared automatically?
9. Which consequential actions require explicit, informed human approval?

---

## 2. Problem Statement

Digital fraud victims in India and globally are thrust into the role of forensic investigators during a moment of peak psychological distress. Following a scam, victims possess fragmented pieces of evidence across multiple apps:
- WhatsApp and Telegram chat logs
- Bank debit SMS notifications
- Screenshots of fraudulent payment apps, malicious APKs, or phishing sites
- Fake FIRs, court orders, or arrest warrants (e.g., in "Digital Arrest" scams)
- Call audio recordings or voicemails
- UTR / Transaction reference numbers

Victims face extreme friction in:
- Identifying the financial loss and specific beneficiary handles
- Knowing if their device has remote-access tools (AnyDesk, TeamViewer) installed
- Drafting formal dispute letters within the golden hour (first 2 to 24 hours) for bank freeze mechanisms (e.g., Indian Cyber Crime Coordination Centre - I4C / 1930 portal)
- Preserving legal evidence provenance for law enforcement

CounterPulse AI eliminates this cognitive burden by providing an agentic, evidence-first incident reconstruction engine.

---

## 3. Core Workflow

```text
       VICTIM / USER
             │
             ▼
   [1. Evidence Intake]  <── Text, Images, PDFs, Audio, SMS, URLs
             │
             ▼
[2. Multimodal Normalization] <── OCR, Document Parsing, Audio Transcription
             │
             ▼
[3. Incident Reconstruction Agent] <── Chronological timeline, financial loss, actors
             │
             ▼
[4. Scam Intelligence Agent] <── Entity extraction (UPI, Phone, URLs, Tactics)
             │
             ▼
[5. Compromise Assessment Agent] <── Banking, Device, Credentials, Identity risks
             │
             ▼
   [6. Fraud Case Passport] <── Verifiable Case Record with Provenance Chains
             │
             ▼
 [7. Response Package Generator] <── Bank Dispute, Cybercrime Draft (1930/NCRP)
             │
             ▼
  [8. Human Review & Approval] <── Explicit HITL Gate (Review, Edit, Confirm)
             │
             ▼
 [9. Executed Approved Action] <── Verified Email Dispatch, PDF Generation
             │
             ▼
   [10. Recovery & Follow-up] <── Actionable checklist, deadline reminders
```

---

## 4. Functional Requirements

1. **Case Management**: Create, view, list, and update cyber-fraud cases.
2. **Multimodal Evidence Ingestion**: Accept screenshots (PNG/JPEG/WEBP), documents (PDF), raw text/SMS/chat exports, and recorded audio files (WAV/MP3/M4A).
3. **Structured AI Incident Reconstruction**: Dynamically extract incident narrative, timeline milestones, financial loss amounts, currency, and scam classification with strict JSON schemas.
4. **Scam Indicator Extraction with Provenance**: Extract all identifiable entities (UPI IDs, phone numbers, URLs, email addresses, suspect aliases, fake agencies) linked directly to their source evidence identifier.
5. **Compromise Assessment**: Evaluate exposure across Banking Details, Credentials, Personal Identifiable Information (PII), and Remote Access/Device compromise.
6. **Fraud Case Passport**: Provide a consolidated digital dossier containing case metrics, provenance-backed facts, and severity scoring.
7. **Response Package Generation**: Formulate formal Bank Dispute Letters and National Cyber Crime Reporting Portal (NCRP / 1930) complaint drafts.
8. **Human-in-the-Loop (HITL) Execution**: Explicit approval state machine before any external action (e.g., sending email to bank fraud cell or generating official submission PDFs).
9. **Real PDF Dossier Generation**: Render real, formatted PDF case files using ReportLab with embedded provenance tables.
10. **Verified Email Dispatch**: Send dispute packets to designated recipients via real transactional email APIs with full delivery audit logging.

---

## 5. Non-Functional Requirements

- **Zero-Fake Rule**: No hardcoded AI responses, fake scam tags, or mock successful states. Every output displayed must originate from real models or verified database state.
- **Fail-Safe & Graceful Degradation**: If an AI provider or external API is unconfigured or unreachable, the system must emit clear, actionable error messages rather than simulated output.
- **Latency & Responsiveness**: Processing multimodal evidence within 15 seconds; streaming or explicit status tracking for asynchronous tasks.
- **Privacy & Security**: PII and banking data encrypted at rest and sanitized in logs. No credentials exposed in client-side code.
- **Auditability**: Complete provenance trail from every extracted fact back to the raw source evidence byte stream.
- **Portability**: Clean architectural separation allowing local SQLite for rapid hackathon iteration and effortless migration to PostgreSQL/Supabase.

---

## 6. System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 18 + TS)                        │
│   Tailwind CSS  │  Lucide Icons  │  Glassmorphism  │  HITL Review UI   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST (JSON)
┌───────────────────────────────────▼────────────────────────────────────┐
│                       BACKEND API (FastAPI)                            │
│  ┌───────────────────────┐  ┌───────────────────────────────────────┐  │
│  │   Route Controllers   │  │         Pydantic Validation           │  │
│  │ /cases, /evidence,    │  │ Strict Input / Output Schema Contract │  │
│  │ /analyze, /passport   │  └───────────────────────────────────────┘  │
│  └───────────┬───────────┘                                             │
│              ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     ORCHESTRATION LAYER                          │  │
│  │   Incident Agent │ Scam Intel Agent │ Compromise Assessor        │  │
│  └───────────────────┬──────────────────────────────────────────────┘  │
│                      │                                                 │
│       ┌──────────────┴──────────────┐                                  │
│       ▼                             ▼                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  AI Provider Interface  │  │        Services & Integrations      │  │
│  │  ┌───────────────────┐  │  │  - PDF Service (ReportLab)          │  │
│  │  │ GeminiProvider    │  │  │  - Email Service (Resend/SMTP)      │  │
│  │  ├───────────────────┤  │  │  - File Storage (Local Secure Store)│  │
│  │  │ FallbackProvider  │  │  └─────────────────────────────────────┘  │
│  │  └───────────────────┘  │                                           │
│  └─────────────────────────┘                                           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy ORM
┌───────────────────────────────────▼────────────────────────────────────┐
│                        DATABASE LAYER (SQLite)                         │
│   cases │ evidence │ indicators │ timeline │ compromise │ reports      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Frontend Architecture

- **Framework**: React with TypeScript, bundled with Vite.
- **Styling**: Tailwind CSS with custom dark-mode theme tailored for cybersecurity emergency response:
  - Deep obsidian backgrounds (`#0B0F17`, `#111827`)
  - Accent emerald (`#10B981`) for verified provenance
  - Amber/Rose (`#F59E0B` / `#EF4444`) for critical severity and compromise alerts
  - Slate glassmorphism (`backdrop-blur-md bg-slate-900/60 border border-slate-800`)
- **State Management**: React state + custom API client hooks with explicit status modeling (`idle`, `loading`, `success`, `error`).
- **Component Hierarchy**:
  - `App.tsx`: Navigation and global notification provider
  - `components/CaseHeader.tsx`: Case status, timestamp, emergency hotline quick-access (1930)
  - `components/EvidenceUploader.tsx`: Drag-and-drop file upload with live preview and MIME validation
  - `components/IncidentSummaryCard.tsx`: AI narrative, scam classification, financial loss display
  - `components/IndicatorsTable.tsx`: Extracted entities with clickable provenance chips
  - `components/CompromiseMatrix.tsx`: Banking, PII, device risk levels with recommended immediate containment
  - `components/ResponsePackages.tsx`: Bank Dispute & NCRP draft preview, edit modal, and explicit HITL approval flow
  - `components/AudioEvidencePlayer.tsx`: Audio transcription player with timestamped evidence quotes

---

## 8. Backend Architecture

- **Framework**: Python 3.10+ with FastAPI.
- **Directory Structure**:
  ```text
  backend/
  ├── app/
  │   ├── api/
  │   │   ├── deps.py             # Database session and provider dependencies
  │   │   ├── router.py           # Master API router
  │   │   └── v1/
  │   │       ├── cases.py        # Case lifecycle endpoints
  │   │       ├── evidence.py     # Evidence upload and retrieval
  │   │       ├── analysis.py     # Trigger AI incident reconstruction
  │   │       ├── passport.py     # Case passport retrieval
  │   │       ├── reports.py      # Response package generation & HITL actions
  │   │       └── dispatch.py     # Email & PDF dispatch execution
  │   ├── core/
  │   │   ├── config.py           # Environment variables (Pydantic BaseSettings)
  │   │   ├── database.py         # SQLAlchemy engine and session factory
  │   │   └── security.py         # Input sanitization and token utilities
  │   ├── models/                 # SQLAlchemy ORM models
  │   │   ├── case.py
  │   │   ├── evidence.py
  │   │   ├── indicator.py
  │   │   ├── timeline.py
  │   │   ├── compromise.py
  │   │   └── report.py
  │   ├── schemas/                # Pydantic validation schemas
  │   │   ├── case.py
  │   │   ├── evidence.py
  │   │   ├── ai_output.py
  │   │   └── report.py
  │   ├── services/
  │   │   ├── ai/
  │   │   │   ├── base.py         # AIProvider abstract base class
  │   │   │   ├── gemini.py       # Google Gemini 1.5/2.0 API implementation
  │   │   │   └── parser.py       # Robust JSON extraction & recovery parser
  │   │   ├── pdf_service.py      # ReportLab case file generator
  │   │   └── email_service.py    # Resend email dispatcher
  │   └── main.py                 # FastAPI application factory
  ├── storage/                    # Uploaded evidence files directory
  └── requirements.txt
  ```

---

## 9. AI Architecture & Provider Abstraction

The AI layer adheres to an Abstract Base Class (`AIProvider`) to prevent vendor lock-in.

```python
class AIProvider(ABC):
    @abstractmethod
    async def reconstruct_incident(self, evidence_items: List[EvidenceData]) -> IncidentReconstructionOutput:
        """Dynamically extract narrative, timeline, financial loss, and scam type."""
        pass

    @abstractmethod
    async def extract_indicators(self, evidence_items: List[EvidenceData]) -> List[ExtractedIndicator]:
        """Extract all verifiable entities with evidence provenance."""
        pass

    @abstractmethod
    async def assess_compromise(self, evidence_items: List[EvidenceData]) -> CompromiseAssessmentOutput:
        """Evaluate banking, credentials, PII, and remote access exposure."""
        pass

    @abstractmethod
    async def generate_response_packages(self, case_passport: CasePassportData) -> ResponsePackagesOutput:
        """Formulate bank dispute letters and NCRP complaint drafts."""
        pass
```

- **Default Implementation**: `GeminiProvider` using Google Gemini (via `google-genai` / REST).
- **Prompt Engineering**: Strict system prompts enforcing verifiable extraction, explicit refusal to fabricate data, and structured JSON output conforming to Pydantic schemas.

---

## 10. Multi-Agent Architecture

```text
                  ┌───────────────────────────────┐
                  │    EVIDENCE ORCHESTRATOR      │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ INCIDENT AGENT  │      │ SCAM INTEL AGENT│      │ COMPROMISE AGENT│
├─────────────────┤      ├─────────────────┤      ├─────────────────┤
│ - Chronology    │      │ - Phone numbers │      │ - Bank cards    │
│ - Financial Loss│      │ - UPI Handles   │      │ - OTP/Passwords │
│ - Tactics used  │      │ - URLs / Domains│      │ - Remote APKs   │
│ - Modus Operandi│      │ - Alias/Entity  │      │ - Identity PII  │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │    SYNTHESIS & PROVENANCE     │
                  │   Creates unified Passport    │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │    RESPONSE PACKAGE AGENT     │
                  │  Generates Bank & Cyber Drafts│
                  └───────────────────────────────┘
```

---

## 11. Evidence Architecture

Evidence items are treated as immutable forensic artifacts.
- Allowed MIME Types:
  - Images: `image/jpeg`, `image/png`, `image/webp`
  - Documents: `application/pdf`
  - Text: `text/plain`, `text/csv`
  - Audio: `audio/mpeg`, `audio/wav`, `audio/mp4`, `audio/x-m4a`
- Limits: 25MB per file maximum. Filenames sanitized via regex `[^a-zA-Z0-9_.-]`.
- Files stored on disk with cryptographic SHA-256 hash tracking to guarantee tamper-evidence.

---

## 12. Database Schema

### Table: `cases`
- `id` (VARCHAR 36, PK): UUID
- `title` (VARCHAR 255)
- `description` (TEXT)
- `status` (VARCHAR 50): `intake`, `analyzing`, `passport_ready`, `action_pending`, `resolved`
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### Table: `evidence`
- `id` (VARCHAR 36, PK): e.g. `EV-001`
- `case_id` (VARCHAR 36, FK -> `cases.id`)
- `evidence_type` (VARCHAR 50): `image`, `pdf`, `text`, `audio`
- `filename` (VARCHAR 255)
- `mime_type` (VARCHAR 100)
- `file_size` (INTEGER)
- `file_path` (VARCHAR 512)
- `raw_content` (TEXT, nullable)
- `sha256_hash` (VARCHAR 64)
- `created_at` (DATETIME)

### Table: `indicators`
- `id` (VARCHAR 36, PK)
- `case_id` (VARCHAR 36, FK -> `cases.id`)
- `indicator_type` (VARCHAR 50): `upi_id`, `phone_number`, `url`, `email`, `suspect_name`, `organization`, `account_number`, `transaction_id`
- `value` (TEXT)
- `confidence` (VARCHAR 20): `high`, `medium`, `low`
- `verification_status` (VARCHAR 30): `supported`, `possible`, `unverified`, `not_found`
- `source_evidence_id` (VARCHAR 36, FK -> `evidence.id`)
- `source_reference` (TEXT)

### Table: `timeline_events`
- `id` (VARCHAR 36, PK)
- `case_id` (VARCHAR 36, FK -> `cases.id`)
- `timestamp_str` (VARCHAR 100)
- `event_description` (TEXT)
- `source_evidence_id` (VARCHAR 36, FK -> `evidence.id`)

### Table: `compromise_assessments`
- `id` (VARCHAR 36, PK)
- `case_id` (VARCHAR 36, FK -> `cases.id`)
- `category` (VARCHAR 50): `banking`, `credentials`, `remote_access`, `pii`
- `risk_level` (VARCHAR 20): `confirmed`, `possible`, `not_found`, `unverified`
- `details` (TEXT)
- `recommended_action` (TEXT)
- `source_evidence_id` (VARCHAR 36, FK -> `evidence.id`, nullable)

### Table: `reports`
- `id` (VARCHAR 36, PK)
- `case_id` (VARCHAR 36, FK -> `cases.id`)
- `report_type` (VARCHAR 50): `bank_dispute`, `cybercrime_complaint`, `executive_passport`
- `title` (VARCHAR 255)
- `content_markdown` (TEXT)
- `content_html` (TEXT)
- `approval_status` (VARCHAR 30): `draft`, `reviewed`, `approved`, `dispatched`
- `pdf_path` (VARCHAR 512, nullable)
- `created_at` (DATETIME)

### Table: `action_events`
- `id` (VARCHAR 36, PK)
- `case_id` (VARCHAR 36, FK -> `cases.id`)
- `action_type` (VARCHAR 50): `email_sent`, `pdf_generated`, `user_approval`
- `status` (VARCHAR 30): `success`, `failed`, `pending`
- `details` (TEXT)
- `timestamp` (DATETIME)

---

## 13. API Contracts

### Endpoints:
- `POST /api/v1/cases`: Create a new case
- `GET /api/v1/cases`: List all active cases
- `GET /api/v1/cases/{case_id}`: Fetch case details
- `POST /api/v1/cases/{case_id}/evidence`: Upload evidence file or raw text
- `GET /api/v1/cases/{case_id}/evidence`: List all evidence items
- `POST /api/v1/cases/{case_id}/analyze`: Trigger real AI multimodal incident reconstruction
- `GET /api/v1/cases/{case_id}/passport`: Retrieve unified Case Passport with provenance
- `POST /api/v1/cases/{case_id}/reports/generate`: Generate response packages (Bank Dispute, NCRP)
- `PUT /api/v1/cases/{case_id}/reports/{report_id}/approve`: Record explicit human approval
- `POST /api/v1/cases/{case_id}/reports/{report_id}/pdf`: Generate verified ReportLab PDF
- `POST /api/v1/cases/{case_id}/reports/{report_id}/send-email`: Send approved email via Resend

---

## 14. AI JSON Schemas

All LLM completions are parsed into and validated by Pydantic models:

```python
class IncidentReconstructionOutput(BaseModel):
    summary: str
    incident_type: str
    scam_category: str
    severity_level: Literal["critical", "high", "medium", "low"]
    financial_loss: Optional[float] = None
    currency: Optional[str] = "INR"
    modus_operandi: str
    timeline: List[TimelineItem]
    indicators: List[ExtractedIndicator]
    compromise: List[CompromiseItem]
    recommended_immediate_actions: List[str]
```

---

## 15. Evidence Provenance Model

Every extracted entity or critical assertion MUST include:
1. `source_evidence_id`: Primary key of the originating evidence file.
2. `source_reference`: Specific citation (e.g., `"Screenshot 2, top chat bubble"`, `"Bank SMS line 2"`, `"Audio 01:23 - 01:45"`).
3. `confidence`: `high`, `medium`, `low`.
4. `verification_status`:
   - `SUPPORTED`: Explicitly stated in the evidence.
   - `POSSIBLE`: Deduced from circumstantial context.
   - `UNVERIFIED`: Claimed by scammer but unconfirmed.
   - `NOT_FOUND`: Evidence checked; element not present.

---

## 16. Call / Audio Evidence Architecture

1. Upload recorded call audio (`.mp3`, `.wav`, `.m4a`).
2. Backend speech-to-text pipeline (Whisper/Gemini Multimodal Audio).
3. Generate timestamped transcript with speaker role tagging (`Victim` vs `Impersonator/Caller`).
4. Pipe transcript to Scam Intelligence agent to extract urgency triggers, coercive language, impersonation tokens, and transaction instructions.
5. All audio-extracted indicators retain exact millisecond timestamp offsets.

---

## 17. Voice Architecture

- Bidirectional voice interface acting as an accessible interaction channel into the core orchestrator.
- Speech Input -> Speech-to-Text -> Incident Orchestrator -> Text-to-Speech Output.
- **Safety Gate**: Consequential operations (such as approving report dispatches) require clear, unambiguous verbal confirmation followed by visual screen confirmation.

---

## 18. Multilingual Architecture

- Tier 1 Languages: **English**, **Hindi (हिंदी)**, **Kannada (ಕನ್ನಡ)**.
- Unified key-value i18n localization dictionary on the frontend.
- Backend prompts include target language instructions to generate culturally precise reports and victim advisories without duplicating orchestration code.

---

## 19. Report / PDF Architecture

- Built using Python's `reportlab` library.
- Formats structured case data into an authoritative, clean forensic document:
  - Header: Case ID, Incident Timestamp, Threat Level
  - Executive Incident Chronology
  - Forensic Indicators & Evidence Provenance Table
  - Compromise Assessment & Urgent Remediation Measures
  - Bank Formal Dispute Declaration (with statutory RBI circular reference)

---

## 20. Email Architecture

- Modular `EmailService` with `ResendEmailService` implementation.
- Configuration:
  - `EMAIL_PROVIDER`: `resend` or `smtp`
  - `RESEND_API_KEY`: API key from environment
  - `DEMO_RECIPIENT_EMAIL`: Configurable recipient email for hackathon demonstration
- Hard requirements: Validates case existence, report generation status, and explicit user approval before network transmission. Logs transaction ID or returns clear configuration error if unconfigured.

---

## 21. Human-in-the-Loop (HITL) Approval Workflow

```text
[Generated Draft] ──> [Victim Review Screen] ──> [Inline Victim Edits]
                                                        │
                                                        ▼
[Action Blocked] <── [Cancel / Revoke] ── [Explicit Approve Button]
                                                        │
                                                        ▼
                                             [Approved Action Executed]
```
The UI maintains unambiguous visual indicators:
- `DRAFT`: Gray badge, actions locked.
- `APPROVED`: Emerald badge with timestamp and approver audit log.
- `DISPATCHED`: Blue badge with delivery receipt ID.

---

## 22. Error Handling & Resilience

- **AI Unavailability / Quota Exhaustion**: Returns HTTP 503 with user-friendly diagnosis: *"AI analysis service temporarily unavailable. Please verify API key configuration."*
- **Malformed AI Response**: Automatic JSON repair attempt; if unrecoverable, logs raw payload and raises validation error.
- **File Validation**: Rejects files exceeding 25MB or with unapproved MIME types with HTTP 415 / 400.
- **Zero Silent Failure**: Frontend displays distinct error banners with recovery suggestions.
