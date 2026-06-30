# I Built an Insurance Claim Processor with Amazon Bedrock -- Here's What I Learned About Model Selection the Hard Way

When I started building an automated document processor for insurance claims using Amazon Bedrock, I expected the hard part to be prompt engineering. It wasn't. The hard part was keeping up with the models themselves.

## The Project

As a bonus assignment from the AWS Exam Prep course for the AIP-C01 (Generative AI Developer - Professional) certification, I built an end-to-end document processing pipeline that takes unstructured insurance claim text and extracts structured JSON with claimant details, policy numbers, incident dates, amounts, and descriptions. The system compares multiple foundation models, validates output quality, and includes extensions for a Flask web interface, a simple RAG knowledge base, and PII content filtering.

## The Technical Decisions That Mattered

**Temperature = 0.0 for extraction, 0.7 for summaries.** This was non-negotiable. When you need deterministic JSON output that parses cleanly every time, you cannot afford creative variance. I tested with temperature 0.3 early on and got inconsistent field naming. Zero temperature gave me 100% parse success across all test runs. Summaries, on the other hand, benefit from a bit of creativity to produce natural language.

**Prompt engineering for JSON output.** The key insight was being explicit about the exact output schema in the prompt. Vague instructions like "extract the important fields" produced inconsistent keys. Specifying exact field names, types, and a JSON template in the prompt turned both models into reliable extraction engines.

**Cross-region inference profiles.** The `us.` prefix on model IDs enables automatic routing across US regions for higher availability. No code changes needed -- just a different model ID string. This is the kind of operational detail that matters in production but rarely shows up in tutorials.

## The Results

I ran both Claude Sonnet 4.6 and Claude Haiku 4.5 against three real claim documents (auto accident, water damage, and theft):

- Both models: 100% extraction accuracy -- 5/5 required fields on every claim, valid JSON, all validations passed
- Sonnet 4.6 average latency: 3.36 seconds
- Haiku 4.5 average latency: 2.38 seconds (1.4x faster)
- Cost difference: Haiku is approximately 4x cheaper per invocation

The headline finding: Haiku 4.5 matched Sonnet's extraction quality at a quarter of the cost and responded faster on every single test. For structured extraction tasks with clear prompts, the "smaller" model is not just adequate -- it is equivalent.

## What I Actually Learned

**Model deprecation is relentless.** In the two years since this project's specification was written, I went through three generations of models: Claude v2/Instant (deprecated 2024), Claude 3 Sonnet/Haiku (blocked 2026), and Claude Sonnet 4 (already Legacy by mid-2026). The code worked every time -- the Messages API is stable -- but the model IDs underneath kept changing. If you are building on Bedrock, design for model swapability from day one.

**Inference profiles are the answer to deprecation anxiety.** Instead of pinning a specific model version, cross-region inference profiles give you the latest active model in a family. This is the pattern to use in production.

**The Messages API is the stable foundation.** Despite three model generations, the API format (`anthropic_version`, `messages` array, `max_tokens`, `temperature`) never changed. Your integration code survives model turnover if you build around the API, not around a specific model version.

## The Aha Moment

I expected Sonnet to meaningfully outperform Haiku on extraction accuracy. It didn't. Both achieved 100% on well-structured documents. The only difference was that Sonnet sometimes interpreted "claim amount" more broadly (including related expenses), while Haiku extracted the explicitly labeled amount. For a production system, that is actually an argument for Haiku -- it does exactly what you ask, no more, no less.

The real architecture recommendation: use Haiku for initial processing at scale, escalate to Sonnet only for flagged edge cases. You get the same accuracy at a fraction of the cost.

## The Code

The full implementation is on GitHub with 27 unit tests (fully mocked, no AWS credentials needed to run), prompt template management, exponential backoff retry logic, and content validation. If you are studying for the AIP-C01, this covers Domain 1 (Foundation Model Integration) end to end.

---
GitHub: [link placeholder]
#awsexamprep #AWS #AmazonBedrock #GenAI #CloudComputing #MachineLearning
