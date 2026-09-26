export type SupportedLanguage = "en" | "hi" | "kn";

export interface TranslationDictionary {
  // Header & Brand
  brand: string;
  brandSubtitle: string;
  brandTagline: string;
  helpline: string;
  helplineTitle: string;
  noCases: string;
  createNewCase: string;
  cancel: string;
  create: string;
  active: string;
  caseUuid: string;
  goldenHourActive: string;
  evidencePipelineReady: string;
  ocrEngine: string;
  selectLanguage: string;
  syntheticDemoBtn: string;
  syntheticDemoLoading: string;
  syntheticDemoSuccess: string;
  footerText: string;
  noCaseSelectedTitle: string;
  noCaseSelectedDesc: string;
  createIncidentCase: string;
  modalCreateTitle: string;
  modalTitlePlaceholder: string;

  // Tabs
  tabEvidence: string;
  tabPassport: string;
  tabReports: string;
  tabScamIntel: string;
  tabCallLog: string;
  tabVoice: string;

  // Voice Console
  voiceBannerTitle: string;
  voiceBannerDesc: string;
  voiceSafetyRule: string;
  voiceListening: string;
  voiceProcessing: string;
  voiceResponding: string;
  voiceDisconnected: string;
  voiceError: string;
  voiceIdle: string;
  voiceStartListening: string;
  voiceStopListening: string;
  voiceSupportedCommands: string;
  voiceInputPlaceholder: string;
  voiceConfirmCardTitle: string;
  voiceConfirmBtn: string;
  voiceCancelBtn: string;
  voicePendingSendPrefix: string;

  // Case Passport
  passportTitle: string;
  passportSubtitle: string;
  downloadPdf: string;
  generatingPdf: string;
  runAnalysis: string;
  analysisRunning: string;
  caseNotAnalyzedTitle: string;
  caseNotAnalyzedDesc: string;
  summaryCard: string;
  financialLoss: string;
  severityLevel: string;
  scamCategory: string;
  compromiseAssessment: string;
  indicatorsOfCompromise: string;
  incidentTimeline: string;
  evidenceVaultSection: string;

  // Response Center / Reports
  responseCenterTitle: string;
  responseCenterSubtitle: string;
  cybercrimeComplaint: string;
  bankDispute: string;
  securityAdvisory: string;
  editReport: string;
  saveReport: string;
  approveReport: string;
  approvedBadge: string;
  sendReport: string;
  sendingReport: string;
  dispatchedBadge: string;
  recipientEmail: string;
  subjectLine: string;
  auditLogTitle: string;

  // Scam Intelligence
  scamIntelTitle: string;
  scamIntelSubtitle: string;
  startControlledCall: string;
  extractIntel: string;
  addToVault: string;
  addedToVaultBadge: string;
  impersonationDetails: string;
  psychologicalTactics: string;
  extractedUpi: string;
  extractedPhones: string;
  extractedUrls: string;
  unverifiedDisclaimer: string;
}

