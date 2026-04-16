from dataclasses import dataclass, asdict
from typing import List

@dataclass
class TargetProfile:
    first_name: str
    current_title: str
    recent_activity_or_posts: List[str]
    past_experience: List[str]
    educational_background: List[str]
    skills_and_endorsements: List[str]

@dataclass
class CompanyProfile:
    company_name: str
    industry_and_domain: str
    recent_company_news_or_launches: List[str]
    core_tech_stack: List[str]

@dataclass
class SenderContext:
    sender_current_status: str
    sender_core_competencies: List[str]
    sender_highlight_projects: List[str]
    ask_type: str

@dataclass
class OutreachData:
    target_profile: TargetProfile
    company_profile: CompanyProfile
    sender_context: SenderContext
    
    def to_dict(self):
        return asdict(self)
