#!/usr/bin/env python3
"""
Search Query Generator

Generates effective LinkedIn X-ray search queries using progressive relaxation strategy.
Starts specific and gets broader to ensure results while maintaining quality.
"""

from typing import Dict, List, Any
import re

class SearchQueryGenerator:
    """Generates LinkedIn X-ray search queries with progressive relaxation"""
    
    def __init__(self):
        # Title variation mappings
        self.title_variations = {
            "Full-Stack Product Engineer": [
                "Software Engineer", "Product Engineer", "Full Stack Developer", 
                "Senior Software Engineer", "Frontend Engineer", "Backend Engineer"
            ],
            "Product Engineer": [
                "Software Engineer", "Product Engineer", "Product Developer",
                "Frontend Engineer", "Backend Engineer", "Full Stack Engineer"
            ],
            "Software Engineer": [
                "Software Engineer", "Developer", "Software Developer",
                "Senior Software Engineer", "Programmer", "Software Engineer"
            ],
            "DevOps Engineer": [
                "DevOps Engineer", "Infrastructure Engineer", "Site Reliability Engineer",
                "Platform Engineer", "Cloud Engineer", "Systems Engineer"
            ],
            "Data Scientist": [
                "Data Scientist", "ML Engineer", "Machine Learning Engineer",
                "AI Engineer", "Data Engineer", "Research Scientist"
            ],
            "Product Manager": [
                "Product Manager", "Senior Product Manager", "Product Owner",
                "Product Lead", "PM", "Technical Product Manager"
            ]
        }
        
        # Location variations and mappings
        self.location_variations = {
            "San Francisco": ["San Francisco", "SF", "Bay Area", "Silicon Valley"],
            "New York": ["New York", "NYC", "Manhattan", "Brooklyn"],
            "Los Angeles": ["Los Angeles", "LA", "Southern California"],
            "Seattle": ["Seattle", "Redmond", "Bellevue", "Washington"],
            "Boston": ["Boston", "Cambridge", "Massachusetts", "MA"],
            "Austin": ["Austin", "Texas", "TX"],
            "Denver": ["Denver", "Colorado", "Boulder"],
            "Chicago": ["Chicago", "Illinois", "IL"],
            "Remote": ["Remote", "Distributed", "Work from home", "WFH"]
        }
        
        # Enhanced Company type signals with more granular industry mapping
        self.company_signals = {
            "construction_tech": [
                # Direct Construction Tech
                "Procore", "PlanGrid", "BuildZoom", "Assignar", "eSUB", "Fieldwire", 
                "Buildertrend", "CoConstruct", "HCSS", "Sage Construction",
                # Field Services & Contractor SaaS
                "ServiceTitan", "Knowify", "Jobber", "Housecall Pro", "mHelpDesk",
                "WorkWave", "Kickserv", "ServiceMax", "FieldEdge", "SimPRO",
                # Operations & Workflow Platforms
                "Monday.com", "Asana", "Smartsheet", "Airtable", "ClickUp",
                # Supply Chain & Logistics
                "Flexport", "Convoy", "FreightWaves", "project44", "Shipwell"
            ],
            "field_services": [
                "ServiceTitan", "Jobber", "Housecall Pro", "FieldEdge", "ServiceMax",
                "WorkWave", "mHelpDesk", "Kickserv", "ServicePro", "PestPac",
                "Route4Me", "Samsara", "Fleetio", "Verizon Connect", "Teletrac Navman"
            ],
            "b2b_saas_startup": [
                # High-growth B2B SaaS
                "Retool", "Linear", "Vanta", "LaunchDarkly", "Ramp", "Rippling", 
                "Airbase", "Brex", "Mercury", "Clerk", "PostHog", "Segment",
                "Mixpanel", "Amplitude", "Datadog", "PagerDuty", "Sentry",
                # YC/A16Z Portfolio
                "Stripe", "Plaid", "Figma", "Notion", "Airtable", "Zapier",
                "Loom", "Cal.com", "Vercel", "PlanetScale", "Supabase"
            ],
            "logistics_operations": [
                "Flexport", "Convoy", "Uber Freight", "Shipwell", "project44",
                "FourKites", "FreightWaves", "Samsara", "Motive", "KeepTruckin",
                "Route4Me", "OptimoRoute", "Onfleet", "GetSwift", "Bringg"
            ],
            "fintech_b2b": [
                "Stripe", "Plaid", "Ramp", "Brex", "Mercury", "Airbase",
                "Bill.com", "Coupa", "Tipalti", "Navan", "Divvy", "Expensify"
            ],
            "enterprise_saas": [
                "Salesforce", "ServiceNow", "Workday", "Oracle", "SAP",
                "Microsoft", "Adobe", "Atlassian", "Slack", "Zoom", "Dropbox"
            ],
            "big_tech": ["Google", "Apple", "Microsoft", "Amazon", "Meta", "Netflix", "FAANG"],
            "startup": ["startup", "Series A", "Series B", "funded", "venture", "YC", "Techstars"]
        }
        
        # Enhanced industry context mapping
        self.industry_context = {
            "construction_tech": {
                "adjacent_industries": ["field_services", "logistics_operations", "b2b_saas_startup"],
                "keywords": ["contractor", "construction", "field service", "blue collar", "operations", "workflow"],
                "avoid": ["pure frontend", "gaming", "consumer apps", "social media"]
            },
            "field_services": {
                "adjacent_industries": ["construction_tech", "logistics_operations", "b2b_saas_startup"],
                "keywords": ["field technician", "mobile workforce", "service management", "scheduling"],
                "avoid": ["office-only", "desk job", "pure analytics"]
            },
            "fintech": {
                "adjacent_industries": ["b2b_saas_startup", "enterprise_saas"],
                "keywords": ["payments", "financial", "banking", "compliance", "security"],
                "avoid": ["unregulated", "consumer social", "gaming"]
            },
            "b2b_saas": {
                "adjacent_industries": ["enterprise_saas", "fintech_b2b"],
                "keywords": ["enterprise", "workflow", "productivity", "automation", "API"],
                "avoid": ["B2C", "consumer", "gaming", "entertainment"]
            }
        }

    def generate_search_queries(self, job_data: Dict[str, Any], criteria: Dict) -> List[str]:
        """
        Generate 5 LinkedIn X-ray searches from most to least restrictive
        Returns queries that will actually return results
        """
        queries = []
        
        # Extract key components
        primary_title = self._extract_primary_title(job_data)
        title_variants = self._get_title_variations(primary_title)
        location = self._extract_location(job_data)
        location_variants = self._get_location_variations(location)
        skills = criteria.get('must_have_skills', [])[:3]  # Top 3 skills
        company_type = job_data.get("company_type", "unknown")
        
        # Query 1: Title + Location + Primary Must-Have Skill (Most Restrictive)
        if skills and location_variants:
            query1 = f'site:linkedin.com/in/ ("{title_variants[0]}" OR "{title_variants[1] if len(title_variants) > 1 else title_variants[0]}") "{location_variants[0]}" {skills[0]}'
            queries.append(self._optimize_query_length(query1))
        
        # Query 2: Title Variations + Key Skill (No location constraint)
        if skills:
            title_or_group = " OR ".join([f'"{title}"' for title in title_variants[:3]])
            query2 = f'site:linkedin.com/in/ ({title_or_group}) {skills[0]}'
            if len(skills) > 1:
                query2 += f" {skills[1]}"
            queries.append(self._optimize_query_length(query2))
        
        # Query 3: Title + Company Type Signal
        if company_type != "unknown":
            company_signals = self.company_signals.get(company_type, [])
            if company_signals:
                query3 = f'site:linkedin.com/in/ "{title_variants[0]}" ({" OR ".join(company_signals[:2])})'
                queries.append(self._optimize_query_length(query3))
        
        # Query 4: Broader Title + Location (Fallback for volume)
        if location_variants and len(title_variants) > 1:
            query4 = f'site:linkedin.com/in/ ("{title_variants[1]}" OR "Engineer") "{location_variants[0]}"'
            queries.append(self._optimize_query_length(query4))
        
        # Query 5: Just Title (Guaranteed fallback)
        query5 = f'site:linkedin.com/in/ "{title_variants[0]}"'
        queries.append(self._optimize_query_length(query5))
        
        # Remove duplicates and return up to 5 queries
        unique_queries = []
        for query in queries:
            if query not in unique_queries:
                unique_queries.append(query)
        
        return unique_queries[:5]

    def _extract_primary_title(self, job_data: Dict[str, Any]) -> str:
        """Extract primary job title from job data"""
        title = job_data.get("title", "Software Engineer")
        
        # Clean up title
        title = re.sub(r'\s+', ' ', title).strip()
        
        # If title is too specific, generalize it
        if "full-stack product engineer" in title.lower():
            return "Product Engineer"
        elif "senior" in title.lower() and "engineer" in title.lower():
            return "Software Engineer"
        elif len(title.split()) > 4:
            # Try to extract core role
            if "engineer" in title.lower():
                return "Software Engineer"
            elif "manager" in title.lower():
                return "Product Manager"
            elif "scientist" in title.lower():
                return "Data Scientist"
        
        return title

    def _get_title_variations(self, primary_title: str) -> List[str]:
        """Get variations of the job title for search"""
        
        # Check if we have predefined variations
        for key, variations in self.title_variations.items():
            if key.lower() in primary_title.lower() or primary_title.lower() in key.lower():
                return variations
        
        # Generate variations based on patterns
        variations = [primary_title]
        
        if "engineer" in primary_title.lower():
            variations.extend(["Software Engineer", "Developer", "Senior Software Engineer"])
        elif "manager" in primary_title.lower():
            variations.extend(["Product Manager", "Senior Product Manager", "Product Lead"])
        elif "scientist" in primary_title.lower():
            variations.extend(["Data Scientist", "ML Engineer", "Research Scientist"])
        
        # Remove duplicates while preserving order
        unique_variations = []
        for var in variations:
            if var not in unique_variations:
                unique_variations.append(var)
        
        return unique_variations

    def _extract_location(self, job_data: Dict[str, Any]) -> str:
        """Extract location from job data"""
        location = job_data.get("location", "San Francisco")
        
        # Clean up location string
        location = re.sub(r'\s*,\s*(CA|California|NY|New York|TX|Texas|WA|Washington)', '', location)
        location = location.strip()
        
        return location

    def _get_location_variations(self, location: str) -> List[str]:
        """Get variations of the location for search"""
        
        # Check predefined variations
        for key, variations in self.location_variations.items():
            if key.lower() in location.lower() or any(var.lower() in location.lower() for var in variations):
                return variations
        
        # Default variations
        variations = [location]
        
        if "san francisco" in location.lower() or "sf" in location.lower():
            variations = ["San Francisco", "SF", "Bay Area"]
        elif "new york" in location.lower() or "nyc" in location.lower():
            variations = ["New York", "NYC", "Manhattan"]
        elif "los angeles" in location.lower() or "la" in location.lower():
            variations = ["Los Angeles", "LA", "Southern California"]
        elif "remote" in location.lower():
            variations = ["Remote", "Distributed"]
        
        return variations

    def _optimize_query_length(self, query: str) -> str:
        """Optimize query length to stay under LinkedIn limits"""
        
        # LinkedIn X-ray searches work best under 250 characters
        max_length = 250
        
        if len(query) <= max_length:
            return query
        
        # Try to shorten by removing less important terms
        # Remove extra OR clauses
        if " OR " in query and len(query) > max_length:
            # Keep only first OR option
            parts = query.split(" OR ")
            shortened = parts[0]
            for part in parts[1:]:
                if len(shortened + " OR " + part) <= max_length:
                    shortened += " OR " + part
                else:
                    break
            query = shortened
        
        # Remove extra skills if still too long
        if len(query) > max_length:
            words = query.split()
            while len(" ".join(words)) > max_length and len(words) > 5:
                # Remove last word that's not part of the core structure
                if words[-1] not in ['site:linkedin.com/in/', '"']:
                    words.pop()
                else:
                    break
            query = " ".join(words)
        
        return query

# Test the generator
if __name__ == "__main__":
    generator = SearchQueryGenerator()
    
    # Test with sample job
    sample_job = {
        "title": "Full-Stack Product Engineer",
        "location": "San Francisco, CA",
        "company_type": "startup"
    }
    
    sample_criteria = {
        "must_have_skills": ["React", "Node.js", "TypeScript"]
    }
    
    # Generate search queries
    queries = generator.generate_search_queries(sample_job, sample_criteria)
    
    print("=== GENERATED SEARCH QUERIES ===")
    for i, query in enumerate(queries, 1):
        print(f"\nQuery {i}: {query}")
        print(f"Length: {len(query)} characters")
    
    print(f"\n✅ Generated {len(queries)} working search queries") 