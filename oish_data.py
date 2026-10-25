"""Read precomputed aggregates only. No comment ingestion or model execution."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import numpy as np
import pandas as pd

FILES = ('summary.json', 'brand_quality.csv', 'brand_image_rates.csv',
         'brand_similarity.csv', 'collaboration_ranking.csv')

class DataError(ValueError):
    """A safe, user-facing dataset validation error."""

def data_location(root: Path):
    mode = os.environ.get('OISH_MODE', 'public').strip()
    if mode not in ('public', 'local_review'):
        raise DataError('OISH_MODE는 public 또는 local_review여야 합니다.')
    if mode == 'public':
        return (root / 'data').resolve(), mode
    setting = os.environ.get('OISH_DATA_DIR', '').strip()
    if not setting:
        raise DataError('내부 시연용 집계 폴더를 OISH_DATA_DIR로 연결해 주세요.')
    path = Path(setting).expanduser()
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if path == root.resolve() or root.resolve() in path.parents:
        raise DataError('내부 집계 자료는 prototype_v1 폴더 밖에 보관해 주세요.')
    return path, mode

def check_public_approval(folder: Path):
    try:
        manifest = json.loads((folder / 'approval.json').read_text(encoding='utf-8'))
        if manifest.get('public_release_approved') is not True:
            raise DataError('공개 승인된 집계 데이터가 아직 연결되지 않았습니다.')
        for field in ('reviewed_by', 'approved_at', 'permission_reference', 'allowed_scope'):
            if not str(manifest.get(field, '')).strip():
                raise DataError('공개 승인 기록이 완성되지 않았습니다.')
        for name in FILES:
            digest = hashlib.sha256((folder / name).read_bytes()).hexdigest()
            if manifest.get('sha256', {}).get(name) != digest:
                raise DataError('승인된 파일과 현재 파일이 다릅니다. 승인 범위를 다시 확인해 주세요.')
    except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
        raise DataError('공개 승인 기록 또는 승인된 집계 파일을 확인해 주세요.') from exc

@dataclass
class Catalog:
    summary: dict
    quality: pd.DataFrame
    profiles: pd.DataFrame
    similarity: pd.DataFrame
    ranking: pd.DataFrame

    @property
    def brands(self):
        return sorted(self.quality.index.tolist())

    def search(self, query='', category='전체'):
        q = self.quality
        if category != '전체': q = q[q.category == category]
        term = query.strip().casefold()
        return sorted(k for k in q.index if term in k.casefold())

    def partners(self, brand, limit=5):
        rows = self.ranking[(self.ranking.a == brand) | (self.ranking.b == brand)]
        return [self.orient(row, brand) for _, row in rows.sort_values(['score', 'rank'], ascending=[False, True]).head(limit).iterrows()]

    @staticmethod
    def orient(row, brand):
        result = row.to_dict()
        if row.b == brand:
            result.update(a=row.b, b=row.a, a_unique=row.b_unique, b_unique=row.a_unique)
        return result

    def pair(self, a, b):
        match = self.ranking[((self.ranking.a == a) & (self.ranking.b == b)) |
                             ((self.ranking.a == b) & (self.ranking.b == a))]
        return None if match.empty else self.orient(match.iloc[0], a)

    def pair_similarity(self, a, b):
        if a not in self.similarity.index or b not in self.similarity.columns: return None
        value = self.similarity.loc[a, b]
        return float(value) if pd.notna(value) else None

def load_catalog(folder: Path, public=False):
    if public: check_public_approval(folder)
    try:
        summary = json.loads((folder / FILES[0]).read_text(encoding='utf-8-sig'))
        quality = pd.read_csv(folder / FILES[1], encoding='utf-8-sig')
        profiles = pd.read_csv(folder / FILES[2], encoding='utf-8-sig', index_col=0)
        similarity = pd.read_csv(folder / FILES[3], encoding='utf-8-sig', index_col=0)
        ranking = pd.read_csv(folder / FILES[4], encoding='utf-8-sig').fillna('')
        required_q = {'key', 'category', 'brand', 'raw_n', 'raw_videos', 'valid_n', 'valid_videos', 'image_n'}
        required_r = {'rank', 'a', 'b', 'score', 'similarity', 'shared_mass', 'distinct_mass', 'support_factor', 'common_images', 'a_unique', 'b_unique'}
        if not required_q <= set(quality.columns) or not required_r <= set(ranking.columns):
            raise DataError('집계 CSV의 필수 열이 누락됐습니다.')
        forbidden = {'text', 'clean_text', 'target_scope', 'author', 'comment_id', 'video_id', 'parent_id', 'email', 'phone'}
        if any(forbidden & set(t.columns) for t in (quality, profiles, similarity, ranking)):
            raise DataError('댓글 또는 식별자 열이 포함된 파일은 이 앱에서 사용할 수 없습니다.')
        quality = quality.set_index('key')
        if any(t.index.has_duplicates for t in (quality, profiles, similarity)):
            raise DataError('브랜드 키가 중복되어 있습니다.')
        if not set(profiles.index) <= set(quality.index): raise DataError('브랜드 프로필의 키가 일치하지 않습니다.')
        if set(similarity.index) != set(profiles.index) or set(similarity.columns) != set(profiles.index):
            raise DataError('유사도 행렬과 이미지 프로필의 브랜드가 일치하지 않습니다.')
        profiles = profiles.apply(pd.to_numeric, errors='raise')
        if profiles.empty or profiles.isna().any().any() or not ((profiles >= 0) & (profiles <= 1)).all().all():
            raise DataError('이미지 비율은 결측 없는 0~1 값이어야 합니다.')
        similarity = similarity.apply(pd.to_numeric, errors='raise').loc[profiles.index, profiles.index]
        mat = similarity.to_numpy()
        if not np.allclose(mat, mat.T, equal_nan=True) or np.isinf(mat).any():
            raise DataError('유사도 행렬의 대칭 또는 숫자 형식이 맞지 않습니다.')
        finite = mat[np.isfinite(mat)]
        if (finite < -1e-10).any() or (finite > 1 + 1e-10).any(): raise DataError('유사도 값의 범위를 확인해 주세요.')
        for c in ['raw_n','raw_videos','valid_n','valid_videos','image_n']:
            quality[c] = pd.to_numeric(quality[c], errors='raise')
            if quality[c].isna().any() or (quality[c] < 0).any() or (quality[c] % 1 != 0).any():
                raise DataError('댓글·영상 수는 0 이상의 정수여야 합니다.')
        if (quality.valid_n > quality.raw_n).any() or (quality.image_n > quality.valid_n).any():
            raise DataError('분석 댓글 수와 원시 댓글 수의 관계를 확인해 주세요.')
        for c in ['score','similarity','shared_mass','distinct_mass','support_factor','rank']:
            ranking[c] = pd.to_numeric(ranking[c], errors='raise')
        if not ranking.score.between(0,100).all() or not ranking[['similarity','shared_mass','distinct_mass','support_factor']].apply(lambda x:x.between(0,1+1e-10)).all().all():
            raise DataError('추천 지표의 숫자 범위를 확인해 주세요.')
        known = set(quality.index)
        if not set(ranking.a) | set(ranking.b) <= known: raise DataError('추천표에 없는 브랜드가 연결돼 있습니다.')
        pairs = [tuple(sorted((a,b))) for a,b in zip(ranking.a,ranking.b)]
        if len(set(pairs)) != len(pairs) or (ranking.a == ranking.b).any(): raise DataError('추천 쌍이 중복됐습니다.')
        if ranking['rank'].duplicated().any() or not ranking['rank'].gt(0).all(): raise DataError('전체 추천 순위가 올바르지 않습니다.')
        for field in ['brands','raw_rows','videos','valid_rows','unique_comment_ids','ranked_pairs','profile_brands']:
            if type(summary.get(field)) is not int or summary[field] < 0: raise DataError('요약 지표의 형식이 올바르지 않습니다.')
        if summary['brands'] != len(quality) or summary['raw_rows'] != int(quality.raw_n.sum()) or summary['valid_rows'] != int(quality.valid_n.sum()) or summary['ranked_pairs'] != len(ranking) or summary['profile_brands'] != len(profiles):
            raise DataError('요약 지표와 CSV 합계가 일치하지 않습니다.')
        return Catalog(summary, quality, profiles, similarity, ranking)
    except DataError: raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise DataError('집계 파일을 읽지 못했습니다. README의 파일 목록과 데이터 형식을 확인해 주세요.') from exc
