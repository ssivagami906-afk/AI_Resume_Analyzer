import os
from openai import OpenAI
import json
from dotenv import load_dotenv
load_dotenv(override=True)

def setup_nvidia():
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "NVIDIA_API_KEY" in st.secrets:
                api_key = st.secrets["NVIDIA_API_KEY"]
        except Exception:
            pass
    if not api_key:
        raise ValueError("NVIDIA_API_KEY not found in environment variables or Streamlit Secrets. Please set it.")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    return client

def analyze_resume(resume_text: str, qualifications: str) -> dict:
    """
    Analyzes the resume text against the qualifications.
    Returns a dictionary with 'approved' (boolean) and 'reason' (string).
    """
    try:
        client = setup_nvidia()
        
        prompt = f"""
        You are an expert HR Technical Recruiter.
        I will provide you with a candidate's resume text and the required job qualifications.
        
        Job Qualifications:
        {qualifications}
        
        Candidate Resume Text:
        {resume_text}
        
        Task: Analyze the resume strictly against the qualifications. 
        Determine if the candidate is a good fit (approved) or not (declined).
        
        Provide the response strictly in JSON format with two keys:
        - "approved": a boolean (true if the candidate meets the core qualifications, false otherwise)
        - "reason": a short 1-2 sentence string explaining why they were approved or declined.
        
        Return ONLY valid JSON, nothing else.
        """
        
        response = client.chat.completions.create(
            model='meta/llama-3.1-70b-instruct',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=256
        )
        text_resp = response.choices[0].message.content.strip()
        
        # Clean up markdown formatting if present
        if text_resp.startswith("```json"):
            text_resp = text_resp.replace("```json", "").replace("```", "").strip()
        elif text_resp.startswith("```"):
            text_resp = text_resp.replace("```", "").strip()
            
        result = json.loads(text_resp)
        return result
        
    except Exception as e:
        print(f"Error analyzing resume: {e}")
        return {"approved": False, "reason": f"Analysis failed due to error: {str(e)}"}
