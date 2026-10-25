from pathlib import Path
import os
import sys
import json
import shutil
import math
import hashlib
import base64
import numpy as np
import pytest
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from oish_data import FILES, DataError, data_location, load_catalog, check_public_approval

@pytest.fixture
def real_folder():
    value = os.environ.get('OISH_TEST_DATA_DIR')
    if not value: pytest.skip('실제 집계 경로 미지정: 실제 데이터 검증을 생략합니다.')
    return Path(value).resolve()

@pytest.fixture
def real(real_folder):
    return load_catalog(real_folder)

def test_default_package_has_no_actual_data():
    assert not list((ROOT/'data').glob('*.csv'))
    assert not (ROOT/'data'/'approval.json').exists()
    assert not (ROOT/'data'/'summary.json').exists()

def test_default_empty_app(monkeypatch):
    monkeypatch.delenv('OISH_MODE',raising=False)
    monkeypatch.delenv('OISH_DATA_DIR',raising=False)
    app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.exception
    assert app.info and not app.selectbox

def test_local_path_rules(monkeypatch,tmp_path):
    monkeypatch.setenv('OISH_MODE','local_review')
    monkeypatch.setenv('OISH_DATA_DIR','data')
    with pytest.raises(DataError): data_location(ROOT)
    root=tmp_path/'code'; root.mkdir()
    monkeypatch.setenv('OISH_DATA_DIR','../private')
    assert data_location(root)[0] == (tmp_path/'private').resolve()

def test_missing_approval(tmp_path):
    with pytest.raises(DataError): check_public_approval(tmp_path)

def test_missing_files(tmp_path):
    with pytest.raises(DataError): load_catalog(tmp_path)

def test_summary_and_all_top5_match_csv(real,real_folder):
    expected=json.loads((real_folder/'summary.json').read_text(encoding='utf-8-sig'))
    assert real.summary==expected
    original=pd.read_csv(real_folder/'collaboration_ranking.csv').fillna('')
    for brand in real.brands:
        wanted=original[(original.a==brand)|(original.b==brand)].sort_values(['score','rank'],ascending=[False,True]).head(5)
        got=real.partners(brand)
        assert [r['score'] for r in got]==wanted.score.tolist()
        assert [r['b'] for r in got]==[r.b if r.a==brand else r.a for r in wanted.itertuples()]

def test_all_pairs_reverse_orientation(real,real_folder):
    original=pd.read_csv(real_folder/'collaboration_ranking.csv').fillna('')
    for row in original.itertuples():
        normal=real.pair(row.a,row.b); reverse=real.pair(row.b,row.a)
        assert normal['score']==reverse['score']==row.score
        assert reverse['a_unique']==row.b_unique
        assert reverse['b_unique']==row.a_unique
        assert math.isclose(real.pair_similarity(row.a,row.b),row.similarity,abs_tol=1e-12)

def test_search_and_unknown(real):
    first=real.brands[0]
    assert first in real.search(first.split(' / ')[-1])
    assert not real.search('NO_SUCH_BRAND_000000')
    assert real.pair('NO_SUCH_BRAND_000000',first) is None
    assert real.pair_similarity('NO_SUCH_BRAND_000000',first) is None

def test_corrupt_csv_is_handled(real_folder,tmp_path):
    for name in FILES: shutil.copyfile(real_folder/name,tmp_path/name)
    q=pd.read_csv(tmp_path/'brand_quality.csv')
    q.loc[0,'raw_n']=-1
    q.to_csv(tmp_path/'brand_quality.csv',index=False)
    with pytest.raises(DataError): load_catalog(tmp_path)

def test_ui_interactions_and_charts(real,real_folder,monkeypatch):
    monkeypatch.setenv('OISH_MODE','local_review')
    monkeypatch.setenv('OISH_DATA_DIR',str(real_folder))
    app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.exception
    assert len(app.get('plotly_chart')) >= 1
    pair=real.ranking.iloc[0]
    app.selectbox(key='compare_a').set_value(pair.b)
    app.selectbox(key='compare_b').set_value(pair.a)
    app.run(timeout=30)
    assert not app.exception
    assert any(m.value==f'{pair.score:.2f} / 100' for m in app.metric)
    app.selectbox(key='compare_b').set_value(pair.b).run(timeout=30)
    assert any('서로 다른' in i.value for i in app.info)
    app.text_input(key='query').set_value('NO_SUCH_BRAND_000000').run(timeout=30)
    assert not app.exception and any('검색 결과가 없습니다' in i.value for i in app.info)
    app.text_input(key='query').set_value('').run(timeout=30)
    absent=next((b for b in real.brands if not real.partners(b)),None)
    if absent:
        app.selectbox(key='brand').set_value(absent).run(timeout=30)
        assert any('저장된 추천 결과가 없는' in i.value for i in app.info)
    assert not app.exception

def test_relative_loading_outside_working_directory(real_folder,tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('OISH_MODE','local_review')
    monkeypatch.setenv('OISH_DATA_DIR',str(real_folder))
    app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.exception

def test_public_approval_hash_gate(real_folder,tmp_path):
    # Temporary test record only. This is not an approval of the real dataset.
    for name in FILES: shutil.copyfile(real_folder/name,tmp_path/name)
    record={'public_release_approved':True,'reviewed_by':'TEST ONLY','approved_at':'TEST ONLY',
            'permission_reference':'TEST ONLY','allowed_scope':'TEST ONLY',
            'sha256':{name:hashlib.sha256((tmp_path/name).read_bytes()).hexdigest() for name in FILES}}
    (tmp_path/'approval.json').write_text(json.dumps(record),encoding='utf-8')
    assert load_catalog(tmp_path,public=True).brands
    with (tmp_path/'summary.json').open('a',encoding='utf-8') as f: f.write(' ')
    with pytest.raises(DataError): load_catalog(tmp_path,public=True)

def test_unranked_pair_and_profile_missing_ui(real,real_folder,monkeypatch):
    monkeypatch.setenv('OISH_MODE','local_review')
    monkeypatch.setenv('OISH_DATA_DIR',str(real_folder))
    app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    category=real.quality.category.iloc[0]
    names=real.quality[real.quality.category==category].index.tolist()
    a,b=names[:2]
    assert real.pair(a,b) is None
    app.selectbox(key='compare_a').set_value(a)
    app.selectbox(key='compare_b').set_value(b)
    app.run(timeout=30)
    assert not app.exception
    assert any('이 조합은 기존 추천표에 없습니다' in i.value for i in app.info)
    missing=next((k for k in real.brands if k not in real.profiles.index),None)
    if missing:
        app.selectbox(key='brand').set_value(missing).run(timeout=30)
        assert any('이미지 프로필이 없습니다' in i.value for i in app.info)
    app.text_input(key='query').set_value(a.split(' / ')[-1]).run(timeout=30)
    assert a in app.selectbox(key='brand').options

def test_chart_values_match_rates(real,real_folder,monkeypatch):
    monkeypatch.setenv('OISH_MODE','local_review')
    monkeypatch.setenv('OISH_DATA_DIR',str(real_folder))
    app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.exception
    charts=app.get('plotly_chart')
    assert len(charts)>=2
    for chart in charts:
        spec=json.loads(chart.proto.spec)
        for trace in spec['data']:
            key=trace['name']; images=trace['y']; values=trace['x']
            if isinstance(values,dict):
                values=np.frombuffer(base64.b64decode(values['bdata']),dtype=values['dtype'])
            np.testing.assert_allclose(values,real.profiles.loc[key,images].to_numpy()*100)
