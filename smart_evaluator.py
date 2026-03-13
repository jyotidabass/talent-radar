import json
import re
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, Field
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import streamlit as st
load_dotenv()

# Pydantic model for OpenAI evaluation response
class EvaluationScores(BaseModel):
    education: float
    career_trajectory: float
    company_relevance: float
    tenure_stability: float
    core_skills: float
    bonus_signals: float
    red_flags: float

class EvaluationResponse(BaseModel):
    scores: EvaluationScores
    final_score: float
    strengths: List[str]
    weaknesses: List[str]
    rationale: str
    override_signal: bool = Field(default=False)

class SmartContextDetector:
    """Detects industry, company type, role type, and role subtype from job descriptions"""
    
    def __init__(self):
        self.industry_patterns = {
            "Tech": ["software", "ai", "ml", "saas", "startup", "tech", "developer", "engineer", "data", "cloud"],
            "Healthcare": ["hospital", "medical", "nurse", "doctor", "clinical", "patient", "healthcare", "pharma"],
            "Finance": ["finance", "investment", "banking", "trading", "fintech", "accounting", "cpa", "tax"],
            "Legal": ["law", "attorney", "lawyer", "legal", "litigation", "compliance", "paralegal"],
            "Retail": ["retail", "ecommerce", "consumer", "merchandising", "store", "sales"],
            "Education": ["education", "teacher", "professor", "university", "school", "academic"],
            "Government": ["government", "public sector", "federal", "state", "municipal", "agency"]
        }
        
        self.company_types = {
            "VC-backed Startup": ["startup", "series a", "series b", "series c", "vc", "venture", "funding", "round"],
            "Enterprise": ["enterprise", "fortune 500", "large company", "corporation", "multinational"],
            "Hospital Group": ["hospital", "health system", "medical center", "clinic"],
            "Public Sector": ["government", "public", "federal", "state", "city", "municipal"],
            "Legal": ["law firm", "lawyer", "attorney", "legal", "litigation", "compliance", "paralegal","real estate"]
        }
        
        self.role_types = {
            "Software Engineer": ["software engineer", "developer", "programmer", "swe"],
            "DevOps Engineer": ["devops", "infrastructure", "site reliability", "platform engineer"],
            "Data Scientist": ["data scientist", "ml engineer", "ai engineer", "machine learning"],
            "Product Manager": ["product manager", "pm", "product owner"],
            "Designer": ["designer", "ux", "ui", "creative director"],
            "Sales": ["sales", "account manager", "business development", "revenue"],
            "Marketing": ["marketing", "growth", "content", "brand"],
            "Finance": ["finance", "accounting", "controller", "cfo", "analyst"],
            "Legal": ["lawyer", "attorney", "counsel", "legal"],
            "Operations": ["operations", "project manager", "program manager"]
        }

    def detect_context(self, job_description: str) -> Dict[str, str]:
        """Detect context parameters from job description"""
        text = job_description.lower()
        
        # Detect industry
        industry = self._detect_category(text, self.industry_patterns, "Tech")
        
        # Detect company type
        company_type = self._detect_category(text, self.company_types, "Enterprise")
        
        # Detect role type
        role_type = self._detect_category(text, self.role_types, "Software Engineer")
        
        # Detect role subtype (more specific)
        role_subtype = self._detect_role_subtype(text, role_type)
        
        return {
            "industry": industry,
            "company_type": company_type,
            "role_type": role_type,
            "role_subtype": role_subtype
        }
    
    def _detect_category(self, text: str, patterns: Dict[str, List[str]], default: str) -> str:
        """Detect category based on keyword patterns"""
        scores = {}
        for category, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[category] = score
        
        return max(scores.items(), key=lambda x: x[1])[0] if scores else default
    
    def _detect_role_subtype(self, text: str, role_type: str) -> str:
        """Detect specific role subtype"""
        subtypes = {
            "Software Engineer": {
                "Frontend": ["frontend", "react", "angular", "vue", "ui"],
                "Backend": ["backend", "api", "server", "database"],
                "Full-stack": ["full-stack", "fullstack"],
                "Mobile": ["mobile", "ios", "android", "react native"]
            },
            "DevOps Engineer": {
                "Cloud Infrastructure": ["cloud", "aws", "azure", "gcp"],
                "CI/CD": ["ci/cd", "jenkins", "pipeline"],
                "Security": ["security", "compliance", "devsecops"]
            },
            "Data Scientist": {
                "ML Engineer": ["ml engineer", "machine learning"],
                "Data Analyst": ["data analyst", "analytics"],
                "AI Researcher": ["ai research", "nlp", "computer vision"]
            }
        }
        
        if role_type in subtypes:
            for subtype, keywords in subtypes[role_type].items():
                if any(keyword in text for keyword in keywords):
                    return subtype
        
        return "General"

