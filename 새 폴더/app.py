"""OISH v1 — portable, read-only Streamlit presentation of aggregate results."""
from pathlib import Path
from html import escape
import pandas as pd
import plotly.express as px
import streamlit as st
from oish_data import DataError, data_location, load_catalog

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='OISH | 뜻밖의 조합', page_icon='✳', layout='wide')
st.markdown((ROOT / 'assets' / 'style.css').read_text(encoding='utf-8'), unsafe_allow_html=True)
st.markdown('<div class="eyebrow">OISH / BRAND COLLABORATION LAB</div><h1>뜻밖의 조합<span class="accent">.</span></h1><p class="intro">소비자가 남긴 이미지에서, 다음 파트너의 가능성을 찾습니다.</p>', unsafe_allow_html=True)

def methodology():
    st.subheader('숫자가 말하는 것, 말하지 않는 것')
    st.markdown('''
**기존 분석 결과를 탐색하는 도구입니다.** 앱은 분석 스크립트를 실행하거나 새로운 추천 점수를 생성하지 않습니다.

1. 명시적 브랜드 평가를 보수적으로 분류하고, 평가 대상·부정 범위가 모호한 댓글을 보류했습니다. 자동 라벨의 수동 검증은 미완료입니다.
2. 이미지 언급률은 **영상별 주 분석 댓글을 분모로 계산한 뒤 영상을 동일 가중 평균**한 값입니다. 전체 소비자의 인식률이 아닙니다.
3. 이미지 비율에 IDF를 곱한 벡터의 코사인 유사도를 사용했습니다. 일반적인 이미지만으로 모든 브랜드가 비슷해지는 현상을 완화합니다.
4. 추천표는 같은 파일군, 식품–음료 쌍, 일부 업종 경계가 불명확한 유통 브랜드와 이미지 근거가 적은 쌍을 제외했습니다.

**점수 = 100 × (0.5 × 유사성 + 0.3 × 공통 이미지 질량 + 0.2 × 양측 차별 이미지 질량) × 표본 충분성 계수**

공통 이미지 질량은 정규화한 두 프로필의 최솟값 합계입니다. 차별성은 서로 공유하지 않는 이미지 질량의 기하평균입니다.
브랜드별 충분성은 `min(1, 댓글수/50) × min(1, 영상수/2) × min(1, 이미지댓글수/10)`이며, 두 브랜드 값의 기하평균을 사용합니다.
점수는 연구자가 정한 탐색 지표로 **성공 확률·구매의향·참신성·매출 효과를 뜻하지 않습니다.**

**해석의 한계**

- 영상은 대부분 1~2개입니다. 댓글 작성자를 독립 소비자 표본으로 간주하지 않았고, 모집단 유의성 검정은 수행하지 않았습니다.
- 파일군은 엄밀한 산업분류가 아닙니다. 예를 들어 음료 파일에는 식품·제과 브랜드도 포함됩니다.
- 채널·광고 여부·영상 관련성·수집 근거는 추가 확인이 필요합니다. 관측 기간 차이와 명시 브랜드 언급의 선택 편향이 있습니다.
- 관측되지 않은 이미지는 해당 브랜드에 없는 특성으로 단정할 수 없습니다. 정제와 가중치를 바꾸면 순위가 달라집니다.
- 원문과 개인 정보는 이 앱에서 읽거나 표시하지 않습니다. 집계 데이터도 별도의 이용·공개·제출 승인 대상입니다.
''')

try:
    folder, mode = data_location(ROOT)
    # Small local tables: validate on each rerun so approval changes take effect immediately.
    catalog = load_catalog(folder, public=(mode == 'public'))
except DataError as exc:
    st.info(str(exc))
    st.markdown('### 데이터 연결 대기 중\n배포용 코드에는 승인되지 않은 집계 자료가 포함되어 있지 않습니다. 로컬 시연은 README의 **내부 시연 모드**를 따라 연결해 주세요.')
    with st.expander('추천 방법론 미리 보기', expanded=True): methodology()
    st.stop()

if mode == 'local_review':
    st.warning('내부 시연 모드 · 데이터 이용·공개·제출 권한 미확인. 외부 접속이나 공개 배포에 사용하지 마세요.')
