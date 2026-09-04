import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# --------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스")
st.caption("KOBIS 영화관입장권통합전산망의 일일 박스오피스를 보여 줍니다.")


# --------------------------------------------------
# 2. 한국 시간 기준으로 '어제' 날짜 계산
# --------------------------------------------------
# Streamlit Cloud 서버가 한국 시간이 아닐 수 있기 때문에
# 서버의 현재 시간을 그대로 사용하지 않습니다.
#
# ZoneInfo("Asia/Seoul")을 사용해서 한국 시간을 가져옵니다.

KST = ZoneInfo("Asia/Seoul")

now_korea = datetime.now(KST)

# 한국 시간 기준 어제
yesterday = now_korea.date() - timedelta(days=1)

# KOBIS API가 요구하는 날짜 형식: yyyymmdd
target_date = yesterday.strftime("%Y%m%d")

# 화면에 보여 줄 날짜
display_date = yesterday.strftime("%Y-%m-%d")


# --------------------------------------------------
# 3. KOBIS API 주소
# --------------------------------------------------

API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)


# --------------------------------------------------
# 4. API에서 박스오피스 가져오기
# --------------------------------------------------
# ttl=3600
# → 한 번 가져온 결과를 약 1시간 동안 기억합니다.
#
# 같은 날짜를 다시 조회하면 그동안에는 API를 다시 호출하지 않습니다.
#
# target_date를 함수의 매개변수로 넣었기 때문에
# 날짜가 바뀌면 새로운 결과를 가져옵니다.

@st.cache_data(ttl=3600)
def get_boxoffice(target_date):
    # Streamlit Secrets에 저장한 인증키를 가져옵니다.
    # 실제 인증키는 코드에 적지 않습니다.
    try:
        api_key = st.secrets["KOBIS_KEY"]
    except Exception:
        return {
            "success": False,
            "message": (
                "KOBIS_KEY를 찾을 수 없습니다.\n\n"
                "Streamlit Cloud의 Secrets에 "
                "`KOBIS_KEY`가 정확한 이름으로 등록되어 있는지 확인하세요."
            ),
            "data": None
        }

    # API에 전달할 요청값
    params = {
        "key": api_key,
        "targetDt": target_date
    }

    try:
        # KOBIS API 요청
        response = requests.get(
            API_URL,
            params=params,
            timeout=10
        )

        # HTTP 오류가 발생했는지 확인
        response.raise_for_status()

        # JSON 형태로 변환
        data = response.json()

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": (
                "KOBIS API 응답 시간이 초과되었습니다.\n\n"
                "잠시 후 다시 실행해 보세요."
            ),
            "data": None
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": (
                "KOBIS API 요청에 실패했습니다.\n\n"
                f"오류 내용: {e}\n\n"
                "인터넷 연결이나 KOBIS API 서버 상태를 확인해 보세요."
            ),
            "data": None
        }

    except ValueError:
        return {
            "success": False,
            "message": (
                "KOBIS API의 응답을 JSON으로 읽을 수 없습니다.\n\n"
                "KOBIS API 서버의 응답 상태를 확인해 보세요."
            ),
            "data": None
        }

    # --------------------------------------------------
    # 5. 인증키 오류 확인
    # --------------------------------------------------
    # KOBIS는 인증키가 틀려도 HTTP 상태코드가 200으로
    # 올 수 있습니다.
    #
    # 따라서 status_code만 확인하면 안 되고
    # faultInfo가 있는지 반드시 확인해야 합니다.

    if "faultInfo" in data:
        fault_info = data["faultInfo"]

        fault_code = fault_info.get("errorCode", "알 수 없음")
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
    # 6. boxOfficeResult 확인
    # --------------------------------------------------

    boxoffice_result = data.get("boxOfficeResult")

    if not boxoffice_result:
        return {
            "success": False,
            "message": (
                "KOBIS API 응답에 `boxOfficeResult`가 없습니다.\n\n"
                "API 응답 형식이나 KOBIS 서버 상태를 확인해 보세요."
            ),
            "data": None
        }

    # 영화 목록 가져오기
    movie_list = boxoffice_result.get("dailyBoxOfficeList", [])

    # 영화 목록이 비어 있는 경우
    if not movie_list:
        return {
            "success": False,
            "message": (
                f"{display_date}의 박스오피스 영화 목록이 없습니다.\n\n"
                "다음 내용을 확인해 보세요.\n"
                "• 조회 날짜가 맞는지 확인\n"
                "• 해당 날짜의 영화관입장권 데이터가 존재하는지 확인\n"
                "• KOBIS API 서버 상태 확인"
            ),
            "data": None
        }

    return {
        "success": True,
        "message": "",
        "data": movie_list
    }