class SmartEvaluator:
    """Main class implementing SRN Smart Candidate Evaluation System"""
    
    def __init__(self):
        self.context_detector = SmartContextDetector()
        self.api_key = st.secrets["OPENAI_API_KEY"]
        # Initialize LLM without JSON mode for criteria generation
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.1, 
            openai_api_key=self.api_key
        )
        # Separate LLM instance with JSON mode for evaluation
        self.llm_json = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.1, 
            openai_api_key=self.api_key,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """Extract JSON from a response that might be wrapped in markdown or contain extra text"""
        # Remove any leading/trailing whitespace
        response = response.strip()
        
        # First try to parse as-is
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
        matches = re.findall(json_pattern, response)
        
        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        # Try to find JSON starting with { and ending with matching }
        start_idx = response.find('{')
        if start_idx != -1:
            bracket_count = 0
            end_idx = start_idx
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(response)):
                char = response[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        bracket_count += 1
                    elif char == '}':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i
                            break
            
            if end_idx > start_idx and bracket_count == 0:
                try:
                    json_str = response[start_idx:end_idx + 1]
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"[DEBUG] JSON decode error: {e}")
                    print(f"[DEBUG] Attempted to parse: {json_str[:200]}...")
        
        print(f"[DEBUG] Could not extract JSON from response: {response[:200]}...")
        return None
    
    def evaluate_candidate_smart(self, candidate_profile: Dict, job_description: str) -> Dict[str, Any]:
        """Complete smart evaluation pipeline"""
        
        # Step 1: Detect context
        context = self.context_detector.detect_context(job_description)
        
        # Step 2: Generate hiring criteria
        criteria = self._generate_criteria(context, job_description)
        
        # Step 3: Evaluate candidate using SRN FitScore
        evaluation = self._evaluate_candidate(candidate_profile, criteria, context)
        
        return {
            "context": context,
            "hiring_criteria": criteria,
            "evaluation": evaluation,
            "fit_score": evaluation["final_score"],
            "recommendation": self._generate_recommendation(evaluation["final_score"])
        }
    
    def evaluate_linkedin_profile(self, linkedin_data: Dict, job_description: str) -> Dict[str, Any]:
        """
        Evaluate a candidate from raw LinkedIn profile data
        Handles more complex LinkedIn data structures
        """
        profile = {}
        
        # Extract basic info
        profile['name'] = linkedin_data.get('name', 'Unknown')
        profile['title'] = linkedin_data.get('headline', linkedin_data.get('title', ''))
        profile['location'] = linkedin_data.get('location', '')
        profile['snippet'] = linkedin_data.get('summary', linkedin_data.get('about', ''))
        
        # Extract experience
        if 'experience' in linkedin_data and isinstance(linkedin_data['experience'], list):
            experiences = linkedin_data['experience']
            if experiences:
                # Current role
                current = experiences[0]
                profile['current_role'] = current.get('title', '')
                profile['current_company'] = current.get('company', '')
                
                # Calculate total years of experience
                total_years = 0
                companies = []
                for exp in experiences:
                    companies.append(exp.get('company', ''))
                    # Try to calculate duration if available
                    if 'duration' in exp:
                        # Parse duration (e.g., "2 yrs 3 mos")
                        duration = exp['duration']
                        years = re.search(r'(\d+)\s*yr', duration)
                        months = re.search(r'(\d+)\s*mo', duration)
                        if years:
                            total_years += int(years.group(1))
                        if months:
                            total_years += int(months.group(1)) / 12
                
                profile['years_experience'] = f"{int(total_years)} years" if total_years > 0 else "Unknown"
                profile['companies'] = list(filter(None, set(companies)))  # Unique, non-empty companies
        
        # Extract education
        if 'education' in linkedin_data and isinstance(linkedin_data['education'], list):
            education_items = []
            for edu in linkedin_data['education']:
                school = edu.get('school', '')
                degree = edu.get('degree', '')
                field = edu.get('field', '')
                edu_str = f"{degree} in {field} from {school}" if degree and field else f"{school}"
                education_items.append(edu_str.strip())
            profile['education'] = '; '.join(education_items)
        
        # Extract skills
        if 'skills' in linkedin_data:
            if isinstance(linkedin_data['skills'], list):
                profile['skills'] = [skill.get('name', skill) if isinstance(skill, dict) else str(skill) 
                                   for skill in linkedin_data['skills']]
            else:
                profile['skills'] = []
        
        # Extract certifications
        if 'certifications' in linkedin_data and isinstance(linkedin_data['certifications'], list):
            profile['certifications'] = [cert.get('name', str(cert)) for cert in linkedin_data['certifications']]
        
        # Extract languages
        if 'languages' in linkedin_data and isinstance(linkedin_data['languages'], list):
            profile['languages'] = [lang.get('name', str(lang)) for lang in linkedin_data['languages']]
        
        # Use the standard evaluation method
        return self.evaluate_candidate_smart(profile, job_description)
    
    def _generate_criteria(self, context: Dict[str, str], job_description: str) -> Dict[str, Any]:
        """Generate elite hiring criteria based on context"""
        
        system_prompt = "You are an elite hiring expert. Always respond with valid JSON only, no markdown formatting."
        
        user_prompt = f"""
        Generate elite hiring criteria for this role using SRN Smart Hiring standards:
        
        Industry: {context['industry']}
        Company Type: {context['company_type']}
        Role Type: {context['role_type']}
        Role Subtype: {context['role_subtype']}
        
        Job Description:
        {job_description}
        
        Create criteria for top 1-2% performers who can thrive in elite environments.
        
        Return ONLY a JSON object with this structure:
        {{
            "education_requirements": "Elite university requirements or equivalent excellence",
            "core_skills": ["4-6 mission-critical skills - what they must DO, not just know"],
            "domain_expertise": ["4-6 technical/domain specific capabilities"],
            "experience_markers": ["3-4 indicators of high performance and ownership"],
            "company_preferences": ["Preferred company types, stages, or caliber"],
            "red_flags": ["3-4 disqualifying factors or concerning patterns"],
            "bonus_signals": ["3-4 exceptional indicators like OSS, publications, awards"]
        }}
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = self.llm_json.invoke(messages).content
            print(f"[DEBUG] Criteria response : {response}...")
            
            # Extract JSON from response
            criteria = self._extract_json_from_response(response)
            
            if criteria is None:
                print(f"[DEBUG] Failed to extract JSON from criteria response")
                criteria = self._get_fallback_criteria(context['role_type'])
            else:
                print(f"[DEBUG] Successfully extracted criteria JSON")
            
        except Exception as e:
            print(f"[DEBUG] OpenAI API failed: {e}. Using fallback criteria.")
            criteria = self._get_fallback_criteria(context['role_type'])
        
        return criteria
    
    def _evaluate_candidate(self, candidate_profile: Dict, criteria: Dict, context: Dict) -> Dict[str, Any]:
        """Evaluate candidate using SRN FitScore methodology"""
        # Build comprehensive candidate information
        candidate_sections = []
        
        # Add title/current role
        if candidate_profile.get('title'):
            candidate_sections.append(f"Current Role: {candidate_profile['title']}")
        
        # Add snippet/summary
        if candidate_profile.get('snippet'):
            candidate_sections.append(f"Summary: {candidate_profile['snippet']}")
        
        # Add education
        if candidate_profile.get('education'):
            candidate_sections.append(f"Education: {candidate_profile['education']}")
        
        # Add years of experience
        if candidate_profile.get('years_experience'):
            candidate_sections.append(f"Years of Experience: {candidate_profile['years_experience']}")
        
        # Add skills
        if candidate_profile.get('skills'):
            skills_list = candidate_profile['skills'] if isinstance(candidate_profile['skills'], list) else [candidate_profile['skills']]
            candidate_sections.append(f"Skills: {', '.join(skills_list)}")
        
        # Add any other fields that might be present
        additional_fields = ['companies', 'achievements', 'certifications', 'languages', 'location']
        for field in additional_fields:
            if candidate_profile.get(field):
                value = candidate_profile[field]
                if isinstance(value, list):
                    value = ', '.join(value)
                candidate_sections.append(f"{field.title()}: {value}")
        
        # Combine all sections
        candidate_text = '\n'.join(candidate_sections)
        
        # If we have very limited information, note that
        if not candidate_text.strip():
            candidate_text = "Limited candidate information available"
        
        system_prompt = "You are an elite hiring evaluator. Always respond with valid JSON only, no markdown formatting."
        
        user_prompt = f"""
        Evaluate this candidate using the SRN FitScore methodology on a 0-10 scale.
        
        CONTEXT:
        Industry: {context['industry']}
        Company Type: {context['company_type']}
        Role: {context['role_type']} - {context['role_subtype']}
        
        ELITE HIRING CRITERIA:
        {json.dumps(criteria, indent=2)}
        
        CANDIDATE PROFILE:
        {candidate_text}
        
        Return ONLY a JSON object with this exact structure:
        {{
            "scores": {{
                "education": ,
                "career_trajectory": ,
                "company_relevance": ,
                "tenure_stability": ,
                "core_skills": ,
                "bonus_signals": ,
                "red_flags": 
            }},
            "final_score": ,
            "strengths": ["Points where candidate is strong based on its skills and experience"],
            "weaknesses": ["Points where candidate can improve"],
            "rationale": "Reasoning behind the scores",
            "override_signal": false
        }}
        
        Replace the example values with your actual evaluation. Score conservatively - 8+ only for exceptional candidates.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = self.llm_json.invoke(messages).content
            print(f"[DEBUG] Evaluation response (first 200 chars): {response[:200]}...")
            
            # Extract and parse JSON
            evaluation_dict = self._extract_json_from_response(response)
            
            if evaluation_dict:
                # Validate against Pydantic model
                validated = EvaluationResponse(**evaluation_dict)
                evaluation = validated.dict()
                print(f"[DEBUG] Successfully parsed and validated evaluation JSON")
            else:
                print(f"[DEBUG] Could not extract valid JSON from evaluation response")
                raise ValueError("Could not extract valid JSON from response")
                    
        except Exception as e:
            print(f"[DEBUG] Evaluation failed: {e}. Using fallback evaluation.")
            evaluation = self._fallback_evaluation(candidate_text)
            
        return evaluation
    
    def _get_fallback_criteria(self, role_type: str) -> Dict[str, Any]:
        """Fallback criteria when API fails"""
        base_criteria = {
            "education_requirements": "Bachelor's+ from top-tier university or equivalent excellence",
            "core_skills": ["System design", "Production ownership", "Technical leadership", "Problem solving"],
            "domain_expertise": ["Cloud platforms", "Scalability", "Best practices", "Modern tools"],
            "experience_markers": ["Ownership of outcomes", "Scale challenges", "Technical impact"],
            "company_preferences": ["High-growth companies", "Technical excellence culture"],
            "red_flags": ["Job hopping", "No ownership", "Buzzword resumes"],
            "bonus_signals": ["Open source", "Technical writing", "Speaking", "Awards"]
        }
        
        # Customize by role type
        if role_type == "DevOps Engineer":
            base_criteria["core_skills"] = ["Infrastructure as Code", "Kubernetes orchestration", "CI/CD pipeline design", "Cloud architecture"]
            base_criteria["domain_expertise"] = ["AWS/GCP/Azure", "Terraform/Pulumi", "Monitoring systems", "Security best practices"]
        elif role_type == "Data Scientist":
            base_criteria["core_skills"] = ["Machine learning implementation", "Statistical analysis", "Data pipeline design", "Model deployment"]
            base_criteria["domain_expertise"] = ["Python/R", "TensorFlow/PyTorch", "SQL/NoSQL", "MLOps practices"]
        
        return base_criteria
    
    def _fallback_evaluation(self, candidate_text: str) -> Dict[str, Any]:
        """Fallback evaluation when API fails"""
        return {
            "scores": {
                "education": 6.0,
                "career_trajectory": 6.0,
                "company_relevance": 6.0,
                "tenure_stability": 6.0,
                "core_skills": 6.0,
                "bonus_signals": 2.0,
                "red_flags": 0.0
            },
            "final_score": 6.0,
            "strengths": ["Professional experience visible"],
            "weaknesses": ["Limited profile information"],
            "rationale": "Assessment based on limited LinkedIn data. Full evaluation requires detailed resume.",
            "override_signal": False
        }
    
    def _generate_recommendation(self, score: float) -> str:
        """Generate hiring recommendation based on SRN FitScore"""
        if score >= 8.5:
            return "🟢 STRONG HIRE - Exceptional candidate meeting elite standards"
        elif score >= 7.0:
            return "🟡 CONSIDER - Good candidate, requires additional evaluation"
        elif score >= 5.5:
            return "🟠 WEAK - Below standards, significant concerns"
        else:
            return "🔴 NO HIRE - Does not meet minimum requirements"

    def evaluate_candidate_from_summary(self, candidate_summary: str, job_description: str) -> dict:
        """
        Takes a candidate summary string (from summarize_apify_profile) and a job description,
        parses the summary into a candidate_profile dict, and evaluates using evaluate_candidate_smart.
        Returns the full evaluation report or an error if parsing fails.
        """
        try:
            lines = candidate_summary.split('\n')
            profile = {}
            
            # Parse each line and extract information
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Name:'):
                    name = line.replace('Name:', '').strip()
                    # Keep name but also set it as title if no current role found
                    profile['name'] = name
                    if 'title' not in profile:
                        profile['title'] = name
                elif line.startswith('Current Role & Company:'):
                    role_company = line.replace('Current Role & Company:', '').strip()
                    profile['title'] = role_company
                    # Try to extract company separately if possible
                    if ' at ' in role_company:
                        role, company = role_company.split(' at ', 1)
                        profile['current_role'] = role.strip()
                        profile['current_company'] = company.strip()
                elif line.startswith('Education:'):
                    profile['education'] = line.replace('Education:', '').strip()
                elif line.startswith('Total Year of experiences:') or line.startswith('Total Years of Experience:'):
                    years = line.split(':', 1)[1].strip()
                    profile['years_experience'] = years
                elif line.startswith('Skills from experiences:') or line.startswith('Skills:'):
                    skills_text = line.split(':', 1)[1].strip()
                    profile['skills'] = [s.strip() for s in skills_text.split(',') if s.strip()]
                elif line.startswith('Previous Companies:') or line.startswith('Companies:'):
                    companies_text = line.split(':', 1)[1].strip()
                    profile['companies'] = [c.strip() for c in companies_text.split(',') if c.strip()]
                elif line.startswith('Location:'):
                    profile['location'] = line.replace('Location:', '').strip()
                elif line.startswith('Achievements:') or line.startswith('Key Achievements:'):
                    achievements_text = line.split(':', 1)[1].strip()
                    profile['achievements'] = achievements_text
                elif line.startswith('Summary:') or line.startswith('Profile Summary:'):
                    profile['snippet'] = line.split(':', 1)[1].strip()
                # Add more field parsers as needed
            
            # Build a comprehensive snippet if not already present
            if 'snippet' not in profile:
                snippet_parts = []
                if profile.get('current_role'):
                    snippet_parts.append(f"{profile['current_role']}")
                if profile.get('current_company'):
                    snippet_parts.append(f"at {profile['current_company']}")
                if profile.get('years_experience'):
                    snippet_parts.append(f"with {profile['years_experience']} experience")
                
                if snippet_parts:
                    profile['snippet'] = ' '.join(snippet_parts)
                else:
                    profile['snippet'] = 'Professional with relevant experience'
            
            # Ensure required fields exist
            if 'title' not in profile:
                if profile.get('name'):
                    profile['title'] = profile['name']
                else:
                    profile['title'] = 'Unknown Professional'
            
            # Debug print to see what we extracted
            print(f"[DEBUG] Extracted profile fields: {list(profile.keys())}")
            
            # Use evaluate_candidate_smart for main evaluation
            return self.evaluate_candidate_smart(profile, job_description)
        except Exception as e:
            return {"error": f"Failed to parse candidate summary: {str(e)}"}

