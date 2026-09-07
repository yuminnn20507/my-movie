import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ==================================================
# 1. 페이지 기본 설정
# ==================================================

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 박스오피스")
st.caption("KOBIS 영화관입장권통합전산망의 일일 박스오피스를 보여 줍니다.")


# ==================================================
# 2. 한국 시간 기준 날짜 계산
# ==================================================
# Streamlit Cloud 서버는 한국 시간이 아닐 수 있습니다.
# 따라서 반드시 한국 시간(Asia/Seoul)을 기준으로 합니다.

KST = ZoneInfo("Asia/Seoul")

now_korea = datetime.now(KST)

# 오늘 날짜
today_korea = now_korea.date()

# 선택할 수 있는 가장 늦은 날짜 = 어제
yesterday = today_korea - timedelta(days=1)


# ==================================================
# 3. KOBIS API 주소
# ==================================================

API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)


# ==================================================
# 4. KOBIS API에서 박스오피스 가져오기
# ==================================================
# 같은 날짜를 다시 조회하면 1시간 동안 저장된 결과를 사용합니다.
# 따라서 같은 날짜로 계속 조회해도 API를 매번 호출하지 않습니다.

@st.cache_data(ttl=3600)
def get_boxoffice(target_date):

    # --------------------------------------------------
    # Secrets에서 인증키 가져오기
    # --------------------------------------------------
    try:
        api_key = st.secrets["KOBIS_KEY"]

    except Exception:
        return {
            "success": False,
            "message": (
                "KOBIS_KEY를 찾을 수 없습니다.\n\n"
                "Streamlit Cloud → App settings → Secrets에서 "
                "`KOBIS_KEY`가 정확한 이름으로 등록되어 있는지 확인하세요."
            ),
            "data": None
        }

    # --------------------------------------------------
    # API 요청
    # --------------------------------------------------
    params = {
        "key": api_key,
        "targetDt": target_date
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": (
                "KOBIS API 응답 시간이 초과되었습니다.\n\n"
                "잠시 후 다시 시도해 주세요."
            ),
            "data": None
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": (
                "KOBIS API 요청에 실패했습니다.\n\n"
                f"오류 내용: {e}\n\n"
                "인터넷 연결이나 KOBIS API 서버 상태를 확인해 주세요."
            ),
            "data": None
        }

    except ValueError:
        return {
            "success": False,
            "message": (
                "KOBIS API의 응답을 읽을 수 없습니다.\n\n"
                "KOBIS API 서버 상태를 확인해 주세요."
            ),
            "data": None
        }

    # --------------------------------------------------
    # 인증키 오류 확인
    # --------------------------------------------------
    # KOBIS는 인증키가 틀려도 HTTP 상태코드가 200일 수 있습니다.
    # 따라서 faultInfo가 있는지 반드시 확인합니다.

    if "faultInfo" in data:

        fault_info = data["faultInfo"]

        fault_code = fault_info.get(
            "errorCode",
            "알 수 없음"
        )

        fault_message = fault_info.get(
            "errorMessage",
            "알 수 없는 오류입니다."
        )

        return {
            "success": False,
            "message": (
                "KOBIS API에서 오류를 반환했습니다.\n\n"
                f"오류 코드: {fault_code}\n"
                f"오류 내용: {fault_message}\n\n"
                "Streamlit Cloud의 Secrets에 등록한 "
                "`KOBIS_KEY`가 정확한지 확인하세요."
            ),
            "data": None
        }

    # --------------------------------------------------
    # boxOfficeResult 확인
    # --------------------------------------------------

    boxoffice_result = data.get("boxOfficeResult")

    if not boxoffice_result:
        return {
            "success": False,
            "message": (
                "KOBIS API 응답에 박스오피스 정보가 없습니다.\n\n"
                "KOBIS API 서버 상태를 확인해 주세요."
            ),
            "data": None
        }

    # 영화 목록 가져오기
    movie_list = boxoffice_result.get(
        "dailyBoxOfficeList",
        []
    )

    # --------------------------------------------------
    # 영화 목록이 비어 있는 경우
    # --------------------------------------------------
    # 사용자가 날짜를 선택했지만 데이터가 없다면
    # 빈 화면 대신 이해하기 쉬운 메시지를 보여 줍니다.

    if not movie_list:
        return {
            "success": True,
            "message": "그날은 아직 집계 전입니다.",
            "data": []
        }

    return {
        "success": True,
        "message": "",
        "data": movie_list
    }


# ==================================================
# 5. 날짜 선택
# ==================================================

st.markdown("### 📅 조회할 날짜")

selected_date = st.date_input(
    "박스오피스를 확인할 날짜를 선택하세요.",
    value=yesterday,
    max_value=yesterday,
    format="YYYY-MM-DD"
)

# KOBIS API가 요구하는 날짜 형식
target_date = selected_date.strftime("%Y%m%d")

# 화면에 표시할 날짜
display_date = selected_date.strftime("%Y-%m-%d")


# ==================================================
# 6. 선택한 날짜의 박스오피스 가져오기
# ==================================================

result = get_boxoffice(target_date)


# ==================================================
# 7. API 요청 자체가 실패한 경우
# ==================================================

