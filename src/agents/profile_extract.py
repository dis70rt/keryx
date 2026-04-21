from pathlib import Path

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.core.llm_client import create_llm
from src.core.models import CompanyProfile, TargetProfile


class ProfileExtractionAgent:
    def __init__(self) -> None:
        self.llm = create_llm()

    def extract_target_profile(self, raw_profile_text: str) -> TargetProfile:
        parser = PydanticOutputParser(pydantic_object=TargetProfile)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """<|channel>thought<channel|> You are an expert data extraction AI.
            Read raw unstructured text scraped from a LinkedIn profile and extract
            it into a highly organized JSON structure.

            Rules:
            1. If a field is missing from the text, leave it blank. Do not invent information.
            2. Synthesize 'professional_summary' from their About section and overall vibe.
            3. Infer 'communication_style' from how they write posts, about section, and headlines.
            4. Extract 'recent_activity_themes' by analyzing recent post topics.
            5. Clean up any messy text before outputting.
            6. For 'past_experience', extract ONLY the 5 most recent roles. Ignore older positions.
            7. For 'skills_and_endorsements', list at most 10 skills.
            8. Keep your JSON output SHORT. Do not repeat field names or values."""),
            ("human", """Here is the raw scraped LinkedIn profile data:

{raw_text}

=========================================
IMPORTANT FINAL INSTRUCTIONS:
{format_instructions}

CRITICAL: You MUST return ONLY valid JSON. Do NOT include markdown blocks (like ```json). Do NOT include any conversational text. Start directly with {{ and end with }}. Your response will be parsed directly by `json.loads()`, so it must be perfect."""),
        ])

        chain = prompt | self.llm | parser
        from src.core.logger import logger
        with logger.status("Extracting target profile..."):
            return chain.invoke({
                "raw_text": raw_profile_text,
                "format_instructions": parser.get_format_instructions()
            })

    def extract_company_profile(self, raw_company_text: str) -> CompanyProfile:
        parser = PydanticOutputParser(pydantic_object=CompanyProfile)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """<|channel>thought<channel|> You are an expert data extraction AI.
            Read raw text scraped from a LinkedIn Company page and extract it
            into a structured format. Analyze their About section and recent posts
            to determine target audience, mission statement, and core tech stack.
            Infer reasonably when exact details are unavailable."""),
            ("human", """Here is the raw scraped LinkedIn company data:

{raw_text}

=========================================
IMPORTANT FINAL INSTRUCTIONS:
{format_instructions}

CRITICAL: You MUST return ONLY valid JSON. Do NOT include markdown blocks (like ```json). Do NOT include any conversational text. Start directly with {{ and end with }}. Your response will be parsed directly by `json.loads()`, so it must be perfect."""),
        ])

        chain = prompt | self.llm | parser
        from src.core.logger import logger
        with logger.status("Extracting company profile..."):
            return chain.invoke({
                "raw_text": raw_company_text,
                "format_instructions": parser.get_format_instructions()
            })