if __name__ == "__main__":
    # Test the smart evaluator
    evaluator = SmartEvaluator()
    
    job_description = """
    Senior Frontend Engineer
    San Francisco, California
    Engineering / On-site
    
    We're building the future of B2B SaaS and need an exceptional frontend engineer to lead our user experience.
    
    Responsibilities:
    * Architect and implement scalable frontend solutions using React/Next.js
    * Collaborate with design and product teams to create intuitive interfaces
    * Optimize performance and ensure cross-browser compatibility
    * Mentor junior engineers and contribute to technical strategy
    
    Requirements:
    * 5+ years of frontend development experience
    * Expert-level React and TypeScript skills
    * Experience with modern frontend tooling and CI/CD
    * Strong understanding of UX/UI principles
    """
    
    # Example 1: Basic profile
    basic_profile = {
        "title": "Senior Frontend Engineer at Stripe",
        "snippet": "MIT Computer Science graduate with 6 years building scalable frontend systems. Led redesign of Stripe Dashboard serving millions of users. Expert in React, TypeScript, and performance optimization."
    }
    
    # Example 2: Comprehensive profile
    comprehensive_profile = {
        "name": "Jane Smith",
        "title": "Senior Frontend Engineer at Stripe",
        "snippet": "Passionate about building delightful user experiences at scale",
        "education": "B.S. Computer Science, MIT (2016); M.S. Human-Computer Interaction, Stanford (2018)",
        "years_experience": "6 years",
        "skills": ["React", "TypeScript", "Next.js", "GraphQL", "Node.js", "AWS", "System Design", "Team Leadership"],
        "companies": ["Stripe", "Airbnb", "Facebook"],
        "current_role": "Senior Frontend Engineer",
        "current_company": "Stripe",
        "achievements": "Led redesign of Stripe Dashboard (10M+ users), Reduced page load time by 60%, Mentored 5 junior engineers",
        "certifications": ["AWS Certified Solutions Architect"],
        "location": "San Francisco, CA"
    }
    
    # Example 3: Testing candidate summary parsing
    candidate_summary = """
    Name: John Doe
    Current Role & Company: Staff Engineer at Google
    Education: PhD Computer Science from Stanford University, BS from UC Berkeley
    Total Years of Experience: 10 years
    Skills from experiences: React, TypeScript, Python, Kubernetes, System Design, Technical Leadership
    Previous Companies: Google, Meta, Microsoft
    Key Achievements: Built Gmail's new frontend architecture, Led team of 15 engineers
    Location: Mountain View, CA
    """
    
    print("=" * 80)
    print("Testing with basic profile:")
    result1 = evaluator.evaluate_candidate_smart(basic_profile, job_description)
    print(f"\n🎯 Fit Score: {result1['fit_score']}/10.0")
    print(f"💡 Recommendation: {result1['recommendation']}")
    
    print("\n" + "=" * 80)
    print("Testing with comprehensive profile:")
    result2 = evaluator.evaluate_candidate_smart(comprehensive_profile, job_description)
    print(f"\n🎯 Fit Score: {result2['fit_score']}/10.0")
    print(f"💡 Recommendation: {result2['recommendation']}")
    
    print("\n" + "=" * 80)
    print("Testing candidate summary parsing:")
    result3 = evaluator.evaluate_candidate_from_summary(candidate_summary, job_description)
    print(f"\n🎯 Fit Score: {result3['fit_score']}/10.0")
    print(f"💡 Recommendation: {result3['recommendation']}")
