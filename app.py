import os
import PyPDF2
import pandas as pd
from groq import Groq
from typing import Dict, List, Any
import re
from datetime import datetime
import logging
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialDocumentAnalyzer:
    """
    A class to analyze financial documents using the Groq API.
    Extracts key information relevant for investors.
    """

    def __init__(self):
        """
        Initialize the analyzer with API credentials.
        """
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "mixtral-8x7b-32768"  # Using Mixtral model for better performance

    def extract_text_from_pdf(self, pdf_file) -> str:
        """
        Extract text content from a PDF file.

        Args:
            pdf_file (BytesIO): PDF file in memory

        Returns:
            str: Extracted text content
        """
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    def chunk_text(self, text: str, chunk_size: int = 15000) -> List[str]:
        """
        Split text into smaller chunks for API processing.

        Args:
            text (str): Input text
            chunk_size (int): Maximum size of each chunk

        Returns:
            List[str]: List of text chunks
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            if current_size + len(word) > chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word) + 1

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def analyze_chunk(self, chunk: str) -> Dict[str, Any]:
        """
        Analyze a text chunk using the Groq API.

        Args:
            chunk (str): Text chunk to analyze

        Returns:
            Dict[str, Any]: Extracted information
        """
        prompt = (
            "Analyze the following financial document text and extract key information for investors:\n\n"
            f"{chunk}\n\n"
            "Please identify and structure the following elements:\n"
            "1. Future Growth Prospects\n"
            "2. Key Business Changes\n"
            "3. Important Triggers\n"
            "4. Material Information Affecting Future Earnings\n"
            "5. Risk Factors\n"
            "6. Financial Metrics\n"
            "7. Strategic Initiatives\n\n"
            "Provide the analysis in a structured format."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )

            return self._parse_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error in API call: {str(e)}")
            raise

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the API response into a structured format.

        Args:
            response (str): Raw API response

        Returns:
            Dict[str, Any]: Structured information
        """
        # Initialize categories
        categories = {
            "growth_prospects": [],
            "business_changes": [],
            "triggers": [],
            "material_information": [],
            "risk_factors": [],
            "financial_metrics": [],
            "strategic_initiatives": []
        }

        current_category = None

        # Parse response line by line
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Check for category headers
            if "Growth Prospects" in line:
                current_category = "growth_prospects"
            elif "Business Changes" in line:
                current_category = "business_changes"
            elif "Triggers" in line:
                current_category = "triggers"
            elif "Material Information" in line:
                current_category = "material_information"
            elif "Risk Factors" in line:
                current_category = "risk_factors"
            elif "Financial Metrics" in line:
                current_category = "financial_metrics"
            elif "Strategic Initiatives" in line:
                current_category = "strategic_initiatives"
            elif current_category and line.startswith(('-', '•', '*')):
                categories[current_category].append(line.lstrip('-').lstrip('•').lstrip('*').strip())

        return categories

    def analyze_document(self, pdf_file) -> Dict[str, Any]:
        """
        Analyze an entire financial document.

        Args:
            pdf_file (BytesIO): PDF file in memory

        Returns:
            Dict[str, Any]: Complete analysis results
        """
        # Extract text from PDF
        text = self.extract_text_from_pdf(pdf_file)

        # Split into chunks
        chunks = self.chunk_text(text)

        # Analyze each chunk
        results = []
        for chunk in chunks:
            chunk_results = self.analyze_chunk(chunk)
            results.append(chunk_results)

        # Merge results
        merged_results = self._merge_results(results)

        # Add metadata
        merged_results['metadata'] = {
            'analysis_date': datetime.now().isoformat(),
            'number_of_chunks': len(chunks)
        }

        return merged_results

    def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results from multiple chunks into a single analysis.

        Args:
            results (List[Dict[str, Any]]): List of chunk results

        Returns:
            Dict[str, Any]: Merged results
        """
        merged = {
            "growth_prospects": set(),
            "business_changes": set(),
            "triggers": set(),
            "material_information": set(),
            "risk_factors": set(),
            "financial_metrics": set(),
            "strategic_initiatives": set()
        }

        # Merge all results, removing duplicates
        for result in results:
            for category in merged.keys():
                merged[category].update(result.get(category, []))

        # Convert sets back to sorted lists
        return {k: sorted(list(v)) for k, v in merged.items()}

def main():
    """
    Main function to run the financial document analyzer.
    """
    st.title("Financial Document Analyzer")

    # File upload
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        # Initialize analyzer
        analyzer = FinancialDocumentAnalyzer()

        # Analyze document
        with st.spinner('Analyzing document...'):
            results = analyzer.analyze_document(uploaded_file)

        # Display results
        st.header("Analysis Results")

        st.subheader("Future Growth Prospects")
        for item in results['growth_prospects']:
            st.write(f"• {item}")

        st.subheader("Key Business Changes")
        for item in results['business_changes']:
            st.write(f"• {item}")

        st.subheader("Important Triggers")
        for item in results['triggers']:
            st.write(f"• {item}")

        st.subheader("Material Information")
        for item in results['material_information']:
            st.write(f"• {item}")

        st.subheader("Risk Factors")
        for item in results['risk_factors']:
            st.write(f"• {item}")

        st.subheader("Financial Metrics")
        for item in results['financial_metrics']:
            st.write(f"• {item}")

        st.subheader("Strategic Initiatives")
        for item in results['strategic_initiatives']:
            st.write(f"• {item}")

if __name__ == "__main__":
    main()
