

from langchain_anthropic import ChatAnthropic
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
from langgraph.graph import END
from typing import TypedDict

import os

from dotenv import load_dotenv
load_dotenv()

start_message = "--------------------------------------------------------------\n# ai-agent start"
print(start_message)

class SpamChecker(BaseModel):
    """PC 게임, Mobile 게임, Online Game과 관련된 이메일인지 확인합니다."""

    is_related_game: bool = Field(
        description="이 기사가 PC 게임, mobile 게임, online Game, computer game과 관련된 내용인지 아닌지를 'true' or 'false' 로 제공해주세요."
    )


class ArticlePostabilityChecker(BaseModel):
    """Binary scores for postability check, word count, sensationalism, and language verification of a news article."""

    can_be_posted: bool = Field(
        description="The article is ready to be posted, 'true' or 'false'"
    )

    is_korean: bool = Field(
        description="The language of the article is korean, 'true' or 'false'"
    )


evaluator_llm = ChatAnthropic(model="claude-3-5-sonnet-20240620",temperature=0,max_tokens=2048)
structured_evaluator_llm = evaluator_llm.with_structured_output(SpamChecker)

evaluator_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "당신은 제공된 내용이 PC Game, Mobile Game, Online Game, Computer Game과 관련된 내용인지를 확인하는 전문가입니다. yes 또는 no로 결과를 제공해주세요"),
        ("human", "News Article:\n\n {article}")
    ]
)

evaluator = evaluator_prompt | structured_evaluator_llm

reviewer_llm = ChatAnthropic(model="claude-3-5-sonnet-20240620",temperature=0,max_tokens=2048)

structured_reviewer_llm = reviewer_llm.with_structured_output(ArticlePostabilityChecker)

reviewer_system = """당신은 뉴스 기사가 게시할 준비가 되었는지, 한국어로 작성되었는지 등을 평가합니다. \n
    만약 컨텐츠가 html 태그를 포함하고 있다면, 이를 제거하고 평가해주세요. \n
    Evaluate the article for grammatical errors, completeness, appropriateness for publication \n
    Also, confirm if the language used in the article is korean \n
    Provide two binary scores: one to indicate if the article can be posted ('true' or 'false'), and another if the language is Korean ('true' or 'false')."""

reviewer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", reviewer_system),
        ("human", "News Article:\n\n {article}")
    ]
)

reviewer = reviewer_prompt | structured_reviewer_llm

translator_llm = ChatAnthropic(model="claude-3-5-sonnet-20240620",temperature=0,max_tokens=2048)

translator_system = """
You are a translator converting articles into Korean. Translate the text accurately while maintaining the original tone and style.
"""

translator_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", translator_system),
        ("human", "Article to translate:\n\n {article}")
    ]
)

translator = translator_prompt | translator_llm

writer_llm = ChatAnthropic(model="claude-3-5-sonnet-20240620",temperature=0,max_tokens=2048)
writer_system = """
당신은 전문 게임관련 기자입니다. 그리고 제공된 내용을 기반으로 뉴스 기사를 작성하는 임무를 맡은 작성자입니다.
기사는 2000자 내외로 작성해주세요. 
한국어로 작성해주세요.
그리고 제공한 내용에 없는 내용은 포함하지 마시요.
기사는 아래형식으로 표시해주세요 

제목: ___
내용: ___
"""
writer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", writer_system),
        ("human", "Content:\n\n {article}")
    ]
)

writer = writer_prompt | writer_llm

class AgentState(TypedDict):
    article_state: str


def is_game_news(state: AgentState) -> AgentState:
    print(f"게임관련 뉴스인지 확인")
    return state

def evaluate_article(state: AgentState) -> AgentState:
    print(f"이메일 내용 평가")
    return state


def translate_article(state: AgentState) -> AgentState:
    print(f"번역 작업")
    article = state["article_state"]
    result = translator.invoke({"article": article})
    state["article_state"] = result.content
    return state

def publisher(state: AgentState) -> AgentState:
    print(f"기사 작성")
    result = writer.invoke({"article": state["article_state"]})
    print("\n\n-------------------\n기사: ", result.content)
    return state

def spamchecker_router(state: AgentState) -> Literal["reviewer", "not_relevant"]:
    article = state["article_state"]
    evaluator = evaluator_prompt | structured_evaluator_llm
    result = evaluator.invoke({"article": article})
    print("evaluator result: ", result)
    if result.is_related_game:
        return "reviewer"
    else:
        return "not_relevant"