export const translations: Record<SupportedLanguage, TranslationDictionary> = {
  en: {
    brand: "COUNTERPULSE",
    brandSubtitle: "AI FORENSICS",
    brandTagline: "Turn panic into an actionable fraud case",
    helpline: "Helpline 1930",
    helplineTitle: "Official National Cyber Crime Reporting Portal Helpline (1930)",
    noCases: "No cases",
    createNewCase: "Create New Case",
    cancel: "Cancel",
    create: "Create Case",
    active: "ACTIVE",
    caseUuid: "CASE UUID",
    goldenHourActive: "Golden Hour Response Window Active",
    evidencePipelineReady: "Evidence Pipeline: Ready",
    ocrEngine: "OCR: RapidOCR ONNX",
    selectLanguage: "Language",
    syntheticDemoBtn: "⚡ Load Demo Case",
    syntheticDemoLoading: "Initializing Demo Case...",
    syntheticDemoSuccess: "Demo Case Created & Analyzed",
    footerText: "CounterPulse AI — Team: The Valiente | Track: Agentic AI For Billions | Zero-Fake Evidence Provenance",
    noCaseSelectedTitle: "No Incident Case Selected",
    noCaseSelectedDesc: "Create a new fraud incident case from real complaint details to begin evidence intake and multimodal forensic analysis.",
    createIncidentCase: "Create Incident Case",
    modalCreateTitle: "Create New Fraud Incident Case",
    modalTitlePlaceholder: "e.g. Telegram Job Scam - ₹1,20,000 Loss",

    tabEvidence: "Evidence Intake & Vault",
    tabPassport: "Fraud Case Passport & Dossier",
    tabReports: "Response Center & Dispatch",
    tabScamIntel: "Scam Intelligence",
    tabCallLog: "Live Call Log",
    tabVoice: "Voice Control",

    voiceBannerTitle: "Gemini Live Voice Control Console",
    voiceBannerDesc: "Real-time voice controller over case reconstruction, compromise assessment, and dispute reports.",
    voiceSafetyRule: "Strict safety rule: Voice commands cannot bypass human approval for consequential email dispatch.",
    voiceListening: "LISTENING",
    voiceProcessing: "PROCESSING",
    voiceResponding: "RESPONDING",
    voiceDisconnected: "DISCONNECTED",
    voiceError: "ERROR",
    voiceIdle: "IDLE",
    voiceStartListening: "Start Voice Input",
    voiceStopListening: "Stop Listening",
    voiceSupportedCommands: "Supported Voice Commands",
    voiceInputPlaceholder: "Or type a voice command e.g. 'Analyze this case', 'What happened?', 'Send complaint email'...",
    voiceConfirmCardTitle: "Confirmation Required Before Consequential Dispatch",
    voiceConfirmBtn: "Yes, Confirm & Send",
    voiceCancelBtn: "No, Cancel",
    voicePendingSendPrefix: "The system is ready to transmit",

    passportTitle: "Fraud Case Passport",
    passportSubtitle: "Deterministic Incident Dossier & Provenance Chain",
    downloadPdf: "Download PDF Dossier",
    generatingPdf: "Generating PDF...",
    runAnalysis: "Analyze Incident",
    analysisRunning: "AI Pipeline Running...",
    caseNotAnalyzedTitle: "Incident Not Analyzed Yet",
    caseNotAnalyzedDesc: "Upload evidence and run the AI analysis pipeline to construct the Fraud Case Passport.",
    summaryCard: "Executive Summary",
    financialLoss: "Financial Loss",
    severityLevel: "Severity Level",
    scamCategory: "Scam Category",
    compromiseAssessment: "Compromise Assessment",
    indicatorsOfCompromise: "Extracted Indicators",
    incidentTimeline: "Incident Timeline",
    evidenceVaultSection: "Forensic Evidence Chain",

    responseCenterTitle: "Response Center & Action Dispatch",
    responseCenterSubtitle: "Actionable dispute letters, police complaints, and emergency containment",
    cybercrimeComplaint: "Cybercrime Complaint",
    bankDispute: "Bank Dispute Letter",
    securityAdvisory: "Emergency Security Advisory",
    editReport: "Edit Draft",
    saveReport: "Save Changes",
    approveReport: "Approve for Dispatch",
    approvedBadge: "APPROVED",
    sendReport: "Send Email",
    sendingReport: "Sending...",
    dispatchedBadge: "DISPATCHED",
    recipientEmail: "Recipient Email",
    subjectLine: "Subject Line",
    auditLogTitle: "Action Audit Trail",

    scamIntelTitle: "Controlled Scam Conversation & Intelligence",
    scamIntelSubtitle: "Active counter-intelligence extraction from scammer interaction",
    startControlledCall: "Start Controlled Conversation",
    extractIntel: "Extract Intelligence",
    addToVault: "Add to Case Vault",
    addedToVaultBadge: "Added to Case Vault",
    impersonationDetails: "Impersonation Details",
    psychologicalTactics: "Psychological Tactics",
    extractedUpi: "Extracted UPI IDs",
    extractedPhones: "Extracted Phone Numbers",
    extractedUrls: "Extracted Phishing Links",
    unverifiedDisclaimer: "Note: Indicators are marked UNVERIFIED until forensic correlation is established.",
  },

  hi: {
    brand: "काउंटरपल्स",
    brandSubtitle: "एआई फोरेंसिक्स",
    brandTagline: "घबराहट को एक ठोस साइबर धोखाधड़ी मामले में बदलें",
    helpline: "हेल्पलाइन 1930",
    helplineTitle: "आधिकारिक राष्ट्रीय साइबर अपराध रिपोर्टिंग पोर्टल हेल्पलाइन (1930)",
    noCases: "कोई मामला नहीं",
    createNewCase: "नया मामला दर्ज करें",
    cancel: "रद्द करें",
    create: "मामला बनाएं",
    active: "सक्रिय",
    caseUuid: "मामला UUID",
    goldenHourActive: "गोल्डन आवर त्वरित प्रतिक्रिया अवधि सक्रिय",
    evidencePipelineReady: "सबूत पाइपलाइन: तैयार",
    ocrEngine: "ओसीआर: RapidOCR ONNX",
    selectLanguage: "भाषा",
    syntheticDemoBtn: "⚡ डेमो मामला लोड करें",
    syntheticDemoLoading: "डेमो मामला तैयार हो रहा है...",
    syntheticDemoSuccess: "डेमो मामला बनाया और विश्लेषित किया गया",
    footerText: "काउंटरपल्स एआई — टीम: द वैलेंटे | ट्रैक: अरबों के लिए एजेंटिक एआई | शून्य-नकली साक्ष्य प्रमाण",
    noCaseSelectedTitle: "कोई मामला चयनित नहीं है",
    noCaseSelectedDesc: "सबूत संग्रह और बहुविध फोरेंसिक विश्लेषण शुरू करने के लिए शिकायत विवरण से नया धोखाधड़ी मामला बनाएं।",
    createIncidentCase: "मामला शुरू करें",
    modalCreateTitle: "नया साइबर धोखाधड़ी मामला बनाएं",
    modalTitlePlaceholder: "उदा. टेलीग्राम जॉब स्कैम - ₹1,20,000 की हानि",

    tabEvidence: "सबूत सेवन और वॉल्ट",
    tabPassport: "धोखाधड़ी केस पासपोर्ट व डोजियर",
    tabReports: "प्रतिक्रिया केंद्र और प्रेषण",
    tabScamIntel: "स्कैम इंटेलिजेंस",
    tabCallLog: "लाइव कॉल लॉग",
    tabVoice: "वॉयस कंट्रोल",

    voiceBannerTitle: "जेमिनी लाइव वॉयस कंट्रोल कंसोल",
    voiceBannerDesc: "घटना पुनर्निर्माण, समझौता मूल्यांकन और विवाद रिपोर्ट के लिए रीयल-टाइम वॉयस नियंत्रक।",
    voiceSafetyRule: "सख्त सुरक्षा नियम: वॉयस कमांड परिणामी ईमेल प्रेषण के लिए मानवीय अनुमोदन को बायपास नहीं कर सकते।",
    voiceListening: "सुन रहा है",
    voiceProcessing: "प्रसंस्करण जारी",
    voiceResponding: "उत्तर दे रहा है",
    voiceDisconnected: "डिस्कनेक्ट हुआ",
    voiceError: "त्रुटि",
    voiceIdle: "निष्क्रिय",
    voiceStartListening: "आवाज से बोलें",
    voiceStopListening: "सुनना बंद करें",
    voiceSupportedCommands: "समर्थित वॉयस कमांड",
    voiceInputPlaceholder: "या वॉयस कमांड टाइप करें जैसे 'इस मामले का विश्लेषण करें', 'क्या हुआ?', 'शिकायत ईमेल भेजें'...",
    voiceConfirmCardTitle: "ईमेल भेजने से पहले मानवीय पुष्टि आवश्यक है",
    voiceConfirmBtn: "हाँ, पुष्टि करें और भेजें",
    voiceCancelBtn: "नहीं, रद्द करें",
    voicePendingSendPrefix: "सिस्टम रिपोर्ट भेजने के लिए तैयार है",

    passportTitle: "धोखाधड़ी केस पासपोर्ट",
    passportSubtitle: "घटना डोजियर और सबूत प्रामाणिकता श्रृंखला",
    downloadPdf: "पीडीएफ डोजियर डाउनलोड करें",
    generatingPdf: "पीडीएफ बन रहा है...",
    runAnalysis: "घटना का विश्लेषण करें",
    analysisRunning: "एआई विश्लेषण जारी है...",
    caseNotAnalyzedTitle: "घटना का विश्लेषण अभी नहीं हुआ है",
    caseNotAnalyzedDesc: "केस पासपोर्ट तैयार करने के लिए सबूत अपलोड करें और एआई विश्लेषण चलाएं।",
    summaryCard: "कार्यकारी सारांश",
    financialLoss: "वित्तीय नुकसान",
    severityLevel: "गंभीरता स्तर",
    scamCategory: "धोखाधड़ी की श्रेणी",
    compromiseAssessment: "समझौता मूल्यांकन",
    indicatorsOfCompromise: "निकाले गए संकेतक",
    incidentTimeline: "घटना समयरेखा",
    evidenceVaultSection: "फोरेंसिक साक्ष्य श्रृंखला",

    responseCenterTitle: "प्रतिक्रिया केंद्र और प्रेषण",
    responseCenterSubtitle: "बैंक विवाद पत्र, पुलिस शिकायतें और आपातकालीन रोकथाम",
    cybercrimeComplaint: "साइबर अपराध शिकायत",
    bankDispute: "बैंक विवाद पत्र",
    securityAdvisory: "आपातकालीन सुरक्षा सलाह",
    editReport: "प्रारूप संपादित करें",
    saveReport: "बदलाव सहेजें",
    approveReport: "प्रेषण के लिए स्वीकृत करें",
    approvedBadge: "स्वीकृत",
    sendReport: "ईमेल भेजें",
    sendingReport: "भेज रहा है...",
    dispatchedBadge: "भेजा गया",
    recipientEmail: "प्राप्तकर्ता ईमेल",
    subjectLine: "विषय",
    auditLogTitle: "कार्रवाई ऑडिट ट्रेल",

    scamIntelTitle: "नियंत्रित स्कैम बातचीत और खुफिया जानकारी",
    scamIntelSubtitle: "धोखेबाजों से बातचीत से काउंटर-इंटेलिजेंस निष्कर्षण",
    startControlledCall: "नियंत्रित बातचीत शुरू करें",
    extractIntel: "खुफिया जानकारी निकालें",
    addToVault: "केस वॉल्ट में जोड़ें",
    addedToVaultBadge: "केस वॉल्ट में जोड़ा गया",
    impersonationDetails: "प्रतिरूपण विवरण",
    psychologicalTactics: "मनोवैज्ञानिक रणनीतियाँ",
    extractedUpi: "निकाले गए यूपीआई आईडी",
    extractedPhones: "निकाले गए फोन नंबर",
    extractedUrls: "निकाले गए फिशिंग लिंक",
    unverifiedDisclaimer: "नोट: संकेतक तब तक असत्यापित रहते हैं जब तक फोरेंसिक पुष्टि न हो।",
  },

  kn: {
    brand: "ಕೌಂಟರ್‌ಪಲ್ಸ್",
    brandSubtitle: "ಎಐ ಫೊರೆನ್ಸಿಕ್ಸ್",
    brandTagline: "ಆತಂಕವನ್ನು ಅಧಿಕೃತ ಸೈಬರ್ ವಂಚನೆ ಪ್ರಕರಣವನ್ನಾಗಿ ಪರಿವರ್ತಿಸಿ",
    helpline: "ಸಹಾಯವಾಣಿ 1930",
    helplineTitle: "ಅಧಿಕೃತ ರಾಷ್ಟ್ರೀಯ ಸೈಬರ್ ಕ್ರೈಮ್ ವರದಿ ಪೋರ್ಟಲ್ ಸಹಾಯವಾಣಿ (1930)",
    noCases: "ಪ್ರಕರಣಗಳಿಲ್ಲ",
    createNewCase: "ಹೊಸ ಪ್ರಕರಣ ದಾಖಲಿಸಿ",
    cancel: "ರದ್ದುಮಾಡಿ",
    create: "ಪ್ರಕರಣ ರಚಿಸಿ",
    active: "ಸಕ್ರಿಯ",
    caseUuid: "ಪ್ರಕರಣ UUID",
    goldenHourActive: "ಗೋಲ್ಡನ್ ಅವರ್ ತ್ವರಿತ ಪ್ರತಿಕ್ರಿಯಾ ಅವಧಿ ಸಕ್ರಿಯ",
    evidencePipelineReady: "ಸಾಕ್ಷ್ಯ ಪೈಪ್‌ಲೈನ್: ಸಿದ್ಧ",
    ocrEngine: "ಒಸಿಆರ್: RapidOCR ONNX",
    selectLanguage: "ಭಾಷೆ",
    syntheticDemoBtn: "⚡ ಡೆಮೊ ಪ್ರಕರಣ ಲೋಡ್ ಮಾಡಿ",
    syntheticDemoLoading: "ಡೆಮೊ ಪ್ರಕರಣ ಸಿದ್ಧವಾಗುತ್ತಿದೆ...",
    syntheticDemoSuccess: "ಡೆಮೊ ಪ್ರಕರಣ ರಚಿಸಲಾಗಿದೆ ಮತ್ತು ವಿಶ್ಲೇಷಿಸಲಾಗಿದೆ",
    footerText: "ಕೌಂಟರ್‌ಪಲ್ಸ್ ಎಐ — ತಂಡ: ದ ವ್ಯಾಲಿಯೆಂಟೆ | ಟ್ರ್ಯಾಕ್: ಕೋಟ್ಯಂತರ ಜನರಿಗೆ ಏಜೆಂಟಿಕ್ ಎಐ | ಶೂನ್ಯ-ನಕಲಿ ಸಾಕ್ಷ್ಯಾಧಾರ",
    noCaseSelectedTitle: "ಯಾವುದೇ ಪ್ರಕರಣವನ್ನು ಆಯ್ಕೆ ಮಾಡಿಲ್ಲ",
    noCaseSelectedDesc: "ಸಾಕ್ಷ್ಯ ಸಂಗ್ರಹಣೆ ಮತ್ತು ಬಹುಮಾದರಿ ಫೋರೆನ್ಸಿಕ್ ವಿಶ್ಲೇಷಣೆ ಆರಂಭಿಸಲು ದೂರಿನ ವಿವರಗಳಿಂದ ಹೊಸ ವಂಚನೆ ಪ್ರಕರಣ ರಚಿಸಿ.",
    createIncidentCase: "ಪ್ರಕರಣ ರಚಿಸಿ",
    modalCreateTitle: "ಹೊಸ ಸೈಬರ್ ವಂಚನೆ ಪ್ರಕರಣ ರಚಿಸಿ",
    modalTitlePlaceholder: "ಉದಾ. ಟೆಲಿಗ್ರಾಂ ಜಾಬ್ ಸ್ಕ್ಯಾಮ್ - ₹1,20,000 ನಷ್ಟ",

    tabEvidence: "ಸಾಕ್ಷ್ಯ ಸ್ವೀಕಾರ ಮತ್ತು ವಾಲ್ಟ್",
    tabPassport: "ವಂಚನೆ ಪ್ರಕರಣ ಪಾಸ್‌ಪೋರ್ಟ್ & ಡಾಸಿಯರ್",
    tabReports: "ಪ್ರತಿಕ್ರಿಯಾ ಕೇಂದ್ರ ಮತ್ತು ರವಾನೆ",
    tabScamIntel: "ಸ್ಕ್ಯಾಮ್ ಇಂಟೆಲಿಜೆನ್ಸ್",
    tabCallLog: "ಲೈವ್ ಕರೆ ದಾಖಲೆ",
    tabVoice: "ಧ್ವನಿ ನಿಯಂತ್ರಣ",

    voiceBannerTitle: "ಜೆಮಿನಿ ಲೈವ್ ಧ್ವನಿ ನಿಯಂತ್ರಣ ಕನ್ಸೋಲ್",
    voiceBannerDesc: "ಘಟನೆ ಪುನರ್ನಿರ್ಮಾಣ, ರಾಜಿ ಮೌಲ್ಯಮಾಪನ ಮತ್ತು ವಿವಾದ ವರದಿಗಳ ನೈಜ-ಸಮಯದ ಧ್ವನಿ ನಿಯಂತ್ರಕ.",
    voiceSafetyRule: "ಕಟ್ಟುನಿಟ್ಟಾದ ಭದ್ರತಾ ನಿಯಮ: ಧ್ವನಿ ಆದೇಶಗಳು ಅಧಿಕೃತ ಇಮೇಲ್ ರವಾನೆಗೆ ಮಾನವ ಅನುಮೋದನೆಯನ್ನು ಬೈಪಾಸ್ ಮಾಡಲು ಸಾಧ್ಯವಿಲ್ಲ.",
    voiceListening: "ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದೆ",
    voiceProcessing: "ಸಂಸ್ಕರಿಸಲಾಗುತ್ತಿದೆ",
    voiceResponding: "ಉತ್ತರಿಸುತ್ತಿದೆ",
    voiceDisconnected: "ಸಂಪರ್ಕ ಕಡಿತಗೊಂಡಿದೆ",
    voiceError: "ದೋಷ",
    voiceIdle: "ನಿಷ್ಕ್ರಿಯ",
    voiceStartListening: "ಧ್ವನಿ ಪ್ರಾರಂಭಿಸಿ",
    voiceStopListening: "ನಿಲ್ಲಿಸಿ",
    voiceSupportedCommands: "ಬೆಂಬಲಿತ ಧ್ವನಿ ಆದೇಶಗಳು",
    voiceInputPlaceholder: "ಅಥವಾ ಆದೇಶ ಟೈಪ್ ಮಾಡಿ ಉದಾ. 'ಈ ಪ್ರಕರಣ ವಿಶ್ಲೇಷಿಸಿ', 'ಏನಾಯಿತು?', 'ದೂರು ಇಮೇಲ್ ಕಳುಹಿಸಿ'...",
    voiceConfirmCardTitle: "ರವಾನಿಸುವ ಮುನ್ನ ಮಾನವ ಅನುಮೋದನೆ ಅಗತ್ಯವಿದೆ",
    voiceConfirmBtn: "ಹೌದು, ದೃಢೀಕರಿಸಿ ಕಳುಹಿಸಿ",
    voiceCancelBtn: "ಬೇಡ, ರದ್ದುಮಾಡಿ",
    voicePendingSendPrefix: "ಸಿಸ್ಟಮ್ ವರದಿ ರವಾನಿಸಲು ಸಿದ್ಧವಾಗಿದೆ",

    passportTitle: "ವಂಚನೆ ಪ್ರಕರಣ ಪಾಸ್‌ಪೋರ್ಟ್",
    passportSubtitle: "ಘಟನೆಯ ಡಾಸಿಯರ್ ಮತ್ತು ಸಾಕ್ಷ್ಯ ನಿಖರತೆಯ ಸರಣಿ",
    downloadPdf: "ಪಿಡಿಎಫ್ ಡಾಸಿಯರ್ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ",
    generatingPdf: "ಪಿಡಿಎಫ್ ರಚಿಸಲಾಗುತ್ತಿದೆ...",
    runAnalysis: "ಘಟನೆ ವಿಶ್ಲೇಷಿಸಿ",
    analysisRunning: "ಎಐ ವಿಶ್ಲೇಷಣೆ ಪ್ರಗತಿಯಲ್ಲಿದೆ...",
    caseNotAnalyzedTitle: "ಘಟನೆಯನ್ನು ಇನ್ನೂ ವಿಶ್ಲೇಷಿಸಿಲ್ಲ",
    caseNotAnalyzedDesc: "ಕೇಸ್ ಪಾಸ್‌ಪೋರ್ಟ್ ಸಿದ್ಧಪಡಿಸಲು ಸಾಕ್ಷ್ಯವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ ಮತ್ತು ಎಐ ವಿಶ್ಲೇಷಣೆಯನ್ನು ಚಲಾಯಿಸಿ.",
    summaryCard: "ಕಾರ್ಯನಿರ್ವಾಹಕ ಸಾರಾಂಶ",
    financialLoss: "ಹಣಕಾಸಿನ ನಷ್ಟ",
    severityLevel: "ಗಂಭೀರತೆ ಮಟ್ಟ",
    scamCategory: "ವಂಚನೆ ವರ್ಗ",
    compromiseAssessment: "ರಾಜಿ ಮೌಲ್ಯಮಾಪನ",
    indicatorsOfCompromise: "ಹೊರತೆಗೆದ ಸೂಚಕಗಳು",
    incidentTimeline: "ಘಟನೆಯ ಕಾಲಾನುಕ್ರಮ",
    evidenceVaultSection: "ಫೋರೆನ್ಸಿಕ್ ಸಾಕ್ಷ್ಯ ಸರಣಿ",

    responseCenterTitle: "ಪ್ರತಿಕ್ರಿಯಾ ಕೇಂದ್ರ ಮತ್ತು ರವಾನೆ",
    responseCenterSubtitle: "ಬ್ಯಾಂಕ್ ವಿವಾದ ಪತ್ರಗಳು, ಪೊಲೀಸ್ ದೂರುಗಳು ಮತ್ತು ತುರ್ತು ಸುರಕ್ಷತಾ ಕ್ರಮಗಳು",
    cybercrimeComplaint: "ಸೈಬರ್ ಕ್ರೈಮ್ ದೂರು",
    bankDispute: "ಬ್ಯಾಂಕ್ ವಿವಾದ ಪತ್ರ",
    securityAdvisory: "ತುರ್ತು ಭದ್ರತಾ ಸಲಹೆ",
    editReport: "ಕರಡು ಸಂಪಾದಿಸಿ",
    saveReport: "ಉಳಿಸಿ",
    approveReport: "ರವಾನೆಗೆ ಅನುಮೋದಿಸಿ",
    approvedBadge: "ಅನುಮೋದಿಸಲಾಗಿದೆ",
    sendReport: "ಇಮೇಲ್ ಕಳುಹಿಸಿ",
    sendingReport: "ಕಳುಹಿಸಲಾಗುತ್ತಿದೆ...",
    dispatchedBadge: "ರವಾನಿಸಲಾಗಿದೆ",
    recipientEmail: "ಸ್ವೀಕರಿಸುವವರ ಇಮೇಲ್",
    subjectLine: "ವಿಷಯ",
    auditLogTitle: "ಆಡಿಟ್ ಹಾದಿ",

    scamIntelTitle: "ನಿಯಂತ್ರಿತ ಸ್ಕ್ಯಾಮ್ ಸಂಭಾಷಣೆ ಮತ್ತು ಇಂಟೆಲಿಜೆನ್ಸ್",
    scamIntelSubtitle: "ವಂಚಕರ ಸಂಭಾಷಣೆಯಿಂದ ಕೌಂಟರ್-ಇಂಟೆಲಿಜೆನ್ಸ್ ಹೊರತೆಗೆಯುವಿಕೆ",
    startControlledCall: "ನಿಯಂತ್ರಿತ ಸಂಭಾಷಣೆ ಪ್ರಾರಂಭಿಸಿ",
    extractIntel: "ಮಾಹಿತಿ ಹೊರತೆಗೆಯಿರಿ",
    addToVault: "ಕೇಸ್ ವಾಲ್ಟ್‌ಗೆ ಸೇರಿಸಿ",
    addedToVaultBadge: "ಕೇಸ್ ವಾಲ್ಟ್‌ಗೆ ಸೇರಿಸಲಾಗಿದೆ",
    impersonationDetails: "ವ್ಯಕ್ತಿತ್ವ ನಕಲು ವಿವರಗಳು",
    psychologicalTactics: "ಮಾನಸಿಕ ತಂತ್ರಗಳು",
    extractedUpi: "ಹೊರತೆಗೆದ ಯುಪಿಐ ಐಡಿಗಳು",
    extractedPhones: "ಹೊರತೆಗೆದ ಫೋನ್ ಸಂಖ್ಯೆಗಳು",
    extractedUrls: "ಹೊರತೆಗೆದ ಫಿಶಿಂಗ್ ಲಿಂಕ್‌ಗಳು",
    unverifiedDisclaimer: "ಗಮನಿಸಿ: ಫೋರೆನ್ಸಿಕ್ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಳ್ಳುವವರೆಗೆ ಸೂಚಕಗಳನ್ನು ಅಪರಿಶೀಲಿತ ಎಂದು ಗುರುತಿಸಲಾಗುತ್ತದೆ.",
  },
};
