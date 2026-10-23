from app.news_display import presentation, exclusion, empty_reason


def test_processing_failure_is_not_uncertain_opinion():
    f = dict(direction='판단 보류', reason='보도된 사실: 최대 10억 원 예비 합의\n사업 영향 해석: 방향 불명확',
             counterpoint='승인 후 지급', processing_status='검증 실패')
    view = presentation({}, f)
    assert view['direction'] == '분석 미완료'
    assert '최대 10억 원 예비 합의' in view['content']
    assert view['conditions'] == '승인 후 지급'
    f['processing_status'] = '분석 완료'
    assert presentation({}, f)['direction'] == '판단 보류'


def test_old_record_does_not_claim_processing_success():
    view = presentation({}, dict(direction='판단 보류', reason='근거 부족'))
    assert view['status'] == '이전 분석 기록'
    assert not view['content']


def test_exclusions_and_empty_search_are_distinct():
    assert exclusion({'duplicate_of':'a'})[0] == '중복 보도'
    assert exclusion({'body_status':'본문 접근 실패'})[0] == '본문 확보 실패'
    assert exclusion({'body_status':'추출됨','relation':'확인 필요'})[0] == '선별 검증 미완료'
    assert '수집 요청에 실패' in empty_reason({'collection':{'status':'failed'},'articles':[]})
    assert '검색에서 반환된 기사가 없습니다' in empty_reason({'collection':{'status':'completed'},'articles':[]})
    assert '검색 결과는 있지만' in empty_reason({'articles':[{'id':'a'}]})
