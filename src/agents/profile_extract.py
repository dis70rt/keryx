from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from src.core.llm_client import create_llm
from src.core.models import CompanyProfile, TargetProfile


class ProfileExtractionAgent:
    def __init__(self) -> None:
        self.llm = create_llm()

    def extract_target_profile(self, raw_profile_text: str) -> TargetProfile:
        structured_llm = self.llm.with_structured_output(TargetProfile)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert data extraction AI.
            Read raw unstructured text scraped from a LinkedIn profile and extract
            it into a highly organized JSON structure.

            Rules:
            1. If a field is missing from the text, leave it blank. Do not invent information.
            2. Synthesize 'professional_summary' from their About section and overall vibe.
            3. Infer 'communication_style' from how they write posts, about section, and headlines.
            4. Extract 'recent_activity_themes' by analyzing recent post topics.
            5. Clean up any messy text before outputting."""),
            ("human", "Here is the raw scraped LinkedIn profile data:\n\n{raw_text}"),
        ])

        chain = prompt | structured_llm
        print("  → Extracting target profile...")
        return chain.invoke({"raw_text": raw_profile_text})

    def extract_company_profile(self, raw_company_text: str) -> CompanyProfile:
        structured_llm = self.llm.with_structured_output(CompanyProfile)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert data extraction AI.
            Read raw text scraped from a LinkedIn Company page and extract it
            into a structured format. Analyze their About section and recent posts
            to determine target audience, mission statement, and core tech stack.
            Infer reasonably when exact details are unavailable."""),
            ("human", "Here is the raw scraped LinkedIn company data:\n\n{raw_text}"),
        ])

        chain = prompt | structured_llm
        print("  → Extracting company profile...")
        return chain.invoke({"raw_text": raw_company_text})