"""Flask Web Interface for Insurance Claim Document Processor.

Provides a simple web UI for uploading claim documents, processing them
with Amazon Bedrock, and viewing processing history.
"""

import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, render_template_string, request, redirect, url_for

from src.content_validator import ContentValidator
from src.model_invoker import ModelInvoker
from src.prompt_templates import PromptTemplateManager

app = Flask(__name__)

# In-memory processing history
processing_history: List[Dict[str, Any]] = []

# Configuration
AWS_PROFILE = os.environ.get("AWS_PROFILE", "wbr-admin")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
)

# HTML Templates
UPLOAD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Insurance Claim Processor</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .upload-form { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
        input[type="file"] { margin: 10px 0; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .nav { margin: 20px 0; }
        .nav a { margin-right: 15px; color: #007bff; text-decoration: none; }
        .nav a:hover { text-decoration: underline; }
        .error { color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px; }
        .success { color: #155724; background: #d4edda; padding: 10px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Insurance Claim Document Processor</h1>
    <div class="nav">
        <a href="/">Upload</a>
        <a href="/results">Results History</a>
    </div>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    {% if success %}
    <div class="success">{{ success }}</div>
    {% endif %}
    <div class="upload-form">
        <h2>Upload Claim Document</h2>
        <form method="POST" action="/process" enctype="multipart/form-data">
            <p>Select a claim document (.txt file) to process:</p>
            <input type="file" name="document" accept=".txt" required>
            <br><br>
            <button type="submit">Process Claim</button>
        </form>
    </div>
    <p><em>Using model: {{ model_id }}</em></p>
</body>
</html>
"""

RESULTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Processing Results - Insurance Claim Processor</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .nav { margin: 20px 0; }
        .nav a { margin-right: 15px; color: #007bff; text-decoration: none; }
        .result-card { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #007bff; }
        .result-card.invalid { border-left-color: #dc3545; }
        .result-card h3 { margin-top: 0; }
        .field { margin: 5px 0; }
        .field strong { display: inline-block; min-width: 150px; }
        .summary { background: #e9ecef; padding: 10px; border-radius: 4px; margin-top: 10px; }
        .timestamp { color: #666; font-size: 0.9em; }
        pre { background: #272822; color: #f8f8f2; padding: 15px; border-radius: 4px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>Processing Results</h1>
    <div class="nav">
        <a href="/">Upload</a>
        <a href="/results">Results History</a>
    </div>
    {% if results %}
        {% for item in results %}
        <div class="result-card {{ 'invalid' if not item.validation.is_valid else '' }}">
            <h3>{{ item.filename }}</h3>
            <p class="timestamp">Processed: {{ item.timestamp }}</p>
            {% if item.validation.is_valid %}
                {% for key, value in item.extracted_info.items() %}
                <div class="field"><strong>{{ key }}:</strong> {{ value }}</div>
                {% endfor %}
                <div class="summary">
                    <strong>Summary:</strong> {{ item.summary }}
                </div>
            {% else %}
                <p>Validation Errors:</p>
                <ul>
                {% for error in item.validation.errors %}
                    <li>{{ error }}</li>
                {% endfor %}
                </ul>
                <pre>{{ item.raw_response }}</pre>
            {% endif %}
        </div>
        {% endfor %}
    {% else %}
        <p>No documents processed yet. <a href="/">Upload a claim</a> to get started.</p>
    {% endif %}
</body>
</html>
"""


@app.route("/")
def upload_form():
    """Display the file upload form."""
    return render_template_string(
        UPLOAD_TEMPLATE,
        model_id=MODEL_ID,
        error=request.args.get("error"),
        success=request.args.get("success"),
    )


@app.route("/process", methods=["POST"])
def process_document():
    """Process an uploaded claim document."""
    if "document" not in request.files:
        return redirect(url_for("upload_form", error="No file uploaded"))

    file = request.files["document"]
    if file.filename == "":
        return redirect(url_for("upload_form", error="No file selected"))

    try:
        # Read document content
        document_text = file.read().decode("utf-8")

        # Initialize components
        template_manager = PromptTemplateManager()
        model_invoker = ModelInvoker(
            profile_name=AWS_PROFILE, region_name=AWS_REGION
        )
        validator = ContentValidator()

        # Extract information
        extraction_prompt = template_manager.get_prompt(
            "extract_info", document_text=document_text
        )
        extraction_response = model_invoker.invoke(
            prompt=extraction_prompt,
            model_id=MODEL_ID,
            temperature=0.0,
            max_tokens=1000,
        )

        # Parse and validate
        parsed_data, parse_error = validator.validate_json_string(extraction_response)

        if parsed_data:
            validation_result = validator.validate_extraction(parsed_data)
            extracted_info = parsed_data
        else:
            validation_result = validator.validate_extraction({})
            extracted_info = {"parse_error": parse_error}

        # Generate summary
        summary = ""
        if validation_result.is_valid:
            summary_prompt = template_manager.get_prompt(
                "generate_summary",
                extracted_info=json.dumps(extracted_info, indent=2),
            )
            summary = model_invoker.invoke(
                prompt=summary_prompt,
                model_id=MODEL_ID,
                temperature=0.7,
                max_tokens=500,
            )

        # Store in history
        result_entry = {
            "filename": file.filename,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "extracted_info": extracted_info,
            "summary": summary,
            "validation": {
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
            },
            "raw_response": extraction_response[:500],
        }
        processing_history.insert(0, result_entry)

        return redirect(
            url_for("upload_form", success=f"Document '{file.filename}' processed successfully!")
        )

    except Exception as e:
        return redirect(url_for("upload_form", error=f"Processing error: {str(e)}"))


@app.route("/results")
def show_results():
    """Display processing history."""
    return render_template_string(RESULTS_TEMPLATE, results=processing_history)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
