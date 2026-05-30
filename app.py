import streamlit as st
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

def get_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        return parse_qs(parsed.query).get("v", [None])[0]
    elif parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")
    return None

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["ko", "en"])
        return " ".join([t["text"] for t in transcript])
    except Exception as e:
        return None

def summarize(text):
    prompt = ChatPromptTemplate.from_template(
        "다음 유튜브 영상 자막을 한국어로 핵심 내용 위주로 요약해줘:\n\n{text}"
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"text": text[:8000]})

st.title("🎬 유튜브 영상 요약기")
url = st.text_input("유튜브 URL을 입력하세요")

if st.button("요약하기"):
    if not url:
        st.warning("URL을 입력해주세요.")
    else:
        video_id = get_video_id(url)
        if not video_id:
            st.error("올바른 유튜브 URL이 아니에요.")
        else:
            with st.spinner("자막 가져오는 중..."):
                transcript = get_transcript(video_id)
            if not transcript:
                st.error("자막을 가져올 수 없어요. 자막이 없는 영상일 수 있어요.")
            else:
                with st.spinner("요약 중..."):
                    result = summarize(transcript)
                st.success("요약 완료!")
                st.write(result)
