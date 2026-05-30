
# ─────────────────────────────────────────────────────────────
# [임포트]
# ─────────────────────────────────────────────────────────────
import traceback
# 예외 발생 시 상세한 스택 트레이스(오류 경로)를 문자열로 추출하는 표준 라이브러리.
# 현재 코드에서 임포트만 되고 실제로 사용되지는 않음.
# 추후 try/except 블록에서 에러 로깅 용도로 추가해둔 것으로 보인다.

import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

import requests
# requests : HTTP 요청을 보내는 외부 라이브러리.
# requests.get(url) 로 웹 페이지의 HTML을 가져온다.

from bs4 import BeautifulSoup
# BeautifulSoup : HTML/XML을 파싱(분석)하는 외부 라이브러리.
# requests로 받아온 HTML 문자열에서 원하는 태그의 텍스트를 추출할 수 있다.

from urllib.parse import urlparse
# urlparse : URL 문자열을 scheme / netloc / path 등의 구성요소로 분리하는 표준 라이브러리.
# 현재 코드에서 임포트만 되고 실제로 사용되지는 않음.
# URL 유효성 검사 등에 활용하려고 준비해둔 것으로 보인다.

from dotenv import load_dotenv

load_dotenv()
# .env 파일의 OPENAI_API_KEY 등 환경변수를 os.environ에 등록한다.

# ─────────────────────────────────────────────────────────────
# [전역 상수 - 프롬프트 템플릿]
# ─────────────────────────────────────────────────────────────
SUMMARIZE_PROMPT = """다음 제공된 콘텐츠의 핵심 내용을 약 300자 내외로 알기 쉽게 요약해주세요.
반드시 한국어로 자연스럽게 작성해야 합니다.

========
{content}
========
"""
# 삼중 따옴표(""") : 줄바꿈을 포함한 여러 줄 문자열(멀티라인 문자열)을 정의한다.
# {content} : chain.stream({'content': 실제텍스트}) 호출 시 실제 웹 페이지 내용으로 치환되는 플레이스홀더.
# ======== 구분선 : LLM이 '지시문'과 '처리할 데이터'를 명확히 구분하도록 돕는 시각적 구분자.
#   프롬프트 엔지니어링에서 입력 데이터 영역을 명시하는 일반적인 관행이다.

# ─────────────────────────────────────────────────────────────
# [페이지 초기화 함수]
# ─────────────────────────────────────────────────────────────
def init_page():
    st.set_page_config(page_title="웹 사이트 요약기", page_icon="🤗")
    # 브라우저 탭 제목과 파비콘 설정. 스크립트 당 한 번만 호출 가능.

    st.header("웹 사이트 요약기 🤗")
    # 앱 본문 상단 헤더 렌더링.

    st.sidebar.title("Options")
    # 사이드바 제목 설정.

# ─────────────────────────────────────────────────────────────
# [모델 선택 함수]
# ─────────────────────────────────────────────────────────────
def select_model(temperature=0):
    # temperature=0 : 함수 매개변수의 기본값(default parameter).
    # 호출 시 temperature를 따로 전달하지 않으면 자동으로 0이 사용된다.
    # 예) select_model()       → temperature=0
    #     select_model(0.7)    → temperature=0.7

    models = ("gpt-5.5", "gpt-5.4-mini")
    model = st.sidebar.radio("Choose a model:", models)
    # 사이드바 라디오 버튼으로 모델 선택. 선택된 모델명 문자열이 model에 담긴다.

    if model == 'gpt-5.5':
        return ChatOpenAI(temperature=temperature, model='gpt-5.5')
    else:
        return ChatOpenAI(temperature=temperature, model='gpt-5.4-mini')
    # if/else 분기로 선택된 모델에 맞는 ChatOpenAI 인스턴스를 생성해 반환한다.
    # 이전 앱에서 쓴 st.session_state 저장 없이 바로 return 하는 단순한 구조.

# ─────────────────────────────────────────────────────────────
# [체인 초기화 함수]
# ─────────────────────────────────────────────────────────────
def init_chain():
    llm = select_model()
    # select_model()을 호출해 사용자가 선택한 모델의 ChatOpenAI 인스턴스를 받는다.

    prompt = ChatPromptTemplate.from_messages([
        ('user', SUMMARIZE_PROMPT)])
    # 이번 앱은 대화 기록이 없는 단순 요약 앱이므로
    # system 메시지나 MessagesPlaceholder 없이 user 메시지 하나만 사용한다.
    # SUMMARIZE_PROMPT의 {content} 는 chain.stream() 호출 시 치환된다.

    chain = prompt | llm | StrOutputParser()
    # LCEL 파이프라인 : 프롬프트 → LLM → 문자열 파서 순으로 연결.

    return chain