def reviewer_router(state: AgentState) -> Literal["translator", "publisher", "not_relevant"]:
    article = state["article_state"]
    result = reviewer.invoke({"article": article})
    print("reviewer result: ", result)
    if result.can_be_posted:
        if result.is_korean == True:
            return "publisher"
        else:
            return "translator"
    else:
        print("기사로 쓸만한 가치가 없음")
        return "not_relevant"


workflow = StateGraph(AgentState)

workflow.add_node("evaluator", is_game_news)
workflow.add_node("reviewer", evaluate_article)
workflow.add_node("translator", translate_article)
workflow.add_node("publisher", publisher)

workflow.set_entry_point("evaluator")

workflow.add_conditional_edges(
    "evaluator", spamchecker_router, {"reviewer": "reviewer", "not_relevant": END}
)
workflow.add_conditional_edges(
    "reviewer", reviewer_router ,{ "translator": "translator", "publisher": "publisher", "not_relevant": END },
)

workflow.add_edge("translator", "reviewer")
workflow.add_edge("publisher", END)

app = workflow.compile()

with open('./langgraph/langgraph.png', 'wb') as file:
    file.write(app.get_graph().draw_mermaid_png())

article = """
그라비티, 라그나로크 온라인 글로벌 e스포츠 대회 ‘ROS 2024 한국 대표 선발전’ 개최!
- 총 5개 팀 본선 진출, ROS 2024 한국 대표 출전권 걸고 치열한 대결 예고
- 우승팀에 태국 ROS 2024 참가 자격 부여 및 비용 전액 지원 등 혜택
글로벌 게임 기업 그라비티가 3일 대표 온라인 PC MMORPG ‘라그나로크 온라인’의 글로벌 e스포츠 대회 ‘ROS(라그나로크 온라인 스타즈) 2024 한국 대표 선발전’을 오프라인 개최한다.
ROS 2024는 전 세계적으로 많은 사랑을 받고 있는 라그나로크 IP를 활용한 글로벌 e스포츠 대회이다. 지난해 10월, ‘RWC 2013(라그나로크 월드 챔피언십)’ 이후 10년 만에 인도네시아 자카르타에서 개최한 ROS 2023 현장에는 약 2만 명 이상의 유저들이 모여 라그나로크 온라인과 ROS에 대한 유저들의 뜨거운 열정을 실감케 했다. 올해 대회는 10월 태국 방콕에서 개최하며 한국을 포함해 대만, 동남아시아 등 총 7개 지역의 라그나로크 온라인 대표가 모여 경기를 치를 예정이다.
그라비티는 지난 5월 ROS 2024 한국 대표 선발전 참가 신청 페이지를 오픈하고 7월 7일까지 참가 신청을 받았다. ‘이카루스’, ‘이카루스:제로’, ‘포링연합’, ‘WIND’, ‘달콤한놈들’ 총 5개 팀이 본선에 진출했으며 ROS 2024 한국 대표 출전권을 놓고 최종 대결을 펼친다.
한국 대표 선발전은 대회 안내 및 조 편성, 토너먼트, 결승전, 결승 진출팀 시상식, ROS 2024 일정 안내로 진행한다. 대진 편성은 현장에서 각 팀 대표가 추첨에 참여해 A조 세 팀, B조 두 팀으로 나눠 5전 3선승제로 진행한다. 결승전은 각 조 1위팀 간 7전 4선승제로 이뤄지며 각각의 대전 시간은 10분씩 주어진다. 결승전을 진행하기 전에 3, 4위 순위 결정전도 열린다.
대회 보상으로는 우승, 준우승, 3위를 차지한 모든 팀에 공통으로 ROS 전용 한정 의상 패키지를 제공한다. 이와 함께 우승팀에게는 태국 ROS 2024 참가 자격 부여 및 비용 전액 지원과 더불어 상금 100만 원을 수여하며 준우승팀에게는 50만 원을 부상으로 증정한다. 이 밖에도 대회 참가자 전원에 ROS 참가 패키지를 선물한다.
라그나로크 온라인 김성진 PM은 “올해 역시 ROS에 많은 성원을 보내주신 한국 유저분들께 감사의 말씀을 드린다. 본선에 진출한 다섯 개 팀 모두 끝까지 제 실력을 발휘해 후회 없는 승부를 펼치시기 바란다”라고 전했다.
라그나로크 온라인 ROS 2024 한국 대표 선발전에 대한 보다 자세한 내용은 ROS 2024 한국 대표 선발전 페이지(https://ro.gnjoy.com/match/2024/)에서 확인 가능하다.
"""

initial_state = {"article_state": article}

app.invoke(initial_state)

