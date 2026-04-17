import json
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_core.prompts import ChatPromptTemplate
from core.models import TargetProfile, CompanyProfile
from core.llm_client import create_llm

class ProfileExtractionAgent:
    def __init__(self):
        self.llm = create_llm()
        
    def extract_target_profile(self, raw_profile_text: str) -> TargetProfile:
        structured_llm = self.llm.with_structured_output(TargetProfile)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert data extraction AI. 
            Your job is to read raw, unstructured text scraped from a LinkedIn profile and extract the information into a highly organized JSON structure.
            
            Follow these rules:
            1. If a field is missing from the text, leave it blank or omit it. Do not invent information.
            2. Synthesize the 'professional_summary' by reading their 'About' section and understanding their overall vibe.
            3. Infer 'communication_style' based on how they write their posts, about section, and headlines.
            4. Extract the core 'recent_activity_themes' by analyzing the topic of their recent posts.
            5. Clean up any messy text before outputting."""),
            ("human", "Here is the raw scraped LinkedIn profile data:\n\n{raw_text}")
        ])
        
        chain = prompt | structured_llm
        print("Extracting Target Profile data...")
        return chain.invoke({"raw_text": raw_profile_text})

    def extract_company_profile(self, raw_company_text: str) -> CompanyProfile:
        structured_llm = self.llm.with_structured_output(CompanyProfile)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert data extraction AI. 
            Your job is to read raw text scraped from a LinkedIn Company page and extract it into a structured format.
            
            Analyze their 'About' section and recent posts to determine their target audience, mission statement, and core tech stack (if mentioned).
            If exact details are not available, infer reasonably based on industry standard context provided in the text."""),
            ("human", "Here is the raw scraped LinkedIn company data:\n\n{raw_text}")
        ])
        
        chain = prompt | structured_llm
        print("Extracting Company Profile data...")
        return chain.invoke({"raw_text": raw_company_text})


if __name__ == "__main__":
    load_dotenv()
    
    project_root = Path(__file__).resolve().parent.parent.parent
    raw_path = project_root / "data" / "raw_extracted.json"
    
    if not raw_path.exists():
        print(f"Need to run scraper first to get raw data! Looking for: {raw_path}")
        exit(1)
        
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        full_text = "\n".join([f"--- {k} ---\n{v}" for k, v in raw_data.items()])
        
    agent = ProfileExtractionAgent()
    target_profile = agent.extract_target_profile(full_text)
    
    print("\n--- EXTRACTED PROFILE ---")
    print(json.dumps(target_profile.model_dump(), indent=2))