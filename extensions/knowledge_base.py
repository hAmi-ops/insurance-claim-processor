"""Simple Knowledge Base for Insurance Policy RAG.

Provides a simple keyword-based search over insurance policy documents
to enable Retrieval-Augmented Generation (RAG) for policy checking.
"""

import os
import re
from typing import Dict, List


# Sample insurance policy content (used when no external documents are loaded)
SAMPLE_POLICIES = {
    "auto_comprehensive.txt": """
AUTO INSURANCE POLICY - COMPREHENSIVE COVERAGE
Policy Type: Comprehensive Auto Insurance
Effective Period: 12 months from policy start date

SECTION 1: COLLISION COVERAGE
Coverage includes damage to the insured vehicle resulting from:
- Collision with another vehicle
- Collision with a stationary object
- Single-vehicle accidents (rollover, running off road)

Deductible: As stated on declarations page (typically $500 or $1,000)
Maximum Coverage: Actual Cash Value (ACV) of the vehicle at time of loss

SECTION 2: COMPREHENSIVE (OTHER THAN COLLISION)
Coverage includes damage from:
- Theft or attempted theft
- Vandalism
- Fire or explosion
- Natural disasters (flood, hail, wind)
- Falling objects
- Contact with animals

SECTION 3: LIABILITY COVERAGE
Bodily Injury Liability: Up to policy limits per person/per accident
Property Damage Liability: Up to policy limits per accident

SECTION 4: MEDICAL PAYMENTS
Covers reasonable medical expenses for the insured and passengers
regardless of fault, up to policy limits.

SECTION 5: RENTAL REIMBURSEMENT
Daily rental car coverage up to $50/day for maximum 30 days while
insured vehicle is being repaired for a covered claim.

EXCLUSIONS:
- Intentional damage by the insured
- Racing or competitive events
- Commercial use (unless endorsed)
- Wear and tear, mechanical breakdown
- Vehicles not listed on the policy
""",
    "homeowners_standard.txt": """
HOMEOWNERS INSURANCE POLICY - STANDARD FORM (HO-3)
Policy Type: Standard Homeowners
Effective Period: 12 months from policy start date

SECTION 1: DWELLING COVERAGE (COVERAGE A)
Covers damage to the physical structure of the home from covered perils.
Covered perils include:
- Fire and lightning
- Windstorm and hail
- Explosion
- Smoke damage
- Vandalism
- Theft
- Weight of ice, snow, or sleet
- Accidental discharge of water or steam from plumbing
- Freezing of plumbing, heating, or air conditioning systems
- Sudden and accidental damage from electrical current

SECTION 2: PERSONAL PROPERTY (COVERAGE B)
Covers personal belongings inside the home.
Standard limit: 50-70% of dwelling coverage amount.
Special limits apply to:
- Jewelry: $1,500 (unless scheduled)
- Electronics: $2,500 (unless scheduled)
- Cash: $200

SECTION 3: LOSS OF USE (COVERAGE C)
If the home is uninhabitable due to a covered loss, policy covers:
- Additional living expenses
- Fair rental value

SECTION 4: WATER DAMAGE SPECIFICS
COVERED:
- Sudden and accidental discharge from plumbing systems
- Burst pipes due to freezing
- Overflow of appliances (washing machine, water heater)

NOT COVERED:
- Gradual water damage or seepage
- Flood (requires separate flood policy)
- Sewer backup (requires endorsement)
- Failure to maintain the property

DEDUCTIBLE: As stated on declarations page
""",
    "renters_policy.txt": """
RENTERS INSURANCE POLICY
Policy Type: Renters (HO-4)
Effective Period: 12 months from policy start date

SECTION 1: PERSONAL PROPERTY COVERAGE
Covers personal belongings against covered perils:
- Fire and smoke
- Windstorm and hail
- Explosion
- Theft and burglary
- Vandalism
- Water damage from plumbing
- Electrical surge damage

Coverage Limit: As stated on declarations page
Deductible: As stated on declarations page (typically $500-$1,000)

SECTION 2: THEFT COVERAGE SPECIFICS
- Must file police report within 72 hours
- Proof of ownership required (receipts, photos, serial numbers)
- Actual Cash Value (ACV) or Replacement Cost Value (RCV) depending on policy
- Off-premises theft covered up to 10% of personal property limit

Special Limits for Theft:
- Cash and securities: $200
- Jewelry and watches: $1,500
- Firearms: $2,500
- Silverware: $2,500
- Electronics: $2,500 (per item)
- Business property: $2,500

SECTION 3: LIABILITY COVERAGE
Personal liability: Up to policy limits
Medical payments to others: Up to $5,000 per person

SECTION 4: LOSS OF USE
If rental unit is uninhabitable due to covered loss:
- Additional living expenses covered
- Limited to 20% of personal property coverage

EXCLUSIONS:
- Flood damage
- Earthquake damage
- Intentional damage
- Damage from pets to the rental unit
- Business inventory or equipment beyond limits
- Vehicles and their contents
""",
}