else:
    st.caption('연결된 집계 자료의 공개 승인 기록 및 파일 무결성을 확인했습니다. 승인 범위 내에서 사용하세요.')

s = catalog.summary
st.markdown('<div class="stats">'+''.join(f'<div class="stat"><span>{label}</span><strong>{s[key]:,}</strong><small>{note}</small></div>' for key,label,note in [('brands','수집 브랜드','원본 파일 기준'),('videos','고유 영상','중복 영상 ID 제외'),('raw_rows','수집 댓글 행','브랜드 간 중복 포함'),('valid_rows','주 분석 댓글','보수적 분류 규칙 통과')])+'</div>', unsafe_allow_html=True)
st.caption(f"고유 댓글 ID {s['unique_comment_ids']:,}개 · 이미지 프로필 {s['profile_brands']:,}개 브랜드 · 추천표 {s['ranked_pairs']:,}쌍. 수집 행 수와 고유 댓글 수는 다릅니다.")

with st.sidebar:
    st.markdown('## OISH\n브랜드에서 시작하기')
    category = st.selectbox('파일 기준 산업군', ['전체']+sorted(catalog.quality.category.unique()), key='category')
    query = st.text_input('브랜드 검색', placeholder='브랜드 이름을 입력하세요', key='query')
    options = catalog.search(query, category)
    st.caption(f'검색 결과 {len(options)}개')
    st.markdown('---\n소비자 표현 → 이미지 프로필 → 파트너 후보')
    st.caption('숭실대학교 경영 데이터 분석 공모전\n1차 프로토타입')

tabs = st.tabs(['파트너 찾기', '두 브랜드 비교', '이미지 프로필', '방법론'])
default = catalog.ranking.iloc[0].a if not catalog.ranking.empty else catalog.brands[0]

