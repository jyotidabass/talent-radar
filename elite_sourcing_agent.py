from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import time
import re
import streamlit as st
# Import the Elite components
from smart_evaluator import SmartEvaluator, SmartContextDetector
from search_generator import SearchQueryGenerator
from linkedin_xray_search import LinkedInXRaySearch

load_dotenv()

@dataclass
class AgentMemory:
    """Memory storage for the agent's learning and optimization"""
    successful_searches: List[Dict[str, Any]] = None
    candidate_evaluations: List[Dict[str, Any]] = None
    search_patterns: List[Dict[str, Any]] = None
    performance_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.successful_searches is None:
            self.successful_searches = []
        if self.candidate_evaluations is None:
            self.candidate_evaluations = []
        if self.search_patterns is None:
            self.search_patterns = []
        if self.performance_metrics is None:
            self.performance_metrics = {
                "search_success_rate": 0.0,
                "candidate_match_rate": 0.0,
                "average_response_time": 0.0
            }

class JobDescriptionAnalyzer:
    """Enhanced analyzer for job descriptions with industry classification and skill extraction"""
    
    def __init__(self):
        self.job_families = {
            "engineering": ["engineer", "developer", "programmer", "swe", "devops", "infrastructure", "backend", "frontend", "fullstack", "mobile", "platform", "site reliability", "sre"],
            "data": ["data scientist", "ml engineer", "ai engineer", "data engineer", "analyst", "machine learning", "artificial intelligence", "data analyst"],
            "product": ["product manager", "pm", "product owner", "product lead", "chief product officer", "cpo"],
            "design": ["designer", "ux", "ui", "creative", "design lead", "art director", "visual designer"],
            "sales": ["sales", "account executive", "account manager", "sales rep", "business development", "bdr", "sdr"],
            "marketing": ["marketing", "growth", "content", "brand", "digital marketing", "social media", "seo", "sem"],
            "finance": ["finance", "accounting", "controller", "cfo", "analyst", "fp&a", "tax", "audit", "cpa"],
            "legal": ["lawyer", "attorney", "counsel", "legal", "paralegal", "compliance"],
            "operations": ["operations", "project manager", "program manager", "business analyst", "consultant"],
            "hr": ["hr", "human resources", "recruiter", "talent", "people operations", "chief people officer"],
            "executive": ["ceo", "cfo", "cto", "coo", "chief", "vp", "vice president", "director", "head of"]
        }
        
        self.seniority_levels = {
            "entry": ["junior", "entry", "associate", "intern", "new grad", "recent graduate", "1-2 years"],
            "mid": ["mid", "2-5 years", "3-6 years", "intermediate"],
            "senior": ["senior", "sr", "5+ years", "6+ years", "lead", "principal", "staff"],
            "executive": ["director", "vp", "vice president", "chief", "ceo", "cfo", "cto", "coo", "head of"]
        }
        
        self.industries = {
            "tech": ["tech", "software", "saas", "platform", "ai", "ml", "startup", "fintech", "edtech", "healthtech"],
            "finance": ["finance", "banking", "investment", "trading", "insurance", "fintech", "hedge fund", "private equity"],
            "healthcare": ["healthcare", "medical", "hospital", "pharma", "biotech", "health tech", "clinical"],
            "consulting": ["consulting", "mckinsey", "bain", "bcg", "deloitte", "pwc", "accenture"],
            "retail": ["retail", "ecommerce", "consumer", "fashion", "cpg", "fmcg"]
        }
        
        # Enhanced technical skills patterns
        self.technical_skills = {
            # Programming Languages
            "programming": r"\b(python|javascript|java|c\+\+|golang|rust|typescript|ruby|php|scala|kotlin|swift|objective-c|c#|r|matlab)\b",
            
            # Cloud & Infrastructure
            "cloud": r"\b(aws|azure|gcp|google cloud|amazon web services|docker|kubernetes|terraform|pulumi|cloudformation|helm|istio)\b",
            
            # Databases
            "databases": r"\b(postgresql|mysql|mongodb|redis|elasticsearch|dynamodb|cassandra|snowflake|bigquery|databricks)\b",
            
            # DevOps & Tools
            "devops": r"\b(jenkins|gitlab ci|github actions|ansible|chef|puppet|docker|kubernetes|prometheus|grafana|datadog|splunk)\b",
            
            # Frontend
            "frontend": r"\b(react|angular|vue|svelte|next\.js|nuxt|webpack|vite|sass|less|tailwind|bootstrap)\b",
            
            # Backend
            "backend": r"\b(node\.js|express|django|flask|spring|rails|laravel|fastapi|graphql|rest api|microservices)\b",
            
            # ML/AI
            "ml_ai": r"\b(tensorflow|pytorch|scikit-learn|pandas|numpy|jupyter|mlflow|kubeflow|langchain|openai|hugging face|transformers)\b",
            
            # Finance/Accounting
            "finance": r"\b(gaap|ifrs|sox|cpa|cfa|frm|quickbooks|sap|oracle financials|hyperion|cognos|tableau|power bi)\b",
            
            # Legal
            "legal": r"\b(westlaw|lexisnexis|clio|contracts|litigation|ip|patent|trademark|compliance|gdpr|ccpa)\b"
        }

    def analyze_job(self, job_description: str) -> Dict[str, Any]:
        """Comprehensive job analysis"""
        text = job_description.lower()
        
        # Analyze job family
        job_family = self._classify_job_family(text)
        
        # Analyze seniority
        seniority = self._detect_seniority(text)
        
        # Analyze industry
        industry = self._detect_industry(text)
        
        # Extract skills
        skills = self._extract_skills(text)
        
        # Extract locations
        locations = self._extract_locations(job_description)
        
        # Determine if role is technical/leadership/remote-eligible
        is_technical = job_family in ["engineering", "data"] or any(skills.values())
        is_leadership = seniority in ["senior", "executive"] or any(term in text for term in ["lead", "manager", "director", "head"])
        remote_eligible = any(term in text for term in ["remote", "distributed", "work from home", "wfh"])
        
        return {
            "job_family": job_family,
            "seniority": seniority,
            "industry": industry,
            "skills": skills,
            "locations": locations,
            "is_technical": is_technical,
            "is_leadership": is_leadership,
            "remote_eligible": remote_eligible,
            "total_skills": sum(len(v) for v in skills.values())
        }
    
    def _classify_job_family(self, text: str) -> str:
        """Classify job into family category with specific logic for product engineers"""
        text_lower = text.lower()
        
        # Special handling for Product Engineers - they are Software Engineers, not Product Managers
        if any(term in text_lower for term in ['product engineer', 'full-stack product engineer', 'full stack product engineer']):
            return "engineering"
        
        # Regular classification for other roles
        family_scores = {}
        for family, keywords in self.job_families.items():
            # Skip "product" family for engineer titles to avoid confusion
            if family == "product" and any(eng_term in text_lower for eng_term in ['engineer', 'developer', 'programmer']):
                continue
                
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                family_scores[family] = score
        
        result = max(family_scores.items(), key=lambda x: x[1])[0] if family_scores else "engineering"
        print(f"🔍 JOB FAMILY CLASSIFICATION: '{result}' (scores: {family_scores})")
        return result
    
    def _detect_seniority(self, text: str) -> str:
        """Detect seniority level"""
        for level, keywords in self.seniority_levels.items():
            if any(keyword in text for keyword in keywords):
                return level
        return "mid"  # Default
    
    def _detect_industry(self, text: str) -> str:
        """Detect industry"""
        for industry, keywords in self.industries.items():
            if any(keyword in text for keyword in keywords):
                return industry
        return "tech"  # Default
    
    def _extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract technical skills by category"""
        skills = {}
        for category, pattern in self.technical_skills.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills[category] = list(set(matches)) if matches else []
        return skills
    
    def _extract_locations(self, text: str) -> List[str]:
        """Extract and standardize location information"""
        locations = []
        text_lower = text.lower()
        
        # Common location patterns
        location_patterns = {
            'san francisco': ['San Francisco', 'SF', 'Bay Area'],
            'new york': ['New York', 'NYC', 'Manhattan'],
            'los angeles': ['Los Angeles', 'LA', 'Southern California'],
            'seattle': ['Seattle', 'Bellevue', 'Pacific Northwest'],
            'austin': ['Austin', 'Texas'],
            'boston': ['Boston', 'Cambridge', 'Massachusetts'],
            'chicago': ['Chicago', 'Illinois'],
            'denver': ['Denver', 'Colorado'],
            'california': ['California', 'CA', 'Bay Area'],
            'remote': ['remote', 'distributed', 'work from home']
        }
        
        # Enhanced pattern matching
        for location_key, variations in location_patterns.items():
            # Check if location key is in text (e.g., "san francisco" in "San Francisco, California")
            if location_key in text_lower:
                locations.extend(variations[:3])  # Take first 3 variations
                print(f"🎯 LOCATION DETECTED: {location_key} -> {variations[:3]}")
            # Also check each variation
            elif any(var.lower() in text_lower for var in variations):
                locations.extend(variations[:3])
                print(f"🎯 LOCATION DETECTED: {location_key} via variations -> {variations[:3]}")
        
        # Remove duplicates while preserving order
        unique_locations = []
        for loc in locations:
            if loc not in unique_locations:
                unique_locations.append(loc)
        
        result = unique_locations if unique_locations else ['remote']
        print(f"🗺️ FINAL LOCATIONS: {result}")
        return result

class EliteSourcingAgent:
    """🎖️ Elite Candidate Sourcing Agent with SRN FitScore Methodology"""
    
    def __init__(self):
        """Initialize the Elite Sourcing Agent with all components"""
        # Import components dynamically to avoid circular imports
        try:
            from smart_evaluator import SmartEvaluator, SmartContextDetector
            from search_generator import SearchQueryGenerator
            from linkedin_xray_search import LinkedInXRaySearch
            
            self.smart_evaluator = SmartEvaluator()
            self.context_detector = SmartContextDetector()
            self.search_generator = SearchQueryGenerator()
            self.linkedin_searcher = LinkedInXRaySearch()
        except ImportError as e:
            print(f"Warning: Could not import Elite components: {e}")
            self.smart_evaluator = None
            self.context_detector = None
            self.search_generator = None
            self.linkedin_searcher = None
        
        # API configuration
        self.api_key =st.secrets["OPENAI_API_KEY"]
        self.google_api_key = st.secrets["GOOGLE_API_KEY"]
        self.search_engine_id = st.secrets["SEARCH_ENGINE_ID"]
        
        # Performance tracking
        self.query_performance = []

    def search_candidates(self, job_description: str, num_candidates: int = 10, elite_threshold: float = 8.5, progress_callback=None) -> Dict[str, Any]:
        """🚀 Elite Candidate Search with SRN FitScore Evaluation"""
        
        start_time = time.time()
        
        print(f"🎖️ STARTING ELITE CANDIDATE SEARCH")
        print(f"🎯 Target: {num_candidates} candidates with SRN FitScore {elite_threshold}+")
        
        # Step 1: Smart Context Detection
        if progress_callback:
            progress_callback("🧠 Analyzing job context...", 10)
        
        context = self._detect_context(job_description) if self.context_detector else self._fallback_context()
        print(f"✅ Smart Context Detection:")
        print(f"   - Industry: {context['industry']}")
        print(f"   - Company Type: {context['company_type']}")
        print(f"   - Role Type: {context['role_type']}")
        print(f"   - Role Subtype: {context['role_subtype']}")
        
        # Step 2: Generate Elite Search Queries
        if progress_callback:
            progress_callback("🎯 Generating elite search queries...", 20)
        
        queries = self._generate_elite_queries(job_description, context)
        print(f"✅ Generated {len(queries)} Elite Search Queries")
        
        # Step 3: Execute Progressive Search
        if progress_callback:
            progress_callback("🔍 Executing progressive search...", 30)
        
        all_candidates = []
        unique_urls = set()
        
        for i, query in enumerate(queries):
            print(f"\n🔍 Query {i+1}/{len(queries)}: {query[:80]}...")
            
            # Execute search
            results = self._execute_google_search(query, num_results=25)
            
            if results:
                linkedin_profiles = self._filter_linkedin_profiles(results)
                
                # Track performance
                self.query_performance.append({
                    "query": query[:80] + "..." if len(query) > 80 else query,
                    "total_results": len(results),
                    "linkedin_profiles": len(linkedin_profiles),
                    "strategy": f"elite_query_{i+1}",
                    "description": f"Elite progressive query {i+1}"
                })
                
                # Deduplicate
                new_profiles = 0
                for profile in linkedin_profiles:
                    if profile["link"] not in unique_urls:
                        unique_urls.add(profile["link"])
                        all_candidates.append(profile)
                        new_profiles += 1
                
                print(f"  📈 Found {len(linkedin_profiles)} profiles, {new_profiles} new unique")
            else:
                print(f"  ❌ No results for query {i+1}")
        
        print(f"\n✅ Search Complete: {len(all_candidates)} unique candidates found")
        
        # Step 4: Elite SRN FitScore Evaluation
        if progress_callback:
            progress_callback("⚡ Elite SRN FitScore evaluation...", 60)
        
        print(f"⚡ Starting Elite SRN FitScore Evaluation for {len(all_candidates)} candidates...")
        
        scored_candidates = []
        elite_candidates = []
        
        for i, candidate in enumerate(all_candidates):
            if progress_callback and i % 10 == 0:
                eval_progress = 60 + (30 * i / len(all_candidates))
                progress_callback(f"⚡ Evaluating {i+1}/{len(all_candidates)}...", eval_progress)
            
            try:
                # Use Elite Smart Evaluator for SRN FitScore
                if self.smart_evaluator:
                    evaluation = self.smart_evaluator.evaluate_candidate_smart(candidate, job_description)
                else:
                    evaluation = self._fallback_evaluation(candidate)
                
                enhanced_candidate = {
                    **candidate,
                    "srn_evaluation": evaluation,
                    "fit_score": evaluation["fit_score"],
                    "recommendation": evaluation["recommendation"],
                    "context": evaluation.get("context", context),
                    "hiring_criteria": evaluation.get("hiring_criteria", {})
                }
                
                scored_candidates.append(enhanced_candidate)
                
                # Track elite candidates
                if enhanced_candidate["fit_score"] >= elite_threshold:
                    elite_candidates.append(enhanced_candidate)
                    print(f"🏆 ELITE CANDIDATE: {candidate.get('title', 'Unknown')[:50]} - Score: {enhanced_candidate['fit_score']:.1f}")
                
            except Exception as e:
                print(f"❌ Evaluation failed for candidate {i+1}: {str(e)}")
                continue
        
        # Step 5: Rank and Return Elite Results
        if progress_callback:
            progress_callback("🏆 Ranking elite candidates...", 90)
        
        # Sort all candidates by SRN FitScore
        scored_candidates.sort(key=lambda x: x["fit_score"], reverse=True)
        top_candidates = scored_candidates[:num_candidates]
        
        # Final results
        end_time = time.time()
        total_time = end_time - start_time
        
        if progress_callback:
            progress_callback("✅ Elite search completed!", 100)
        
        print(f"\n🎉 ELITE SEARCH COMPLETED!")
        print(f"⏱️  Total Time: {total_time:.2f}s")
        print(f"🎖️ Elite Candidates Found: {len(elite_candidates)} (score {elite_threshold}+)")
        print(f"📊 Total Evaluated: {len(scored_candidates)}")
        print(f"🏆 Returning Top {len(top_candidates)} Candidates")
        
        return {
            "candidates": top_candidates,
            "total_found": len(scored_candidates),
            "elite_found": len(elite_candidates),
            "search_time": total_time,
            "query_performance": self.query_performance,
            "context": context,
            "elite_threshold": elite_threshold,
            "queries_used": [{"query": q["query"], "description": q["description"]} for q in self.query_performance]
        }
    
    def _detect_context(self, job_description: str) -> Dict[str, str]:
        """Detect smart context from job description"""
        if self.context_detector:
            return self.context_detector.detect_context(job_description)
        return self._fallback_context()
    
    def _fallback_context(self) -> Dict[str, str]:
        """Fallback context when smart detection fails"""
        return {
            "industry": "Tech",
            "company_type": "Enterprise",
            "role_type": "Software Engineer",
            "role_subtype": "General"
        }
    
    def _generate_elite_queries(self, job_description: str, context: Dict) -> List[str]:
        """Generate elite-focused LinkedIn X-Ray search queries"""
        
        # Elite query patterns based on context
        role_type = context.get('role_type', 'Software Engineer')
        industry = context.get('industry', 'Tech')
        company_type = context.get('company_type', 'Enterprise')
        
        queries = []
        
        # Elite Query 1: Role + Elite Companies
        if 'Engineer' in role_type:
            elite_companies = '"Google" OR "Apple" OR "Microsoft" OR "Amazon" OR "Meta" OR "Netflix"'
            queries.append(f'site:linkedin.com/in/ "{role_type}" ({elite_companies}) "5+ years"')
        
        # Elite Query 2: Role + Top Universities
        elite_universities = '"Stanford" OR "MIT" OR "Harvard" OR "CMU" OR "Berkeley"'
        queries.append(f'site:linkedin.com/in/ "{role_type}" ({elite_universities})')
        
        # Elite Query 3: Role + Industry Leaders
        if industry == 'Tech':
            industry_leaders = '"startup" OR "YC" OR "venture" OR "Series A" OR "Series B"'
            queries.append(f'site:linkedin.com/in/ "{role_type}" ({industry_leaders})')
        
        # Elite Query 4: Senior + Technical Skills
        if 'DevOps' in role_type or 'Engineer' in role_type:
            tech_skills = '"AWS" OR "Kubernetes" OR "Terraform" OR "Python"'
            queries.append(f'site:linkedin.com/in/ "Senior {role_type}" ({tech_skills})')
        
        # Elite Query 5: Leadership + Experience
        queries.append(f'site:linkedin.com/in/ ("Lead {role_type}" OR "Principal {role_type}") "team"')
        
        return queries[:5]  # Return top 5 elite queries
    
    def _execute_google_search(self, query: str, num_results: int = 25) -> List[Dict]:
        """Execute Google Custom Search API"""
        all_results = []
        
        try:
            if not self.google_api_key or not self.search_engine_id:
                raise Exception("Google API keys not configured")
            
            params = {
                "key": self.google_api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": min(num_results, 10)  # Google CSE max per request
            }
            
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
            response.raise_for_status()
            data = response.json()
            
            if "items" in data:
                all_results.extend(data["items"])
                
        except Exception as e:
            print(f"❌ Google Search API error: {str(e)}")
            raise Exception(f"Google search failed: {str(e)}")
        
        return all_results
    
    def _filter_linkedin_profiles(self, search_results: List[Dict]) -> List[Dict]:
        """Filter and clean LinkedIn profile results"""
        linkedin_profiles = []
        
        for item in search_results:
            link = item.get("link", "")
            
            # Check if it's a LinkedIn profile
            if "linkedin.com/in/" in link:
                profile = {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": link,
                    "source": "linkedin_elite"
                }
                linkedin_profiles.append(profile)
        
        return linkedin_profiles
    
    def _fallback_evaluation(self, candidate: Dict) -> Dict[str, Any]:
        """Fallback evaluation when Smart Evaluator is not available"""
        # Simple scoring based on keywords
        title = candidate.get('title', '').lower()
        snippet = candidate.get('snippet', '').lower()
        text = f"{title} {snippet}"
        
        score = 6.0  # Base score
        
        # Elite company bonus
        elite_companies = ['google', 'apple', 'microsoft', 'amazon', 'meta', 'netflix', 'stripe', 'openai']
        if any(company in text for company in elite_companies):
            score += 1.5
        
        # Elite university bonus
        elite_schools = ['stanford', 'mit', 'harvard', 'cmu', 'berkeley', 'princeton', 'caltech']
        if any(school in text for school in elite_schools):
            score += 1.0
        
        # Senior experience bonus
        if any(term in text for term in ['senior', 'lead', 'principal', 'staff', '7+ years', '8+ years']):
            score += 0.8
        
        # Technical skills bonus
        tech_skills = ['python', 'javascript', 'aws', 'kubernetes', 'terraform', 'react', 'node.js']
        skill_count = sum(1 for skill in tech_skills if skill in text)
        score += min(skill_count * 0.2, 1.0)
        
        # Cap at 10.0
        score = min(score, 10.0)
        
        recommendation = self._generate_recommendation(score)
        
        return {
            "fit_score": score,
            "recommendation": recommendation,
            "evaluation": {
                "strengths": ["Professional experience", "Industry background"],
                "weaknesses": ["Limited profile data for full assessment"],
                "rationale": f"Score based on profile keywords and elite indicators. Full evaluation requires detailed resume."
            }
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

    def get_linkedin_urls_from_job_description(self, job_description: str) -> set:
        """
        Given a job description, return a set of unique LinkedIn profile URLs found via Google Custom Search.
        This uses context detection, elite query generation, and LinkedIn filtering logic.
        """
        # Step 1: Detect context
        context = self._detect_context(job_description) if self.context_detector else self._fallback_context()

        # Step 2: Generate elite queries
        queries = self._generate_elite_queries(job_description, context)

        # Step 3: Execute search and collect LinkedIn URLs
        unique_urls = set()
        for query in queries:
            try:
                results = self._execute_google_search(query, num_results=25)
                linkedin_profiles = self._filter_linkedin_profiles(results)
                for profile in linkedin_profiles:
                    url = profile.get("link")
                    if url:
                        unique_urls.add(url)
            except Exception as e:
                print(f"Error during search for query '{query}': {e}")
                continue
        return unique_urls

if __name__ == "__main__":
    # Test the Elite Sourcing Agent
    agent = EliteSourcingAgent()
    
    # Sample elite job description
    job_description = """
    Senior DevOps Engineer
    San Francisco, California
    Engineering / On-site
    
    Ivo AI is building tools to help every company in the world make sense of their contracts. 
    The tools are getting popular - we've just raised a $16M Series A. Now, we need your help.
    
    What we're looking for:
    We're looking for a seasoned DevOps engineer to:
    - Own and shape the future of our environment
    - Manage dozens, hundreds, thousands of customer deployments
    - Instrument our system so we understand performance bottlenecks, errors, etc.
    - Get our CI/CD system running super quickly (it currently takes ~12 minutes)
    
    About you:
    - Passionate about orchestration and Infrastructure as Code. We're currently using Pulumi
    - Want to move quickly while striving for best practices
    - Can write code, preferably JavaScript
    - Experienced with either Azure and or GCP
    - Deeply knowledgeable about computers. Linux systems, containers, SQL databases, cloud infrastructure
    - 5+ years experience with Infrastructure as Code
    """
    
    # Search for elite candidates
    results = agent.search_candidates(job_description, num_candidates=5, elite_threshold=8.5)
    
    print("\n" + "="*80)
    print("🎖️ ELITE CANDIDATE SOURCING RESULTS")
    print("="*80)
    
    # Show context and analysis
    print(f"\n📊 Smart Context Analysis:")
    print(f"   Industry: {results['context']['industry']}")
    print(f"   Company Type: {results['context']['company_type']}")
    print(f"   Role Type: {results['context']['role_type']}")
    print(f"   Role Subtype: {results['context']['role_subtype']}")
    
    # Show top elite candidates
    print(f"\n🏆 Top Elite Candidates (SRN FitScore {results['elite_threshold']}+):")
    for i, candidate in enumerate(results["candidates"][:3]):
        print(f"\n   Candidate {i+1}:")
        print(f"   Title: {candidate['title']}")
        print(f"   SRN FitScore: {candidate['fit_score']}/10.0")
        print(f"   Recommendation: {candidate['recommendation']}")
        print(f"   Profile: {candidate['link']}")
    
    # Show performance summary
    print(f"\n📊 Search Performance:")
    print(f"   Elite Candidates Found: {results['elite_found']}")
    print(f"   Total Candidates Evaluated: {results['total_found']}")
    print(f"   Search Time: {results['search_time']:.2f}s")
    print(f"   Queries Used: {len(results['queries_used'])}") 