# --------------------------------------------------
# 7. API 호출
# --------------------------------------------------

result = get_boxoffice(target_date)


# --------------------------------------------------
# 8. API 요청에 실패한 경우
# --------------------------------------------------

if not result["success"]:
    st.error("⚠️ 박스오피스 정보를 가져오지 못했습니다.")

    # 여러 줄의 안내문을 보기 좋게 출력
    st.warning(result["message"])

    st.info(
        "💡 확인할 것\n"
        "1. Streamlit Cloud → Settings → Secrets에서 "
        "`KOBIS_KEY`가 등록되어 있는지 확인하세요.\n"
        "2. 인증키를 복사할 때 앞뒤에 불필요한 문자가 없는지 확인하세요.\n"
        "3. KOBIS API 서버가 정상적으로 동작하는지 확인하세요."
    )

    # 이후 코드는 실행하지 않음
    st.stop()


# --------------------------------------------------
# 9. 영화 데이터를 DataFrame으로 변환
# --------------------------------------------------

movie_list = result["data"]

df = pd.DataFrame(movie_list)


# --------------------------------------------------
# 10. 숫자로 변환
# --------------------------------------------------
# KOBIS API는 숫자도 문자열로 보내 줍니다.
#
# 예:
# "1"       → 1
# "15234"   → 15234
#
# 그래프와 정렬에 제대로 사용하려면 숫자로 바꿔야 합니다.

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


# --------------------------------------------------
# 11. 순위 기준으로 정렬
# --------------------------------------------------

df = df.sort_values("rank").reset_index(drop=True)


# --------------------------------------------------
# 12. 날짜와 데이터 개수 표시
# --------------------------------------------------

st.subheader(f"📅 {display_date} 박스오피스")

st.caption(
    f"한국 시간 기준 어제의 데이터 · 총 {len(df)}편"
)


# --------------------------------------------------
# 13. 1위 영화 정보
# --------------------------------------------------

first_movie = df.iloc[0]

first_movie_name = first_movie["movieNm"]
first_audience = first_movie["audiCnt"]
first_total = first_movie["audiAcc"]


st.markdown("### 🥇 1위 영화")


# --------------------------------------------------
# 14. 1위 영화 지표 카드 3개
# --------------------------------------------------

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


# --------------------------------------------------
# 15. 관객수 상위 5편 막대그래프
# --------------------------------------------------

st.markdown("### 📊 관객수 상위 5편")


# 관객수가 많은 순서로 정렬
top5 = (
    df.sort_values(
        "audiCnt",
        ascending=False
    )
    .head(5)
    .copy()
)

# 영화명을 그래프의 인덱스로 사용
top5_chart = top5.set_index("movieNm")[["audiCnt"]]

# Streamlit 기본 막대그래프
st.bar_chart(
    top5_chart,
    y="audiCnt",
    horizontal=True
)


# --------------------------------------------------
# 16. 전체 박스오피스 표
# --------------------------------------------------

st.markdown("### 🎞️ 전체 박스오피스")


# 화면에 보여 줄 열
table_df = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()


# 사용자가 보기 쉬운 한국어 열 이름으로 변경
table_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]


# 숫자에 천 단위 쉼표 표시
# 화면 표시용이므로 실제 df의 숫자 데이터는 그대로 유지됩니다.
table_df["관객수"] = table_df["관객수"].map(
    lambda x: f"{x:,}"
)

table_df["누적관객"] = table_df["누적관객"].map(
    lambda x: f"{x:,}"
)

table_df["스크린수"] = table_df["스크린수"].map(
    lambda x: f"{x:,}"
)


# 표 출력
st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 17. 데이터 출처
# --------------------------------------------------

st.caption(
    "데이터 출처: 영화관입장권통합전산망(KOBIS) 일일 박스오피스 API"
)
