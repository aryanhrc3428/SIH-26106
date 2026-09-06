# INSTRUCTIONS.md: AI Agent Designing & Coding Standards
## Module 5: NLP Fraud Classifier & Content Analysis Engine

---

## 1. Module Identity & Architectural Boundary
* **Module Name:** `module-5-nlp-fraud`
* **Owner:** Member 5 (Backend Dev 3)
* **Framework Stack:** Python 3.11+, Celery, Redis, PyTorch / ONNX Runtime, HuggingFace `transformers` (`DeBERTa-v3` / `DistilBERT`), `beautifulsoup4`, `httpx`, `tldextract`, Pydantic V2.
* **Core Function:** Extracts plain text and HTML body contents, detects social engineering & urgency cues, executes NLP Transformer-based fraud classification (Phishing, BEC, Credential Harvesting, Impersonation), inspects embedded URLs, resolves redirect chains, and calculates `content_suspicion_score`.
* **Isolation Guarantee:** Module 5 operates strictly as a background worker consuming tasks from Redis queue `queue_nlp_fraud`. It **NEVER** exposes HTTP endpoints directly and **NEVER** interacts directly with Module 1, Module 3, Module 4, or Module 6.

---

## 2. Directory Structure & Code Layout Guidelines

When generating or editing code for Module 5, strictly follow this layout:

```
module-5-nlp-fraud/
├── app/
│   ├── worker.py                   # Celery worker entrypoint & task definitions
│   ├── core/
│   │   ├── config.py               # Pydantic settings for model paths & inference limits
│   │   └── celery_app.py           # Celery application instance configured for queue_nlp_fraud
│   ├── nlp/
│   │   ├── text_extractor.py       # MIME body extraction & HTML sanitization (BeautifulSoup)
│   │   ├── classifier.py           # Transformer model inference wrapper (ONNX/PyTorch)
│   │   ├── urgency_detector.py     # Financial diversion & pressure language lexical analyzer
│   │   ├── url_analyzer.py         # URL regex extraction & tldextract risk scorer
│   │   └── redirect_resolver.py    # Async HTTP redirect chain unshortener
│   ├── schemas/
│   │   └── output_schema.py        # Strict Pydantic output model for task completion payload
│   └── utils/
│       └── model_loader.py         # Singleton model loader ensuring zero reload overhead
├── models/
│   └── deberta_phishing_v1.onnx    # Quantized ONNX Transformer model for CPU inference
├── tests/
│   ├── test_text_extractor.py
│   ├── test_classifier.py
│   ├── test_urgency_detector.py
│   └── test_url_analyzer.py
├── requirements.txt
└── Dockerfile
```

---

## 3. Designing & Coding Standards

### A. Body Content Extraction & Cleaning
1. **HTML Parsing & Sanitization:**
   * Extract plain text from multi-part MIME bodies (`text/plain` preferred, `text/html` fallback).
   * Use `BeautifulSoup` (`lxml` parser) to strip HTML tags, script elements, CSS styles, and hidden zero-font obfuscation text (`<span style="font-size:0px">...</span>`).
   * Normalize whitespace, decode HTML entities (`&amp;`, `&lt;`), and remove control characters.

### B. NLP Transformer Model Inference
1. **ONNX Runtime / CPU Optimization (CRITICAL):**
   * Use ONNX Runtime (`onnxruntime`) with quantized Transformer models (`DeBERTa-v3-small` or `DistilBERT-phishing`) for sub-second CPU inference (< 300ms execution per email).
   * Maintain a **Singleton Model Class** in `utils/model_loader.py` so model weights are loaded into memory once during worker initialization, NOT per task.
2. **Multi-Class Classification Categories:**
   * `LEGITIMATE`: Standard business communication.
   * `PHISHING`: Generic credential stealing / fake portal link.
   * `BEC_FINANCIAL`: Payment diversion, urgent wire transfer, fake invoice request.
   * `CREDENTIAL_HARVESTING`: Account suspension warning requiring immediate login.
   * `IMPERSONATION`: Executive name impersonation / internal authority spoofing.

### C. Urgency & Social Engineering Analysis
1. **Lexical Pattern Matching:**
   * Detect urgency triggers ("IMMEDIATE ACTION REQUIRED", "WIRE TRANSFER", "GIFT CARD", "PAYMENT OVERDUE", "ACCOUNT SUSPENDED").
   * Calculate `urgency_score` (0.0 to 100.0) combining lexical pattern weights and Transformer model confidence output.

### D. Embedded URL & Redirect Chain Analysis
1. **URL Extraction:** Extract all embedded links using regex `https?://[^\s<>"]+`.
2. **Redirect Unshortening & SSRF Protection (CRITICAL):**
   * Expand shortened links (`bit.ly`, `tinyurl.com`, `t.co`) using asynchronous `httpx.AsyncClient` HEAD/GET requests.
   * **SSRF Guardrail:** Resolve destination IP before initiating each redirect hop. Immediately abort unshortening if target resolves to private/internal subnets (RFC 1918 `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), link-local (`169.254.0.0/16`), or cloud metadata endpoints (`169.254.169.254`).
   * Limit redirect chain depth to maximum **5 hops**.
3. **Suspicious TLD & Domain Inspection:**
   * Use `tldextract` to isolate Registered Domain and TLD.
   * Flag high-risk TLDs (`.top`, `.work`, `.xyz`, `.click`, `.zip`, `.tk`).
   * Note: Domain WHOIS age calculation is performed by Module 4 (`domain_intel`), set `domain_age_days = null` in Module 5 output schema.

---

## 4. Error Handling & Guardrails

1. **Redirect Unshortener Timeout Guardrails (CRITICAL):**
   * All link unshortening HTTP calls MUST enforce strict `timeout=2.0` seconds total timeout.
   * If a target URL hangs, fails to resolve, or triggers SSRF filter, abort redirect tracking for that URL, retain original link, and set `risk_score = 75.0` (unresolvable / suspicious link flag).
2. **Out-of-Memory (OOM) Protection:**
   * Truncate input text to maximum **512 tokens** before passing to Transformer tokenizer to guarantee fixed-memory inference bounds.
3. **Content Suspicion Score Calculation & Clamping:**
   * `content_suspicion_score` (0.0 to 100.0) calculated dynamically based on weights:
     * Model Class = BEC / Phishing: +60 * Model Confidence
     * High Urgency Score (> 70): +25
     * Suspicious TLD / Shortened URL Detected: +15
   * **Score Clamping:** Standardize score output using `content_suspicion_score = min(calculated_score, 100.0)`.

---

## 5. Testing & Quality Requirements

1. Test coverage must include HTML obfuscated text, shortened links, BEC wire transfer templates, and benign emails.
2. Run test suite:
   ```bash
   pytest tests/ -v --cov=app
   ```