class SimpleKnowledgeBase:
    """Simple keyword-based knowledge base for insurance policies.

    Loads policy documents and provides search functionality based on
    keyword matching. Designed for RAG (Retrieval-Augmented Generation)
    to provide policy context when checking claims.

    Attributes:
        documents: Dictionary mapping document names to their content.
    """

    def __init__(self, policy_directory: str = None) -> None:
        """Initialize the knowledge base.

        Args:
            policy_directory: Optional path to directory containing policy
                text files. If None, uses built-in sample policies.
        """
        self.documents: Dict[str, str] = {}

        if policy_directory and os.path.isdir(policy_directory):
            self._load_from_directory(policy_directory)
        else:
            self.documents = SAMPLE_POLICIES.copy()

    def _load_from_directory(self, directory: str) -> None:
        """Load all .txt files from a directory.

        Args:
            directory: Path to directory containing policy documents.
        """
        for filename in os.listdir(directory):
            if filename.endswith(".txt"):
                filepath = os.path.join(directory, filename)
                with open(filepath, "r") as f:
                    self.documents[filename] = f.read()

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """Search policy documents using keyword matching.

        Searches all loaded documents for paragraphs/sections containing
        query keywords. Returns the most relevant excerpts.

        Args:
            query: Search query string (keywords will be extracted).
            max_results: Maximum number of relevant excerpts to return.

        Returns:
            List of dictionaries with 'source' and 'content' keys,
            containing relevant policy excerpts.
        """
        # Extract keywords (words longer than 3 chars, lowercased)
        keywords = [
            word.lower()
            for word in re.findall(r"\b\w+\b", query)
            if len(word) > 3
        ]

        if not keywords:
            return []

        scored_sections: List[Dict] = []

        for doc_name, doc_content in self.documents.items():
            # Split document into sections by double newlines
            sections = [s.strip() for s in doc_content.split("\n\n") if s.strip()]

            for section in sections:
                section_lower = section.lower()
                # Score by number of keyword matches
                score = sum(
                    1 for keyword in keywords if keyword in section_lower
                )

                if score > 0:
                    scored_sections.append({
                        "source": doc_name,
                        "content": section,
                        "score": score,
                    })

        # Sort by score descending and return top results
        scored_sections.sort(key=lambda x: x["score"], reverse=True)

        return [
            {"source": s["source"], "content": s["content"]}
            for s in scored_sections[:max_results]
        ]

    def get_document(self, name: str) -> str:
        """Retrieve a full policy document by name.

        Args:
            name: Document filename/key.

        Returns:
            Full document content string.

        Raises:
            KeyError: If document name is not found.
        """
        if name not in self.documents:
            raise KeyError(
                f"Document '{name}' not found. Available: {list(self.documents.keys())}"
            )
        return self.documents[name]

    def list_documents(self) -> List[str]:
        """List all available policy document names.

        Returns:
            List of document name strings.
        """
        return list(self.documents.keys())


if __name__ == "__main__":
    # Demo usage
    kb = SimpleKnowledgeBase()
    print(f"Loaded {len(kb.documents)} policy documents:")
    for name in kb.list_documents():
        print(f"  - {name}")

    print("\nSearching for 'water damage burst pipe':")
    results = kb.search("water damage burst pipe")
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} (from {result['source']}) ---")
        print(result["content"][:200] + "...")
