"""Presentation only: never turn a processing failure into an investment opinion."""


def exclusion(article):
    if article.get('duplicate_of'):
        return '중복 보도', '동일 사건의 대표 기사를 표시합니다.'
    if article.get('analysis_candidate'):
        return '분석 대상', '대표 기사로 선별했습니다.'
    if article.get('relevant') is False:
        return '관련성 낮음', '검색 결과에서 대상 종목과의 관련성이 낮게 판정됐습니다.'
    body = article.get('body_status')
    if body != '추출됨':
        return ('본문 확보 실패', body) if body and body != '미확보' else ('본문 미확보', '본문을 확보하지 못했거나 이번 본문 조회 대상에 포함되지 않았습니다.')
    if article.get('relation') == '확인 필요':
        return '선별 검증 미완료', article.get('relation_reason', '본문 관련성 검증을 완료하지 못했습니다.')
    if article.get('relation') not in (None, '직접 관련'):
        return '직접 관련 아님', article.get('relation_reason', '대상 기업 자체의 사건인지 확인하지 못했습니다.')
    if article.get('market_roundup'):
        return '시황·동향', '기업 사업 영향 분석에서 제외된 시황 기사입니다.'
    if article.get('business_event') is False:
        return '구체적 사건 부족', '기업 자체의 구체적인 사업 사건을 확인하지 못했습니다.'
    if article.get('analysis_candidate') is False:
        return '분석 대상 밖', '최신 대표 기사 최대 5건을 분석하며, 이번 대상에 포함되지 않았습니다.'
    return '이전 기록', '이전 분석에는 상세 선별 상태가 저장되지 않았습니다.'


def presentation(article, finding):
    status = finding.get('processing_status')
    detail = finding.get('processing_detail', '')
    if not status:
        status, detail = ('이전 분석 기록', '세부 처리 상태를 기록하기 전 결과입니다. 다시 분석하면 현재 처리 상태를 확인할 수 있습니다.')
    reason = finding.get('reason', '')
    facts, separator, effect = reason.partition('\n사업 영향 해석: ')
    if not separator:
        facts = ''
        effect = reason
    else:
        facts = facts.removeprefix('보도된 사실: ')
    direction = finding.get('direction', '판단 보류')
    failed = status in ('사실 추출 실패', '분석 응답 실패', '검증 실패', '검증 미완료', '분석 제외')
    return dict(content=facts, effect=effect if not failed else '처리가 완료되지 않아 영향 방향을 제시하지 않습니다.',
                direction='분석 미완료' if failed else direction,
                status=status, detail=detail,
                conditions=finding.get('counterpoint', '') if facts else '')


def empty_reason(result):
    collection = result.get('collection', {})
    if collection.get('status') == 'failed':
        return '뉴스 수집 요청에 실패했습니다. 잠시 후 뉴스 분석을 다시 실행해 주세요.'
    if not result.get('articles'):
        return ('최근 7일 검색에서 반환된 기사가 없습니다.' if collection.get('status') == 'completed'
                else '저장된 기사 결과가 없습니다. 수집 경고를 확인하거나 다시 분석해 주세요.')
    return '검색 결과는 있지만 현재 표시 조건에 맞는 분석 기사가 없습니다. 아래 선별 내역 또는 추가 검색 결과를 확인해 주세요.'