def profile_chart(keys):
    available = [k for k in keys if k in catalog.profiles.index]
    if not available:
        st.info('선택한 브랜드의 이미지 프로필이 없습니다. 정제 후 분석 근거가 부족할 수 있습니다.')
        return
    missing = [k for k in keys if k not in available]
    if missing: st.info('프로필 없음: '+', '.join(missing))
    values = catalog.profiles.loc[available]
    if not values.gt(0).any().any():
        st.info('프로필의 모든 이미지 언급률이 0입니다. 이미지 부재를 입증하는 결과는 아닙니다.')
        return
    long = values.rename_axis('브랜드').reset_index().melt('브랜드',var_name='이미지',value_name='언급률')
    long['언급률(%)'] = long['언급률']*100
    order = values.mean().sort_values().index.tolist()
    fig = px.bar(long,x='언급률(%)',y='이미지',color='브랜드',orientation='h',barmode='group',
                 category_orders={'이미지':list(reversed(order))}, color_discrete_sequence=['#6554d9','#17a398'])
    fig.update_layout(height=540,margin=dict(l=0,r=10,t=20,b=0),legend=dict(orientation='h',y=1.15,x=0),
                      font=dict(family='sans-serif'),plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(hovertemplate='%{y}<br>%{x:.2f}%<extra>%{fullData.name}</extra>')
    st.plotly_chart(fig, width='stretch', key='profile_chart_'+str(keys))
    st.caption('단위: % · 영상별 주 분석 댓글 중 이미지 언급 비율의 동일 가중 평균. 다중 이미지이므로 합계는 100%가 아닙니다.')

def evidence(key):
    row = catalog.quality.loc[key]
    st.caption(f"{key} · 주 분석 {int(row.valid_n):,}건 / {int(row.valid_videos)}영상 · 이미지 포착 댓글 {int(row.image_n):,}건")
    if row.valid_videos < 2 or row.valid_n < 50:
        st.caption('표본 제한: 주 분석 영상 2개 미만 또는 댓글 50개 미만. 탐색 결과로 해석하세요.')

def terms(label, value):
    st.markdown('**'+label+'**')
    st.write(value if str(value).strip() else '이번 표본·사전에서 별도 이미지가 관측되지 않았습니다.')

with tabs[0]:
    st.subheader('어떤 브랜드와 만나면 좋을까요?')
    st.caption('선택한 브랜드가 포함된 기존 추천표에서 점수순으로 최대 5개를 보여줍니다.')
    if not options:
        st.info('검색 결과가 없습니다. 검색어나 산업군 필터를 바꿔 주세요.')
        selected = None
    else:
        selected = st.selectbox('기준 브랜드', options,index=options.index(default) if default in options else 0,key='brand')
        evidence(selected)
        partners = catalog.partners(selected)
        if not partners: st.info('저장된 추천 결과가 없는 브랜드입니다. 표본 부족, 이미지 근거 부족 또는 추천 제외 기준 때문일 수 있습니다. 점수를 새로 만들지 않습니다.')
        for i, r in enumerate(partners,1):
            with st.container(border=True):
                st.markdown(f'<div class="partner"><div><span class="eyebrow">PARTNER {i:02d}</span><h3>{escape(r["b"])}</h3></div><div class="score">{r["score"]:.2f}<small>/ 100</small></div></div>',unsafe_allow_html=True)
                st.caption(f"전체 추천표 {int(r['rank'])}위 · 이미지 유사도 {r['similarity']:.3f} · 탐색 점수, 성공 확률 아님")
                terms('공통 이미지',r['common_images'])
                evidence(r['b'])

with tabs[1]:
    st.subheader('두 브랜드의 접점을 살펴보세요')
    cols=st.columns(2)
    a=cols[0].selectbox('브랜드 A',catalog.brands,index=catalog.brands.index(default),key='compare_a')
    initial_b = catalog.partners(default)[0]['b'] if catalog.partners(default) else catalog.brands[-1]
    b=cols[1].selectbox('브랜드 B',catalog.brands,index=catalog.brands.index(initial_b),key='compare_b')
    if a==b:
        st.info('서로 다른 두 브랜드를 선택해 주세요.')
    else:
        pair=catalog.pair(a,b); similarity=catalog.pair_similarity(a,b)
        cols=st.columns(2)
        cols[0].metric('이미지 유사도', '계산 결과 없음' if similarity is None else f'{similarity:.3f}')
        cols[1].metric('기존 추천 점수', '추천표에 없음' if pair is None else f"{pair['score']:.2f} / 100")
        if pair is None:
            st.info('이 조합은 기존 추천표에 없습니다. 동일 파일군, 업종 경계, 표본·이미지 근거 등의 제외 기준이 적용됐을 수 있습니다. 유사도가 있어도 추천 점수로 바꾸지 않습니다.')
            if a in catalog.profiles.index and b in catalog.profiles.index:
                av,bv=catalog.profiles.loc[a],catalog.profiles.loc[b]
                terms('두 프로필에서 관측된 공통 이미지',', '.join(av.index[(av>0)&(bv>0)]))
                terms('A에서만 관측된 이미지',', '.join(av.index[(av>0)&(bv==0)]))
                terms('B에서만 관측된 이미지',', '.join(av.index[(bv>0)&(av==0)]))
        else:
            terms('공통 이미지 · 기존 추천표의 주요 표현',pair['common_images'])
            cols=st.columns(2)
            with cols[0]: terms('A의 차별 이미지',pair['a_unique'])
            with cols[1]: terms('B의 차별 이미지',pair['b_unique'])
            with st.expander('점수 구성 확인'):
                st.dataframe(pd.DataFrame({'요소':['유사성','공통 이미지 질량','양측 차별 이미지 질량','표본 충분성 계수'],'기존 계산값':[pair[x] for x in ['similarity','shared_mass','distinct_mass','support_factor']]}),hide_index=True)
        evidence(a); evidence(b); profile_chart([a,b])

with tabs[2]:
    st.subheader('브랜드 이미지 프로필')
    if selected is None: st.info('왼쪽 필터를 조정하고 기준 브랜드를 선택해 주세요.')
    else:
        st.markdown('### '+selected); evidence(selected); profile_chart([selected])
        with st.expander('원본 집계 비율 보기'):
            if selected in catalog.profiles.index:
                st.dataframe(catalog.profiles.loc[selected].rename('비율(0~1)').to_frame())

with tabs[3]: methodology()
st.markdown('---')
st.caption('OISH | 뜻밖의 조합 · 근거를 살펴보고, 가능성을 검증하세요.')
