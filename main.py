from langchain.agents import initialize_agent, AgentType
from langchain.llms import HuggingFaceHub
from langchain.tools import Tool
import fitz
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
PDF_PATH = "resume.pdf"
JOB_DESCRIPTION_PDF_PATH = "JD.pdf"

# Initialize Llama 3.2 model from Hugging Face Hub
llama_llm = HuggingFaceHub(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",  # Adjust if needed for Llama 3.2
    model_kwargs={"temperature": 0.7, "max_length": 500},
    huggingfacehub_api_token=HUGGINGFACEHUB_API_TOKEN
)

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    return text

def analyze_resume_with_llama(combined_text: str):
    """Use Llama 3.2 to analyze a resume against a job description."""
    analysis_prompt = f"""
    Based on the resume and job description below, provide EXACTLY 3 specific areas for improvement.
    Prioritize technical skills over managerial or soft skills.
    If there are no more technical skills to improve, then suggest managerial or soft skills.
    
    Format each area as a new line starting with '- IMPROVE: '
    Focus only on listing the improvement areas, do not provide any other analysis.
    
    {combined_text}
    """
    return llama_llm.predict(analysis_prompt)

def extract_improvement_areas(analysis_text):
    """Extract improvement areas from the analysis text."""
    improvements = []
    for line in analysis_text.split('\n'):
        if line.strip().startswith('- IMPROVE:'):
            improvement = line.replace('- IMPROVE:', '').strip()
            if improvement:
                improvements.append(improvement)
    return improvements

def search_youtube_videos(query):
    """Search YouTube for long-format educational videos/playlists, ordered by highest view count."""
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    
    request = youtube.search().list(
        part="snippet",
        q=query,
        maxResults=3,
        type="video,playlist",   
        videoDuration="long",   
        videoCategoryId="27",   
        order="viewCount"       
    )
    
    response = request.execute()
    
    video_urls = []
    for item in response.get("items", []):
        kind = item["id"]["kind"]
        if kind == "youtube#video":
            video_urls.append(f"https://www.youtube.com/watch?v={item['id']['videoId']}")
        elif kind == "youtube#playlist":
            video_urls.append(f"https://www.youtube.com/playlist?list={item['id']['playlistId']}")

    return video_urls

def main():
    try:
        print("Extracting text from PDFs...")
        resume_text = extract_text_from_pdf(PDF_PATH)
        job_description_text = extract_text_from_pdf(JOB_DESCRIPTION_PDF_PATH)
        
        analysis_prompt = f"""
        You are an AI that evaluates resumes based on job descriptions.
        
        Resume:
        {resume_text}
        
        Job Description:
        {job_description_text}
        
        Provide EXACTLY 3 specific areas for improvement.
        Prioritize technical skills first.
        Each area must be on a new line starting with '- IMPROVE: '
        """
        
        print("\nAnalyzing resume...")
        improvements = analyze_resume_with_llama(analysis_prompt)
        improvement_areas = extract_improvement_areas(improvements)
        
        if not improvement_areas:
            print("\nNo specific improvement areas identified. Retrying with a stricter prompt...")
            retry_prompt = f"""
            Reanalyze this resume and job description.
            List EXACTLY 3 areas for improvement, prioritizing technical skills first.
            Each area MUST start with '- IMPROVE: '
            
            Resume: {resume_text}
            Job Description: {job_description_text}
            """
            improvements = analyze_resume_with_llama(retry_prompt)
            improvement_areas = extract_improvement_areas(improvements)
        
        print("\nStored Improvement Areas:")
        for area in improvement_areas:
            print(f"- {area}")
        
        print("\nSearching YouTube for relevant videos...")
        video_recommendations = {}
        for area in improvement_areas:
            video_recommendations[area] = search_youtube_videos(area)
        
        for area, videos in video_recommendations.items():
            print(f"\nVideos for improvement area: {area}")
            for video in videos:
                print(video)
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()
