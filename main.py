import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="영화 데이터 그래프 도감 2 - 분포와 관계",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 영화 데이터 그래프 도감 2 - 분포와 관계")
st.markdown("KOBIS 영화 박스오피스 데이터를 통해 영화 시청 트렌드, 장르별 분포 및 수치 간의 관계를 분석합니다.")

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    # 장르 전처리: 벡터화 함수(.str)를 사용하여 세로막대 기호(|) 기준 첫 번째 장르만 추출
    df['primary_genre'] = df['genre'].fillna('기타').astype(str).str.split('|').str[0]
    return df

try:
    df = load_data()
    st.success(f"데이터를 성공적으로 불러왔습니다! (총 {len(df)}편)")
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

st.divider()

st.subheader("📊 1. 장르별 영화 편수 분포 (도넛 차트)")

genre_counts = df['primary_genre'].value_counts().reset_index()
genre_counts.columns = ['장르', '편수']

fig1 = px.pie(
    genre_counts,
    names='장르',
    values='편수',
    hole=0.4,
    title="장르별 영화 편수 비율",
    color_discrete_sequence=px.colors.qualitative.Pastel
)

fig1.update_traces(
    hoverinfo='label+value+percent',
    textinfo='percent+label',
    hovertemplate="<b>장르: %{label}</b><br>편수: %{value}편<br>비율: %{percent}"
)

fig1.update_layout(
    margin=dict(t=50, b=20, l=20, r=20),
    legend_title_text="장르"
)

st.plotly_chart(fig1, use_container_width=True)
st.info("💡 **이 그래프로 알 수 있는 것:** 개봉한 영화 중 특정 대표 장르(드라마, 액션 등)가 차상위 장르들에 비해 확연히 높은 비중을 차지하고 있음을 알 수 있습니다.")

st.divider()

st.subheader("📈 2. 개봉 첫 주 관객수 vs 총 관객수 관계")

fig2 = px.scatter(
    df,
    x='first_week_audi',
    y='total_audi',
    color='primary_genre',
    size='days_in_top10',
    hover_name='movieNm',
    labels={
        'first_week_audi': '개봉 첫 주 관객수',
        'total_audi': '총 관객수',
        'primary_genre': '장르',
        'days_in_top10': 'Top 10 유지 일수'
    },
    title="개봉 첫 주 관객수와 총 관객수의 상관관계"
)

fig2.update_layout(margin=dict(t=50, b=20, l=20, r=20))
st.plotly_chart(fig2, use_container_width=True)
st.info("💡 **이 그래프로 알 수 있는 것:** 개봉 첫 주 관객수가 많은 영화일수록 최종 총 관객수 역시 비례하여 높아지는 경향을 보입니다.")

st.divider()

st.subheader("📦 3. 장르별 총 관객수 분포 (박스 플롯)")

fig3 = px.box(
    df,
    x='primary_genre',
    y='total_audi',
    color='primary_genre',
    points="all",
    hover_name='movieNm',
    labels={
        'primary_genre': '장르',
        'total_audi': '총 관객수'
    },
    title="장르별 총 관객수 분포 및 이상치 확인"
)

fig3.update_layout(
    showlegend=False,
    margin=dict(t=50, b=20, l=20, r=20)
)
st.plotly_chart(fig3, use_container_width=True)
st.info("💡 **이 그래프로 알 수 있는 것:** 특정 장르 내에서 대흥행을 거둔 극소수의 흥행작(이상치)이 전체 관객수 평균을 견인하고 있음을 확인할 수 있습니다.")

st.divider()

with st.expander("🔍 원본 데이터 미리보기"):
    target_cols = ['movieCd', 'movieNm', 'openDt', 'primary_genre', 'nation', 'first_scrn', 'first_show', 'first_week_audi', 'total_audi', 'days_in_top10']
    available_cols = [col for col in target_cols if col in df.columns]
    st.dataframe(df[available_cols])