# ─────────────────────────────────────────────────────────────
# [웹 페이지 내용 추출 함수]
# ─────────────────────────────────────────────────────────────
def get_content(url):
    with st.spinner('웹 사이트 정보 찾는중...'):
    # 이 with 블록이 실행되는 동안 화면에 로딩 스피너를 표시한다.

        url = requests.get(url)
        # requests.get(url) : 해당 URL에 HTTP GET 요청을 보내고
        # 응답(Response 객체)을 반환한다.
        # ※ 변수명 url을 재사용해 덮어쓰고 있다.
        #   url(문자열) → url(Response 객체) 로 바뀌어 혼동될 수 있다.

        html = BeautifulSoup(url.text)
        # url.text : Response 객체에서 HTML 문자열을 추출.
        # BeautifulSoup(html문자열) : HTML을 파싱해 태그 탐색이 가능한 객체로 변환.
        # ※ 파서를 명시하지 않아 경고가 발생할 수 있다.
        #   권장 방식 : BeautifulSoup(url.text, 'html.parser')

        if html.main:
            return html.main.text
        elif html.article:
            return html.article.text
        else:
            return html.body.text
        # 웹 페이지 구조에 따라 핵심 콘텐츠 영역을 우선순위로 추출한다.
        #
        # 우선순위 로직 :
        #   1순위 : <main> 태그   → 페이지 주요 콘텐츠 영역 (가장 정확)
        #   2순위 : <article> 태그 → 블로그/뉴스 기사 본문
        #   3순위 : <body> 태그   → 위 두 태그가 없을 때 전체 본문 (노이즈 많음)
        #
        # .text : BeautifulSoup 태그 객체에서 HTML 태그를 제거한 순수 텍스트만 추출.

# ─────────────────────────────────────────────────────────────
# [메인 함수]
# ─────────────────────────────────────────────────────────────
def main():
    init_page()
    chain = init_chain()
    # 페이지 설정 → 체인 생성 순서로 초기화.

    if url := st.text_input("URL: ", key='input'):
    # := (바다코끼리 연산자) :
    #   st.text_input()의 반환값을 url에 할당하는 동시에
    #   빈 문자열(False)이 아닌지 조건 검사를 한 번에 수행한다.
    # st.text_input() : 한 줄 텍스트 입력창을 렌더링하고 입력된 문자열을 반환.
    # 아무것도 입력되지 않으면 빈 문자열("") → 조건이 False → 블록 건너뜀.

        if content := get_content(url):
        # url을 get_content()에 전달해 웹 페이지 텍스트를 가져오고
        # 동시에 content 변수에 할당 + None/빈문자열 여부를 확인한다.
        # content가 있을 때만 아래 요약 블록을 실행한다.

            st.markdown("## Summary")
            # 마크다운 형식의 소제목을 렌더링.

            st.write_stream(chain.stream({'content': content}))
            # chain.stream({'content': content}) :
            #   SUMMARIZE_PROMPT의 {content} 자리에 웹 페이지 텍스트를 주입하고
            #   LLM이 토큰을 생성할 때마다 청크를 yield 하는 제너레이터를 반환.
            # st.write_stream() :
            #   제너레이터를 받아 토큰이 오는 즉시 화면에 이어 써 실시간 타이핑 효과를 낸다.

            st.markdown("-----")
            # 수평선(구분선) 렌더링.

            st.markdown("## Original Text")
            st.write(content)
            # 요약 아래에 원본 텍스트 전체를 표시한다.
            # st.write() : 문자열, 데이터프레임 등 다양한 타입을 자동 감지해 렌더링.

main()
# 모든 함수 정의 후 진입점으로 main() 호출.
# Streamlit rerun마다 이 한 줄이 전체 앱 흐름을 다시 실행한다.

# ═════════════════════════════════════════════════════════════
# [전체 앱 요약]
# ═════════════════════════════════════════════════════════════
# URL을 입력하면 해당 웹 페이지의 내용을 크롤링해 GPT로 요약해주는 앱.
#
# ┌─ 실행 흐름 ─────────────────────────────────────────────┐
# │  main()                                                  │
# │   ├── init_page()     페이지/사이드바 UI 설정             │
# │   ├── init_chain()    모델 선택 → LCEL 체인 생성          │
# │   ├── st.text_input() 사용자로부터 URL 입력 수신          │
# │   ├── get_content()   requests로 HTML 가져오기            │
# │   │    └── BeautifulSoup으로 main/article/body 텍스트 추출│
# │   ├── chain.stream()  텍스트 → LLM → 실시간 요약 출력    │
# │   └── st.write()      원본 텍스트 표시                    │
# └──────────────────────────────────────────────────────────┘
#
# 핵심 설계 포인트 :
#   1. requests + BeautifulSoup — URL에서 핵심 텍스트 자동 추출
#   2. 우선순위 태그 탐색(main → article → body) — 노이즈 최소화
#   3. st.write_stream — 요약 결과를 실시간 타이핑 효과로 출력
#   4. 바다코끼리 연산자(:=) — 입력 수신 + 조건 검사를 한 줄로 처리
