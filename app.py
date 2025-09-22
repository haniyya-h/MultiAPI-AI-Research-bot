import streamlit as st
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd
from typing import Dict, List, Any
import io
import base64
import os
import xml.etree.ElementTree as ET
from groq import Groq

# Configure page
st.set_page_config(
    page_title="AI Research Summarizer & Explorer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .paper-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .insight-card {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid #ff7f0e;
    }
    .keyword-tag {
        background-color: #1f77b4;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.2rem;
        display: inline-block;
    }
    .stButton > button {
        background-color: #1f77b4;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background-color: #0d5aa7;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Groq client
@st.cache_resource
def get_groq_client():
    """Initialize and cache Groq client"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY environment variable not set!")
        return None
    return Groq(api_key=api_key)

class ArxivAPI:
    """Handle arXiv API interactions"""
    
    @staticmethod
    def search_papers(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search arXiv for papers matching the query"""
        base_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            # Parse XML response (simplified parsing)
            root = ET.fromstring(response.content)
            
            papers = []
            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                paper = {
                    "title": entry.find("{http://www.w3.org/2005/Atom}title").text.strip(),
                    "authors": [author.find("{http://www.w3.org/2005/Atom}name").text 
                              for author in entry.findall("{http://www.w3.org/2005/Atom}author")],
                    "abstract": entry.find("{http://www.w3.org/2005/Atom}summary").text.strip(),
                    "published": entry.find("{http://www.w3.org/2005/Atom}published").text[:10],
                    "url": entry.find("{http://www.w3.org/2005/Atom}id").text,
                    "arxiv_id": entry.find("{http://www.w3.org/2005/Atom}id").text.split("/")[-1]
                }
                papers.append(paper)
            
            return papers
            
        except Exception as e:
            st.error(f"Error fetching from arXiv: {str(e)}")
            return []

class SemanticScholarAPI:
    """Handle Semantic Scholar API interactions"""
    
    @staticmethod
    def get_paper_details(arxiv_id: str) -> Dict[str, Any]:
        """Get detailed information from Semantic Scholar"""
        try:
            # First, get paper ID from arXiv ID
            search_url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
            headers = {
                'User-Agent': 'AI-Research-Summarizer/1.0 (https://github.com/your-repo)'
            }
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                return {}
        except Exception as e:
            return {}
    
    @staticmethod
    def get_related_works(arxiv_id: str) -> List[Dict[str, Any]]:
        """Get related works from Semantic Scholar"""
        try:
            paper_data = SemanticScholarAPI.get_paper_details(arxiv_id)
            if paper_data and "references" in paper_data:
                return paper_data.get("references", [])[:5]  # Limit to 5 related works
            return []
        except Exception as e:
            return []

class GroqAI:
    """Handle AI summarization and analysis using Groq"""
    
    @staticmethod
    def summarize_papers(papers: List[Dict[str, Any]]) -> str:
        """Generate AI summary of papers"""
        groq_client = get_groq_client()
        if not groq_client:
            return "Error: Groq client not available"
            
        abstracts = [paper["abstract"] for paper in papers]
        combined_text = "\n\n".join(abstracts)
        
        prompt = f"""
        Please provide a comprehensive summary of the following research papers. 
        Focus on the main findings, methodologies, and key insights:
        
        {combined_text}
        
        Provide a clear, structured summary highlighting the most important points.
        """
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    @staticmethod
    def explain_like_15(papers: List[Dict[str, Any]]) -> str:
        """Generate explanation suitable for 15-year-olds"""
        groq_client = get_groq_client()
        if not groq_client:
            return "Error: Groq client not available"
            
        abstracts = [paper["abstract"] for paper in papers]
        combined_text = "\n\n".join(abstracts)
        
        prompt = f"""
        Explain the following research in simple terms that a 15-year-old would understand.
        Use analogies and avoid technical jargon:
        
        {combined_text}
        
        Make it engaging and easy to understand.
        """
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating explanation: {str(e)}"
    
    @staticmethod
    def extract_keywords(papers: List[Dict[str, Any]]) -> List[str]:
        """Extract key terms and concepts"""
        groq_client = get_groq_client()
        if not groq_client:
            return []
            
        abstracts = [paper["abstract"] for paper in papers]
        combined_text = "\n\n".join(abstracts)
        
        prompt = f"""
        Extract the most important keywords and key terms from this research:
        
        {combined_text}
        
        Return only a list of 10-15 key terms, separated by commas.
        """
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            keywords = response.choices[0].message.content.split(",")
            return [kw.strip() for kw in keywords if kw.strip()]
        except Exception as e:
            return []
    
    @staticmethod
    def analyze_trends(papers: List[Dict[str, Any]]) -> str:
        """Analyze trends and patterns in the research"""
        groq_client = get_groq_client()
        if not groq_client:
            return "Error: Groq client not available"
            
        abstracts = [paper["abstract"] for paper in papers]
        combined_text = "\n\n".join(abstracts)
        
        prompt = f"""
        Analyze the following research papers and identify:
        1. Current trends in this field
        2. Emerging patterns
        3. Common methodologies
        4. Key themes
        
        Research abstracts:
        {combined_text}
        
        Provide insights about the direction this field is heading.
        """
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing trends: {str(e)}"
    
    @staticmethod
    def identify_challenges(papers: List[Dict[str, Any]]) -> str:
        """Identify open challenges and future directions"""
        groq_client = get_groq_client()
        if not groq_client:
            return "Error: Groq client not available"
            
        abstracts = [paper["abstract"] for paper in papers]
        combined_text = "\n\n".join(abstracts)
        
        prompt = f"""
        Based on the following research papers, identify:
        1. Open challenges mentioned
        2. Limitations of current approaches
        3. Future research directions
        4. Unresolved questions
        
        Research abstracts:
        {combined_text}
        
        Focus on what problems still need to be solved.
        """
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error identifying challenges: {str(e)}"

class ResearchAPI:
    """Handle research operations directly (no backend needed)"""
    
    @staticmethod
    def search_papers(query: str) -> Dict[str, Any]:
        """Search for papers and return comprehensive analysis"""
        if not query:
            st.error("Query is required")
            return None
        
        try:
            # Fetch papers from arXiv
            papers = ArxivAPI.search_papers(query, max_results=5)
            
            if not papers:
                st.error("No papers found for the given query")
                return None
            
            # Get additional data from Semantic Scholar for first paper
            related_works = []
            citation_counts = {}
            
            if papers:
                first_paper_id = papers[0]["arxiv_id"]
                
                # Try to get data from Semantic Scholar
                paper_details = SemanticScholarAPI.get_paper_details(first_paper_id)
                related_works = SemanticScholarAPI.get_related_works(first_paper_id)
                
                if paper_details:
                    citation_counts = {
                        "citations": paper_details.get("citationCount", 0),
                        "references": paper_details.get("referenceCount", 0)
                    }
                else:
                    # Fallback: provide some mock data for demonstration
                    citation_counts = {
                        "citations": 0,
                        "references": 0,
                        "status": "Semantic Scholar unavailable"
                    }
            
            # Generate AI analysis
            ai_summary = GroqAI.summarize_papers(papers)
            explain_like_15 = GroqAI.explain_like_15(papers)
            keywords = GroqAI.extract_keywords(papers)
            trends = GroqAI.analyze_trends(papers)
            open_challenges = GroqAI.identify_challenges(papers)
            
            return {
                "papers": papers,
                "ai_summary": ai_summary,
                "explain_like_15": explain_like_15,
                "keywords": keywords,
                "related_works": related_works,
                "citation_counts": citation_counts,
                "trends": trends,
                "open_challenges": open_challenges
            }
            
        except Exception as e:
            st.error(f"Error during search: {str(e)}")
            return None
    
    @staticmethod
    def export_results(query: str, search_result: Dict[str, Any]) -> Dict[str, Any]:
        """Export search results as markdown"""
        try:
            # Generate markdown content
            markdown_content = f"""# Research Summary: {query}

## Papers Found ({len(search_result['papers'])})

"""
            
            for i, paper in enumerate(search_result['papers'], 1):
                markdown_content += f"""### {i}. {paper['title']}

**Authors:** {', '.join(paper['authors'])}
**Published:** {paper['published']}
**URL:** {paper['url']}

**Abstract:**
{paper['abstract']}

---

"""
            
            markdown_content += f"""
## AI Summary

{search_result['ai_summary']}

## Explain Like I'm 15

{search_result['explain_like_15']}

## Keywords

{', '.join(search_result['keywords'])}

## Trends & Insights

{search_result['trends']}

## Open Challenges

{search_result['open_challenges']}

## Related Works

"""
            
            for work in search_result['related_works'][:5]:
                markdown_content += f"- {work.get('title', 'Unknown Title')}\n"
            
            return {
                "content": markdown_content,
                "filename": f"research_summary_{query.replace(' ', '_')}.md"
            }
            
        except Exception as e:
            st.error(f"Error generating export: {str(e)}")
            return None

def display_paper_card(paper: Dict[str, Any], index: int):
    """Display a paper in a card format"""
    with st.container():
        st.markdown(f"""
        <div class="paper-card">
            <h3>{index + 1}. {paper['title']}</h3>
            <p><strong>Authors:</strong> {', '.join(paper['authors'])}</p>
            <p><strong>Published:</strong> {paper['published']}</p>
            <p><strong>Abstract:</strong></p>
            <p>{paper['abstract'][:300]}{'...' if len(paper['abstract']) > 300 else ''}</p>
            <p><a href="{paper['url']}" target="_blank">📄 View on arXiv</a></p>
        </div>
        """, unsafe_allow_html=True)

def display_insights_panel(search_result: Dict[str, Any]):
    """Display insights and analysis panel"""
    st.markdown("## 🔍 Research Insights")
    
    # AI Summary
    with st.expander("📝 AI Summary", expanded=True):
        st.write(search_result['ai_summary'])
    
    # Explain Like I'm 15
    with st.expander("🧒 Explain Like I'm 15", expanded=False):
        st.write(search_result['explain_like_15'])
    
    # Keywords
    st.markdown("### 🏷️ Key Terms")
    keywords = search_result.get('keywords', [])
    if keywords:
        keyword_html = " ".join([f'<span class="keyword-tag">{kw}</span>' for kw in keywords[:10]])
        st.markdown(keyword_html, unsafe_allow_html=True)
    
    # Trends Analysis
    with st.expander("📈 Trends & Patterns", expanded=False):
        st.write(search_result.get('trends', 'No trends analysis available'))
    
    # Open Challenges
    with st.expander("🚧 Open Challenges", expanded=False):
        st.write(search_result.get('open_challenges', 'No challenges analysis available'))
    
    # Citation Information
    citation_counts = search_result.get('citation_counts', {})
    if citation_counts:
        st.markdown("### 📊 Citation Information")
        col1, col2 = st.columns(2)
        with col1:
            citations = citation_counts.get('citations', 0)
            st.metric("Citations", citations)
        with col2:
            references = citation_counts.get('references', 0)
            st.metric("References", references)
        
        # Show additional citation info
        status = citation_counts.get('status', '')
        if status == "Semantic Scholar unavailable":
            st.info("💡 Citation data from Semantic Scholar is currently unavailable. This is normal and doesn't affect the AI analysis.")

def create_citation_visualization(search_result: Dict[str, Any]):
    """Create visualization for citation data"""
    citation_counts = search_result.get('citation_counts', {})
    
    citations = citation_counts.get('citations', 0)
    references = citation_counts.get('references', 0)
    
    # Only show visualization if we have numeric data
    if (isinstance(citations, (int, float)) and citations > 0) or (isinstance(references, (int, float)) and references > 0):
        fig = go.Figure(data=[
            go.Bar(name='Citations', x=['Citations'], y=[citations if isinstance(citations, (int, float)) else 0]),
            go.Bar(name='References', x=['References'], y=[references if isinstance(references, (int, float)) else 0])
        ])
        
        fig.update_layout(
            title="Citation Metrics",
            xaxis_title="Metric Type",
            yaxis_title="Count",
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Citation visualization not available - Semantic Scholar data not accessible")

def export_to_markdown(search_result: Dict[str, Any], query: str):
    """Export results to markdown format"""
    api = ResearchAPI()
    export_data = api.export_results(query, search_result)
    
    if export_data:
        # Create download link
        markdown_content = export_data['content']
        filename = export_data['filename']
        
        # Encode the content for download
        b64 = base64.b64encode(markdown_content.encode()).decode()
        href = f'<a href="data:text/markdown;base64,{b64}" download="{filename}">📥 Download Markdown Report</a>'
        st.markdown(href, unsafe_allow_html=True)

def main():
    """Main application function"""
    
    # Header
    st.markdown('<h1 class="main-header">🔬 AI Research Summarizer & Explorer</h1>', unsafe_allow_html=True)
    st.markdown("Search for academic papers and get AI-powered summaries, insights, and explanations!")
    
    # Sidebar for information
    with st.sidebar:
        st.markdown("## 📚 About")
        st.markdown("""
        This application helps you:
        - 🔍 Search academic papers from arXiv
        - 🤖 Get AI-powered summaries
        - 🧒 Understand complex research in simple terms
        - 📊 Analyze trends and patterns
        - 📥 Export results as reports
        """)
    
    # Main search interface
    st.markdown("## 🔍 Search Research Papers")
    
    # Search input
    query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., machine learning, quantum computing, climate change",
        help="Search for papers by topic, keywords, or research area"
    )
    
    # Search button
    search_clicked = st.button("🔍 Search Papers", type="primary")
    
    # Initialize session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'current_query' not in st.session_state:
        st.session_state.current_query = None
    
    # Perform search
    if search_clicked and query:
        with st.spinner("🔍 Searching papers and generating AI insights..."):
            api = ResearchAPI()
            search_result = api.search_papers(query)
            
            if search_result:
                st.session_state.search_results = search_result
                st.session_state.current_query = query
                st.success(f"Found {len(search_result['papers'])} papers!")
            else:
                st.error("No results found or error occurred. Please try again.")
    
    # Display results if available
    if st.session_state.search_results:
        search_result = st.session_state.search_results
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["📄 Search Results", "🔍 Insights", "📥 Export"])
        
        with tab1:
            st.markdown(f"## 📚 Papers Found for: '{st.session_state.current_query}'")
            
            # Display papers
            for i, paper in enumerate(search_result['papers']):
                display_paper_card(paper, i)
            
            # Related works if available
            related_works = search_result.get('related_works', [])
            if related_works:
                st.markdown("## 🔗 Related Works")
                for work in related_works[:5]:
                    st.write(f"- {work.get('title', 'Unknown Title')}")
        
        with tab2:
            display_insights_panel(search_result)
            
            # Citation visualization
            st.markdown("### 📊 Citation Analysis")
            create_citation_visualization(search_result)
        
        with tab3:
            st.markdown("## 📥 Export Results")
            st.markdown("Download your research summary as a markdown file:")
            
            if st.button("📄 Generate Markdown Report"):
                export_to_markdown(search_result, st.session_state.current_query)
            
            # Display preview of export content
            if st.checkbox("👁️ Preview Export Content"):
                api = ResearchAPI()
                export_data = api.export_results(st.session_state.current_query, search_result)
                if export_data:
                    st.markdown("### 📄 Export Preview")
                    st.text_area("Markdown Content", export_data['content'], height=400)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🔬 AI Research Summarizer & Explorer | Powered by arXiv, Semantic Scholar, and Groq AI</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
