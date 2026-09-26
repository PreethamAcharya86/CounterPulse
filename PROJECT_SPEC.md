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
│  │  ├───────────────────┤  │  │  - File Storage (Local Secure Store) │  │
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

---

## 23. Security Considerations

- API keys stored strictly in `.env` and accessed through server-side configuration.
- Files stored with randomized GUID filenames to prevent path traversal.
- Uploaded files checked for executable extensions.
- Database access managed via parameterized SQLAlchemy queries to eliminate SQL injection.

---

## 24. Testing Strategy

- **Unit Tests**: Schema validation, provenance mapping, PDF generation, email provider fallback.
- **Integration Tests**: FastAPI TestClient tests covering:
  - Case creation (`POST /api/v1/cases`)
  - Evidence upload and SHA-256 verification (`POST /api/v1/cases/{id}/evidence`)
  - AI analysis execution and structured schema validation
  - Passport compilation (`GET /api/v1/cases/{id}/passport`)
  - Human approval state transitions
- **Automated Test Runner**: `pytest tests/`

---

## 25. Six-Person Development Split

| Laptop / Stream | Primary Responsibility | Dedicated Directory / Modules | Interfaces Owned |
| :--- | :--- | :--- | :--- |
| **LAPTOP 1** | **Core Architecture, Backend Foundation & Integration** | `backend/app/core/`, `backend/app/main.py`, `PROJECT_SPEC.md` | Case models, API Router, Provider Interface |
| **LAPTOP 2** | **Evidence Ingestion & Processing** | `backend/app/api/v1/evidence.py`, `frontend/src/components/EvidenceUploader.tsx` | Multipart upload, OCR, Audio parser |
| **LAPTOP 3** | **AI Orchestration & Scam Intelligence** | `backend/app/services/ai/`, `agents/` | Multi-agent coordination, entity extraction |
| **LAPTOP 4** | **Case Passport, Reports & PDF Engine** | `backend/app/services/pdf_service.py`, `frontend/src/components/CasePassport.tsx` | ReportLab generator, NCRP & Bank templates |
| **LAPTOP 5** | **Voice Assistant & Multilingual Localization** | `frontend/src/i18n/`, `backend/app/services/voice/` | Kannada/Hindi i18n, WebSpeech / Audio API |
| **LAPTOP 6** | **Email Dispatch, QA & Integration Testing** | `backend/app/services/email_service.py`, `tests/` | Resend API, automated test suite, demo scripts |

---

## 26. Git & Branching Strategy

- **Main Branch**: `main` (always deployable, protected).
- **Stream Branches**:
  - `feature/laptop-1-core-foundation`
  - `feature/laptop-2-evidence-ingestion`
  - `feature/laptop-3-ai-agents`
  - `feature/laptop-4-passport-pdf`
  - `feature/laptop-5-voice-multilingual`
  - `feature/laptop-6-email-testing`
- **Rule**: Never push broken code to `main`. Merge through PR or verified fast-forward integration after automated tests pass.

---

## 27. Integration Strategy

1. **Phase 1 (Laptop 1 - Completed First)**: Establish runnable FastAPI backend, SQLite database, Pydantic schemas, UI skeleton, and end-to-end vertical slice.
2. **Phase 2 (Laptops 2, 3, 4)**: Branch off `main`; build against frozen API contracts and database schema.
3. **Phase 3 (Laptops 5, 6)**: Integrate voice layer, email provider, and end-to-end automated test suites.
4. **Phase 4**: Final integration pass and demo rehearsal.

---

## 28. Demo Scenario: "Digital Arrest & Impersonation Scam"

- **Context**: Victim receives a call from someone claiming to be a CBI/TRAI officer stating their Aadhaar was used to register 14 illegal SIMs and an arrest warrant is pending.
- **Evidence Uploaded**:
  1. Screenshot of fake Supreme Court arrest warrant PDF.
  2. WhatsApp chat snippet with extortion demands and payment QR / UPI handle.
  3. Bank SMS showing unauthorized IMPS debit of ₹85,000.
- **Dynamic Output**:
  - Scam Category: *Digital Arrest / Law Enforcement Impersonation*
  - Extracted Financial Loss: *₹85,000 INR*
  - Provenance: Linked directly to Bank SMS and WhatsApp evidence items.
  - Compromise: Confirmed Aadhaar exposure, Possible Banking credentials leak.
  - Action Package: Real PDF generated for 1930 Cyber Crime submission + Bank dispute email prepared for victim approval.

---

## 29. Hackathon Architecture Explanation

*(Suitable for submission documentation and judges presentation)*

CounterPulse AI pioneers an **Evidence-First Agentic Architecture** tailored for high-stakes cybersecurity emergencies. Unlike conversational chatbots that produce unstructured advice, CounterPulse treats every piece of user-submitted media as raw forensic evidence. The Evidence Orchestrator normalizes these inputs and activates specialized agents that independently extract temporal milestones, financial indicators, and vulnerability vectors. Crucially, each finding maintains an immutable provenance link back to the source media. The resulting Fraud Case Passport feeds into a deterministic response engine that compiles formal bank and law enforcement dossiers, while enforcing strict Human-in-the-Loop safeguards prior to external dispatch.

---

## 30. Hackathon Approach & Methodology

1. **Evidence-First Incident Reconstruction**: Every conclusion is grounded in verifiable evidence bytes.
2. **Specialized Agent Orchestration**: Modular division of analytical tasks to maximize accuracy and minimize hallucinations.
3. **Strict Structured Outputs**: 100% Pydantic-validated JSON interfaces.
4. **Auditable Provenance**: Complete traceability for legal compliance.
5. **Human-in-the-Loop Safety**: Zero autonomous consequential actions.
6. **Accessible Multimodal Interaction**: Support for text, images, documents, audio, and localized voice.

| Capability | Status in Current Release | Planned Next Phase |
| :--- | :--- | :--- |
| Core FastAPI + SQLite Backend | **IMPLEMENTED** | PostgreSQL / Supabase migration |
| Real AI Multimodal Reconstruction | **IMPLEMENTED** | Multi-model consensus voting |
| Evidence Provenance Tracking | **IMPLEMENTED** | Cryptographic block-stamping |
| ReportLab PDF Dossier Generation | **IMPLEMENTED** | Custom bank-specific PDF layouts |
| Human Approval State Machine | **IMPLEMENTED** | Multi-signatory workflow |
| Live Email Dispatch via Resend | **IMPLEMENTED** | Direct 1930 portal API webhook |
| Real-time Gemini Live Voice | **PLANNED** | Full duplex low-latency voice |

---

## 31. Definition of Done (DoD)

- [x] Repository inspected and initialized
- [x] `PROJECT_SPEC.md` created and approved as source of truth
- [x] Backend architecture (FastAPI, SQLAlchemy, Pydantic) established
- [x] Database models with relationships created and migrations ready
- [x] AI Provider abstraction with structured validation implemented
- [x] Evidence provenance tracking model fully functional
- [x] Frontend created with premium dark security aesthetics and zero fake UI
- [x] Real vertical slice (Upload -> Real AI Analysis -> DB Persistence -> UI Display) verified
- [x] Comprehensive test suite written and passing
- [x] Six-laptop development split clearly documented
- [x] Complete README with setup and execution instructions provided