if not result["success"]:

    st.error("⚠️ 박스오피스 정보를 가져오지 못했습니다.")

    st.warning(result["message"])

    st.info(
        "💡 확인할 것\n\n"
        "1. Streamlit Cloud → App settings → Secrets에서 "
        "`KOBIS_KEY`가 등록되어 있는지 확인하세요.\n\n"
        "2. 인증키를 복사할 때 불필요한 문자가 들어가지 않았는지 확인하세요.\n\n"
        "3. KOBIS API 서버가 정상적으로 동작하는지 확인하세요."
    )

    st.stop()


# ==================================================
# 8. 영화 목록이 없는 경우
# ==================================================

movie_list = result["data"]

if not movie_list:

    st.warning(
        f"📭 {display_date}의 박스오피스 데이터가 없습니다."
    )

    st.info(
        "그날은 아직 집계 전입니다.\n\n"
        "다른 날짜를 선택해 보세요."
    )

    st.stop()


# ==================================================
# 9. DataFrame으로 변환
# ==================================================

df = pd.DataFrame(movie_list)


# ==================================================
# 10. 숫자 데이터를 실제 숫자로 변환
# ==================================================
# KOBIS API에서는 숫자도 문자열로 보내 줍니다.
#
# 예:
# "1" → 1
# "259744" → 259744
#
# 숫자로 변환해야 정렬과 그래프에 제대로 사용할 수 있습니다.

number_columns = [
    "rank",
    "rankInten",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "showCnt"
]

for column in number_columns:

    if column in df.columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0).astype(int)


# ==================================================
# 11. 순위 기준으로 정렬
# ==================================================

df = df.sort_values(
    "rank",
    ascending=True
).reset_index(drop=True)


# ==================================================
# 12. 화면 상단 날짜 표시
# ==================================================

st.subheader(
    f"📅 {display_date} 박스오피스"
)

st.caption(
    f"한국 시간 기준 · 총 {len(df)}편"
)


# ==================================================
# 13. 1위 영화 정보
# ==================================================

first_movie = df.iloc[0]

first_movie_name = first_movie["movieNm"]
first_audience = first_movie["audiCnt"]
first_total = first_movie["audiAcc"]


st.markdown("### 🥇 1위 영화")


# ==================================================
# 14. 1위 영화 지표 카드
# ==================================================

card1, card2, card3 = st.columns(3)


with card1:

    st.metric(
        label="🎬 영화",
        value=first_movie_name
    )


with card2:

    st.metric(
        label="👥 일일 관객수",
        value=f"{first_audience:,}명"
    )


with card3:

    st.metric(
        label="👥 누적 관객수",
        value=f"{first_total:,}명"
    )


# ==================================================
# 15. 관객수 상위 5편
# ==================================================

st.markdown("### 📊 관객수 상위 5편")


top5 = (
    df.sort_values(
        "audiCnt",
        ascending=False
    )
    .head(5)
    .copy()
)


# 영화명을 그래프의 이름으로 사용
top5_chart = top5.set_index(
    "movieNm"
)[["audiCnt"]]


# 가로 막대그래프
st.bar_chart(
    top5_chart,
    y="audiCnt",
    horizontal=True
)


# ==================================================
# 16. 전체 박스오피스 표
# ==================================================

st.markdown("### 🎞️ 전체 박스오피스")


# --------------------------------------------------
# 표에 사용할 데이터 복사
# --------------------------------------------------

table_df = df[
    [
        "rank",
        "rankInten",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()


# ==================================================
# 17. 순위 증감 표시
# ==================================================
# rankInten
#
# 양수 → 순위 상승 → 빨간색 ↑
# 음수 → 순위 하락 → 파란색 ↓
# 0    → 변동 없음
#
# 예:
# +2 → 🔴 ↑2
# -1 → 🔵 ↓1
#  0 → -
#
# 표에서는 이 값을 보기 좋게 문자열로 만들어 줍니다.

def make_rank_change(value):

    if value > 0:
        return f"🔴 ↑{value}"

    elif value < 0:
        return f"🔵 ↓{abs(value)}"

    else:
        return "-"


table_df["순위 변동"] = table_df[
    "rankInten"
].apply(make_rank_change)


# ==================================================
# 18. 누적 관객 100만 명 이상이면 트로피 추가
# ==================================================
# 1,000,000명 이상인 영화 이름 뒤에 🏆를 붙입니다.

def add_trophy(row):

    movie_name = row["movieNm"]
    accumulated = row["audiAcc"]

    if accumulated >= 1_000_000:
        return f"{movie_name} 🏆"

    return movie_name


table_df["영화명"] = table_df.apply(
    add_trophy,
    axis=1
)


# ==================================================
# 19. 표의 열 이름 변경
# ==================================================

table_df = table_df[
    [
        "rank",
        "순위 변동",
        "영화명",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
]


table_df.columns = [
    "순위",
    "순위 변동",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]


# ==================================================
# 20. 숫자에 천 단위 쉼표 표시
# ==================================================
# 화면에서 보기 좋게 만들기 위한 작업입니다.
#
# 실제 계산용 df의 숫자는 그대로 숫자입니다.

table_df["관객수"] = table_df[
    "관객수"
].map(
    lambda x: f"{x:,}"
)


table_df["누적관객"] = table_df[
    "누적관객"
].map(
    lambda x: f"{x:,}"
)


table_df["스크린수"] = table_df[
    "스크린수"
].map(
    lambda x: f"{x:,}"
)


# ==================================================
# 21. 표 출력
# ==================================================

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True
)


# ==================================================
# 22. 데이터 출처
# ==================================================

st.caption(
    "데이터 출처: 영화관입장권통합전산망(KOBIS) "
    "일일 박스오피스 API"
)
