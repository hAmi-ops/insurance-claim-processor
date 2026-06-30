# Insurance Claim Document Processor

A Python application for automated processing of insurance claim documents using Amazon Bedrock foundation models. Built as a hands-on project for the **AWS Certified Generative AI Developer - Professional (AIP-C01)** certification, demonstrating Domain 1: Foundation Model Integration, Data Management, and Compliance.

## Architecture Overview

```
[Amazon S3 Bucket] → [Document Processor] → [Amazon Bedrock (Claude 4)] → [Structured Output]
       ↓                      ↓                         ↓
 claim-documents-poc-jh  Prompt Templates         Information Extraction
                         Model Invoker            Summary Generation
                         Content Validator        Model Comparison
```

**AWS Services:**
- Amazon S3 — Document storage
- Amazon Bedrock — Foundation model invocation (Claude Sonnet 4, Claude Haiku 4.5 via inference profiles)

See `architecture/diagram.md` for the full Mermaid diagram.

## Model Substitution Note

This project has undergone two model migrations as Anthropic deprecated older generations:

### Model Evolution

| Era | Models | Status |
|-----|--------|--------|
| Original spec (2023) | `anthropic.claude-v2` / `anthropic.claude-instant-v1` | Deprecated 2024 |
| First adaptation (2024) | `anthropic.claude-3-sonnet-20240229-v1:0` / `anthropic.claude-3-haiku-20240307-v1:0` | Legacy (blocked as of 2026) |
| Second adaptation (2025) | `anthropic.claude-sonnet-4-20250514-v1:0` | Legacy (blocked as of 2026) |
| **Current (2026)** | `us.anthropic.claude-sonnet-4-6` / `us.anthropic.claude-haiku-4-5-20251001-v1:0` | **Active** |

### Inference Profiles

The current models use **cross-region inference profiles**, identified by the `us.` prefix in the model ID. This enables:
- Automatic routing across US regions for higher availability
- No code changes needed — just use the inference profile ID as the `modelId` parameter

### API Compatibility

The Claude Messages API format works for all Claude models (3, 3.5, 4, 4.5):
```python
body = json.dumps({
    'anthropic_version': 'bedrock-2023-05-31',
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 1000,
    'temperature': 0.0
})
# Response: response_body['content'][0]['text']
```

## Setup Instructions

### 1. Create a Virtual Environment

```bash
cd ~/shared/insurance-claim-processor
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Ensure you have an AWS profile configured with access to Amazon Bedrock and S3:

```bash
aws configure --profile your-profile
# Set region to us-east-1
```

### 3. Create S3 Bucket and Upload Sample Claims

```bash
aws s3 mb s3://claim-documents-poc-jh --profile your-profile --region us-east-1
aws s3 cp tests/sample_claims/ s3://claim-documents-poc-jh/claims/ --recursive --profile your-profile --region us-east-1
```

## Usage

### Programmatic Usage

```python
from src.document_processor import process_document

result = process_document(
    bucket="claim-documents-poc-jh",
    key="claims/claim1.txt",
    profile_name="your-profile"
)

print(result["extracted_info"])  # Structured JSON with claim fields
print(result["summary"])         # Generated summary
print(result["validation"])      # Validation status
```

### CLI - Model Comparison

```bash
python -m src.model_comparison tests/sample_claims/claim1.txt \
    --profile your-profile \
    --region us-east-1 \
    --output evaluation/results.json
```

### CLI - Direct Processing

```bash
python -m src.document_processor
```

## Extensions

### Web Interface (Flask)

```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-east-1
python extensions/app.py
# Open http://localhost:5000
```

### Knowledge Base (RAG)

```python
from extensions.knowledge_base import SimpleKnowledgeBase

kb = SimpleKnowledgeBase()
results = kb.search("water damage burst pipe coverage")
for result in results:
    print(f"[{result['source']}] {result['content'][:100]}...")
```

### Content Filter (PII Redaction)

```python
from extensions.content_filter import ContentFilter

cf = ContentFilter()
safe_text = cf.filter_pii("SSN: 123-45-6789, Phone: 555-123-4567")
# Output: "SSN: [SSN REDACTED], Phone: [PHONE REDACTED]"
```

## Testing

Run all tests (no AWS credentials required — uses mocking):

```bash
python -m pytest tests/test_processor.py -v
```

Run with unittest directly:

```bash
python -m unittest tests.test_processor -v
```

## Project Structure

```
insurance-claim-processor/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── architecture/
│   └── diagram.md              # Mermaid architecture diagram
├── src/
│   ├── __init__.py             # Package init
│   ├── document_processor.py   # Core processing orchestrator
│   ├── prompt_templates.py     # PromptTemplateManager class
│   ├── model_invoker.py        # Bedrock wrapper with retries
│   ├── content_validator.py    # JSON validation for extractions
│   └── model_comparison.py     # Multi-model comparison tool
├── tests/
│   ├── sample_claims/          # Sample claim documents
│   │   ├── claim1.txt          # Auto accident (~$15,000)
│   │   ├── claim2.txt          # Water damage (~$8,500)
│   │   └── claim3.txt          # Theft/burglary (~$3,200)
│   └── test_processor.py       # Unit tests (mocked, no AWS needed)
├── evaluation/
│   └── findings.md             # Model comparison findings
└── extensions/
    ├── app.py                  # Flask web interface
    ├── knowledge_base.py       # Simple RAG knowledge base
    └── content_filter.py       # PII detection and redaction
```

## Key Design Decisions

1. **Temperature Settings:** 0.0 for extraction (deterministic JSON output), 0.7 for summaries (natural language)
2. **Retry Logic:** Exponential backoff (1s → 2s → 4s) for ThrottlingException and ModelTimeoutException
3. **Validation:** Strict required-field checking with warnings for quality issues
4. **JSON Extraction:** Robust parsing that handles model responses with surrounding text
5. **Credential Management:** Uses AWS profiles (no hardcoded keys), configurable via parameters
