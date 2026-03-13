
import streamlit as st
import time
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Import the required modules
from elite_sourcing_agent import EliteSourcingAgent
from linkedin_real_data import WorkingLinkedInIntegration
from smart_evaluator import SmartEvaluator

# Load environment variables
load_dotenv()

# Initialize session state
if 'candidates' not in st.session_state:
    st.session_state.candidates = []
if 'search_completed' not in st.session_state:
    st.session_state.search_completed = False
if 'job_description' not in st.session_state:
    st.session_state.job_description = ""
if 'job_criteria' not in st.session_state:
    st.session_state.job_criteria = None

# Page configuration
st.set_page_config(
    page_title="🎖️ Elite Candidate Sourcing System",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stButton > button {
        background-color: #0066cc;
        color: white;
        font-weight: bold;
    }
    .candidate-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .score-badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        margin-right: 10px;
    }
    .excellent { background-color: #28a745; color: white; }
    .good { background-color: #ffc107; color: black; }
    .average { background-color: #fd7e14; color: white; }
    .poor { background-color: #dc3545; color: white; }
    .metric-container {
        display: flex;
        justify-content: space-around;
        margin: 20px 0;
    }
    .metric-box {
        text-align: center;
        padding: 15px;
        background-color: #e9ecef;
        border-radius: 8px;
        flex: 1;
        margin: 0 10px;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #0066cc;
    }
    .metric-label {
        font-size: 0.9em;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

class JobDescription(BaseModel):
    Job_location: str = Field(..., description="Location of the job")
    Job_title: str = Field(..., description="Title of the job")
    Company_name: str = Field(..., description="Name of the company")
    

def generate_personalized_outreach(candidate_summary: str, evaluation: Dict, job_description: str) -> str:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    sum_llm = llm.with_structured_output(JobDescription)
    job_description = sum_llm.invoke(job_description)
    
    # Extract candidate name from summary
    name = "there"
    lines = candidate_summary.split('\n')
    for line in lines:
        if line.startswith('Name:'):
            name = line.replace('Name:', '').strip()
            break
    Current = "N/A"
    lines = candidate_summary.split('\n')
    for line in lines:
        if line.startswith('Current Role & Company:'):
            Current = line.replace('Current Role & Company:', '').strip()
            break
    
    # Extract role from job description
    role = job_description.Job_title
    company = job_description.Company_name
    
    # Get key strengths from evaluation
    strengths = evaluation.get('evaluation', {}).get('strengths', [])
    strengths_text = strengths[0] if strengths else "your impressive background"
    
    # Craft personalized message
    outreach = f"""Hi {name},

I came across your profile and was immediately impressed by {strengths_text.lower()} at {Current}. Your experience aligns remarkably well with an opportunity we have for a {role} at {company}.

Based on your background, I believe you'd be an excellent fit for this role. The position offers the chance to work on cutting-edge technology and make a significant impact on our product.

Would you be open to a brief conversation to learn more about this opportunity? I'd love to share more details about the role and hear about your career goals.

Looking forward to connecting!

Best regards,
[Your Name]
[Your Title]"""
    
    return outreach

def get_score_badge(score: float) -> str:
    """Get HTML badge for score display"""
    if score >= 8.5:
        return f'<span class="score-badge excellent">🟢 {score:.1f}/10</span>'
    elif score >= 7.0:
        return f'<span class="score-badge good">🟡 {score:.1f}/10</span>'
    elif score >= 5.5:
        return f'<span class="score-badge average">🟠 {score:.1f}/10</span>'
    else:
        return f'<span class="score-badge poor">🔴 {score:.1f}/10</span>'

def main():
    # Header
    st.title("🎖️ Elite Candidate Sourcing System")
    st.markdown("*Powered by SRN FitScore Methodology*")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Number of candidates to display
        num_candidates = st.number_input(
            "Number of Top Candidates to Display",
            min_value=1,
            max_value=100,
            value=5,
            help="The search will stop once this many qualified candidates are found, improving efficiency."
        )
        
        # API Key validation
        st.subheader("🔑 API Status")
        api_keys = {
            "OpenAI": st.secrets["OPENAI_API_KEY"],
            "Google": st.secrets["GOOGLE_API_KEY"],
            "Apify": st.secrets["APIFY_API_KEY"]
        }
        
        for api, key in api_keys.items():
            if key:
                st.success(f"✅ {api} API configured")
            else:
                st.error(f"❌ {api} API missing")
        
        # Instructions
        st.markdown("---")
        st.subheader("📋 Instructions")
        st.markdown("""
        1. Enter the job description
        2. Click 'Start Elite Search'
        3. Wait for candidate analysis
        4. Review ranked results
        5. Use personalized outreach messages
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Job Description")
        job_description = st.text_area(
            "Enter the job description:",
            height=300,
            placeholder="""Example:
Senior DevOps Engineer
San Francisco, California
Engineering / On-site

We're looking for a seasoned DevOps engineer to:
- Own and shape the future of our environment
- Manage customer deployments at scale
- Instrument our system for performance monitoring
- Optimize our CI/CD pipeline

Requirements:
- 5+ years experience with Infrastructure as Code
- Experience with AWS/GCP/Azure
- Strong knowledge of Kubernetes and Docker
- Proficiency in Python or JavaScript
""",
            value=st.session_state.job_description
        )
        
        # Store job description in session state
        if job_description:
            st.session_state.job_description = job_description
    
    with col2:
        st.header("🎯 Search Controls")
        
        # Search button
        if st.button("🚀 Start Elite Search", type="primary", use_container_width=True):
            if not job_description:
                st.error("Please enter a job description first!")
            elif not all(api_keys.values()):
                st.error("Please configure all required API keys!")
            else:
                st.session_state.search_completed = False
                st.session_state.candidates = []
                st.session_state.job_criteria = None
                
                # Progress container
                progress_container = st.container()
                with progress_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Initialize components
                        status_text.text("🔧 Initializing elite sourcing system...")
                        agent = EliteSourcingAgent()
                        linkedin_integration = WorkingLinkedInIntegration()
                        evaluator = SmartEvaluator()
                        progress_bar.progress(10)
                        
                        # Step 1: Get LinkedIn URLs
                        status_text.text("🔍 Searching for elite candidates...")
                        linkedin_urls = agent.get_linkedin_urls_from_job_description(job_description)
                        
                        if not linkedin_urls:
                            st.error("No LinkedIn profiles found. Please try a different job description.")
                            return
                        
                        progress_bar.progress(30)
                        status_text.text(f"✅ Found {len(linkedin_urls)} potential candidates")
                        
                        # Step 2: Extract candidate summaries
                        candidates_data = []
                        total_urls = len(linkedin_urls)
                        urls_to_process = list(linkedin_urls)
                        
                        # Store the first evaluation to extract criteria
                        job_criteria = None
                        
                        for i, url in enumerate(urls_to_process):
                            # Stop if we have enough candidates
                            if len(candidates_data) >= num_candidates:
                                status_text.text(f"✅ Found {num_candidates} qualified candidates!")
                                break
                            
                            progress = 30 + int((i / min(len(urls_to_process), num_candidates * 2)) * 40)
                            progress_bar.progress(progress)
                            status_text.text(f"📊 Analyzing candidate {i+1} (Found: {len(candidates_data)}/{num_candidates})...")
                            
                            try:
                                # Get candidate summary
                                summary = linkedin_integration.summarize_apify_profile(url)
                                
                                # Evaluate candidate
                                evaluation = evaluator.evaluate_candidate_from_summary(summary, job_description)
                                
                                if not evaluation.get('error'):
                                    candidates_data.append({
                                        'url': url,
                                        'summary': summary,
                                        'evaluation': evaluation,
                                        'fit_score': evaluation.get('fit_score', 0.0)
                                    })
                                    
                                    # Store criteria from first successful evaluation
                                    if job_criteria is None and 'hiring_criteria' in evaluation:
                                        job_criteria = evaluation['hiring_criteria']
                                
                                # Rate limiting
                                time.sleep(0.5)
                                
                            except Exception as e:
                                st.warning(f"Failed to process candidate {i+1}: {str(e)}")
                                continue
                        
                        progress_bar.progress(70)
                        status_text.text("🏆 Ranking candidates...")
                        
                        # Step 3: Sort candidates by fit score
                        candidates_data.sort(key=lambda x: x['fit_score'], reverse=True)
                        
                        # Generate outreach messages
                        progress_bar.progress(80)
                        status_text.text("✉️ Generating personalized outreach messages...")
                        
                        for candidate in candidates_data:
                            candidate['outreach'] = generate_personalized_outreach(
                                candidate['summary'],
                                candidate['evaluation'],
                                job_description
                            )
                        
                        # Store results
                        st.session_state.candidates = candidates_data[:num_candidates]
                        st.session_state.search_completed = True
                        st.session_state.job_criteria = job_criteria
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Elite search completed!")
                        time.sleep(1)
                        
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                        st.exception(e)
        
        # Clear results button
        if st.session_state.search_completed:
            if st.button("🔄 Clear Results", use_container_width=True):
                st.session_state.candidates = []
                st.session_state.search_completed = False
                st.session_state.job_criteria = None
                st.rerun()
    
    # Results section
    if st.session_state.search_completed and st.session_state.candidates:
        st.markdown("---")
        st.header("🏆 Elite Candidates - Ranked by SRN FitScore")
        
        # Display Job Criteria
        if st.session_state.job_criteria:
            with st.expander("📋 Elite Hiring Criteria Used for Evaluation", expanded=False):
                st.subheader("Job Analysis Context")
                
                # Extract context from first candidate's evaluation
                if st.session_state.candidates and 'context' in st.session_state.candidates[0]['evaluation']:
                    context = st.session_state.candidates[0]['evaluation']['context']
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Industry", context.get('industry', 'N/A'))
                    with col2:
                        st.metric("Company Type", context.get('company_type', 'N/A'))
                    with col3:
                        st.metric("Role Type", context.get('role_type', 'N/A'))
                    with col4:
                        st.metric("Role Subtype", context.get('role_subtype', 'N/A'))
                
                st.subheader("Evaluation Criteria")
                criteria = st.session_state.job_criteria
                
                # Education Requirements
                st.markdown("**🎓 Education Requirements:**")
                st.info(criteria.get('education_requirements', 'Not specified'))
                
                # Core Skills
                st.markdown("**💼 Core Skills (Mission-Critical):**")
                core_skills = criteria.get('core_skills', [])
                if core_skills:
                    for skill in core_skills:
                        st.markdown(f"• {skill}")
                
                # Domain Expertise
                st.markdown("**🔧 Domain Expertise:**")
                domain_exp = criteria.get('domain_expertise', [])
                if domain_exp:
                    for exp in domain_exp:
                        st.markdown(f"• {exp}")
                
                # Experience Markers
                st.markdown("**📈 Experience Markers:**")
                exp_markers = criteria.get('experience_markers', [])
                if exp_markers:
                    for marker in exp_markers:
                        st.markdown(f"• {marker}")
                
                # Company Preferences
                st.markdown("**🏢 Company Preferences:**")
                company_prefs = criteria.get('company_preferences', [])
                if company_prefs:
                    for pref in company_prefs:
                        st.markdown(f"• {pref}")
                
                # Bonus Signals
                st.markdown("**⭐ Bonus Signals:**")
                bonus_signals = criteria.get('bonus_signals', [])
                if bonus_signals:
                    for signal in bonus_signals:
                        st.markdown(f"• {signal}")
                
                # Red Flags
                st.markdown("**🚩 Red Flags:**")
                red_flags = criteria.get('red_flags', [])
                if red_flags:
                    for flag in red_flags:
                        st.markdown(f"• {flag}")
        
        # Summary metrics
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{len(st.session_state.candidates)}</div>
                <div class="metric-label">Top Candidates</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            avg_score = sum(c['fit_score'] for c in st.session_state.candidates) / len(st.session_state.candidates)
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{avg_score:.1f}</div>
                <div class="metric-label">Average Score</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            elite_count = sum(1 for c in st.session_state.candidates if c['fit_score'] >= 8.5)
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{elite_count}</div>
                <div class="metric-label">Elite (8.5+)</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            good_count = sum(1 for c in st.session_state.candidates if 7.0 <= c['fit_score'] < 8.5)
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{good_count}</div>
                <div class="metric-label">Good (7.0+)</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display candidates
        for i, candidate in enumerate(st.session_state.candidates):
            # Extract name from summary
            name = "Candidate"
            lines = candidate['summary'].split('\n')
            for line in lines:
                if line.startswith('Name:'):
                    name = line.replace('Name:', '').strip()
                    break
            
            # Create expandable section for each candidate
            with st.expander(f"#{i+1} - {name} - Score: {candidate['fit_score']:.1f}/10"):
                # Header with score badge
                st.markdown(f"""
                <h3>{name} {get_score_badge(candidate['fit_score'])}</h3>
                <p><strong>LinkedIn:</strong> <a href="{candidate['url']}" target="_blank">{candidate['url']}</a></p>
                """, unsafe_allow_html=True)
                
                # Create tabs for different information
                tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "📊 Evaluation", "✉️ Outreach", "📈 Detailed Scores"])
                
                with tab1:
                    st.subheader("Candidate Summary")
                    st.text(candidate['summary'])
                
                with tab2:
                    st.subheader("Evaluation Results")
                    eval_data = candidate['evaluation']
                    
                    # Recommendation
                    st.markdown(f"**Recommendation:** {eval_data.get('recommendation', 'N/A')}")
                    
                    # Strengths and Weaknesses
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**💪 Strengths:**")
                        strengths = eval_data.get('evaluation', {}).get('strengths', [])
                        for strength in strengths:
                            st.markdown(f"• {strength}")
                    
                    with col2:
                        st.markdown("**⚠️ Weaknesses:**")
                        weaknesses = eval_data.get('evaluation', {}).get('weaknesses', [])
                        for weakness in weaknesses:
                            st.markdown(f"• {weakness}")
                    
                    # Rationale
                    st.markdown("**📝 Evaluation Rationale:**")
                    st.info(eval_data.get('evaluation', {}).get('rationale', 'No rationale provided'))
                
                with tab3:
                    st.subheader("Personalized Outreach Message")
                    st.text_area(
                        "Copy this message:",
                        value=candidate['outreach'],
                        height=300,
                        key=f"outreach_{i}"
                    )
                    
                    # Copy button instructions
                    st.caption("💡 Tip: Customize this message with your name and company details before sending")
                
                with tab4:
                    st.subheader("Detailed Score Breakdown")
                    
                    # Get scores
                    scores = eval_data.get('evaluation', {}).get('scores', {})
                    
                    # Create score visualization
                    score_data = []
                    for category, score in scores.items():
                        score_data.append({
                            'Category': category.replace('_', ' ').title(),
                            'Score': score
                        })
                    
                    if score_data:
                        df = pd.DataFrame(score_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # Bar chart
                        st.bar_chart(df.set_index('Category')['Score'])
                    
                    # Context information
                    st.markdown("**Context:**")
                    context = eval_data.get('context', {})
                    if context:
                        st.json(context)
        
        # Export functionality
        st.markdown("---")
        st.subheader("📥 Export Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export as JSON
            export_data = {
                'search_date': datetime.now().isoformat(),
                'job_description': job_description,
                'job_criteria': st.session_state.job_criteria,
                'candidates': st.session_state.candidates
            }
            
            st.download_button(
                label="📄 Download as JSON",
                data=json.dumps(export_data, indent=2),
                file_name=f"elite_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            # Export as CSV
            csv_data = []
            for candidate in st.session_state.candidates:
                name = "Unknown"
                lines = candidate['summary'].split('\n')
                for line in lines:
                    if line.startswith('Name:'):
                        name = line.replace('Name:', '').strip()
                        break
                
                csv_data.append({
                    'Name': name,
                    'Score': candidate['fit_score'],
                    'LinkedIn URL': candidate['url'],
                    'Recommendation': candidate['evaluation'].get('recommendation', 'N/A'),
                    'Strengths': '; '.join(candidate['evaluation'].get('evaluation', {}).get('strengths', [])),
                    'Weaknesses': '; '.join(candidate['evaluation'].get('evaluation', {}).get('weaknesses', []))
                })
            
            df = pd.DataFrame(csv_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="📊 Download as CSV",
                data=csv,
                file_name=f"elite_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
