import pytest
from app import fact_ledger as ledger

STOCK={'code':'051910','name':'LG화학'}
def article(body, refs):
    a={'id':'ownership','body':body,'title':'기업 소식'}
    a['fact_ledger']=ledger.materialize(a,refs,STOCK)
    return a
def ref(i,subject,event,kind,role='main',anchor=None):
    return dict(paragraph_index=i,role=role,subject=subject,
                subject_paragraph_index=i if anchor is None else anchor,event_quote=event,event_kind=kind)
def choice(effect,ids=['p0']):return dict(fact_ids=ids,effect=effect,impact='중간')

def test_other_company_profit_cannot_support_target_even_with_exact_quote():
    other='OCI는 영업이익이 433억원으로 늘었다.'
    target='LG화학과 OCI는 담합 혐의로 기소됐다.'
    a=article(other+'\n'+target,[ref(0,'OCI',other,'earnings'),ref(1,'LG화학',target,'cost_risk')])
    assert a['fact_ledger']['facts'][0]['role']=='context'
    with pytest.raises(ValueError): ledger.render(a,choice('earnings_up'))
    f=ledger.render(a,choice('cost_risk',['p1']))
    assert f['direction']=='하락 요인'
    assert other not in f['reason']+f['counterpoint']
    assert all(e['quote']!=other for e in f['evidence'])

def test_invented_target_owner_or_cross_paragraph_event_is_rejected():
    with pytest.raises(ValueError):
        article('OCI는 올해 영업이익이 증가했다.',[ref(0,'LG화학','OCI는 올해 영업이익이 증가했다.','earnings')])

def test_subject_mention_elsewhere_does_not_license_foreign_event():
    own='LG화학은 담합 혐의로 기소됐다.'
    foreign='OCI는 영업이익이 늘었다.'
    a=article(own+'\n'+foreign,[ref(0,'LG화학',own,'cost_risk'),ref(1,'LG화학',foreign,'earnings',anchor=0)])
    with pytest.raises(ValueError): ledger.render(a,choice('earnings_up',['p1']))

def test_short_body_pronoun_can_resolve_to_target_with_prior_evidence():
    own='LG화학은 신규 사업 계획을 밝혔다.'
    p='회사는 정부로부터 최대 500억원 보조금을 받을 예정이다.'
    a=article(own+'\n'+p,[ref(0,'LG화학',own,'development'),ref(1,'LG화학',p,'funding',anchor=0)])
    assert ledger.render(a,choice('funding',['p1']))['direction']=='상승 요인'

def test_buyback_has_return_explanation_and_preserves_conditional_limit():
    p='LG화학은 이사회 승인 후 최대 500억원의 자사주 매입을 추진할 계획이다.'
    a=article(p,[ref(0,'LG화학',p,'shareholder_return')])
    f=ledger.render(a,choice('shareholder_return'))
    assert p in f['reason'] and '주주가치' in f['reason']
    assert '투자 재원 확보' not in f['reason']
    with pytest.raises(ValueError): ledger.render(a,choice('funding'))

def test_wrong_extraction_kind_cannot_turn_buyback_into_funding():
    p='LG화학은 500억원 자사주 매입을 결정했다.'
    a=article(p,[ref(0,'LG화학',p,'funding')])
    with pytest.raises(ValueError): ledger.render(a,choice('funding'))

def test_distinct_funding_and_return_events_remain_distinct():
    p='LG화학은 정부와 최대 100억원 보조금 예비 약정을 체결했다.'
    q='LG화학은 50억원 자사주 매입도 추진한다.'
    a=article(p+'\n'+q,[ref(0,'LG화학',p,'funding'),ref(1,'LG화학',q,'shareholder_return')])
    assert ledger.render(a,choice('funding'))['direction']=='상승 요인'
    assert ledger.render(a,choice('shareholder_return',['p1']))['direction']=='상승 요인'

def test_cancelled_buyback_cannot_be_positive_return():
    p='LG화학은 자사주 매입 계획을 취소했다.'
    a=article(p,[ref(0,'LG화학',p,'shareholder_return')])
    with pytest.raises(ValueError): ledger.render(a,choice('shareholder_return'))

def test_split_company_needs_source_link_not_just_similar_name():
    stock={'code':'035720','name':'카카오'}
    p='카카오X는 분할 이후 3000억원 자사주 매입을 추진한다.'
    a={'id':'split','body':p}
    refs=[ref(0,'카카오X',p,'shareholder_return')]
    with pytest.raises(ValueError):ledger.materialize(a,refs,stock)
    a['body']='카카오는 분할 이후 카카오X의 사업 전략을 공개한다.\n'+p
    refs=[ref(1,'카카오X',p,'shareholder_return')]
    a['fact_ledger']=ledger.materialize(a,refs,stock)
    assert a['fact_ledger']['facts'][0]['target_connection_index']==0
    assert ledger.render(a,choice('shareholder_return',['p1']))['direction']=='상승 요인'

def test_target_risk_promoted_when_other_company_was_marked_main():
    p='OCI는 영업이익이 433억원으로 증가했다.'
    q='LG화학은 공정거래법 위반 혐의로 기소됐다.'
    a=article(p+'\n'+q,[ref(0,'OCI',p,'earnings'),ref(1,'LG화학',q,'cost_risk','context')])
    assert a['fact_ledger']['facts'][1]['role']=='main'
    assert ledger.render(a,choice('cost_risk',['p1']))['direction']=='하락 요인'


def test_financial_alias_preserves_amount_and_schedule_without_bank_conflation():
    p='신한금융지주는 7000억원 자기주식 매입을 마쳤고 11월 4일 소각할 예정이다.'
    a={'id':'alias','title':'소각','body':p}
    a['fact_ledger']=ledger.materialize(a,[ref(0,'신한금융지주',p,'shareholder_return')],{'code':'055550','name':'신한지주'})
    f=ledger.render(a,choice('shareholder_return'))
    assert p in f['reason']
    assert '신한은행' not in ledger.target_names({'code':'055550','name':'신한지주'})

@pytest.mark.parametrize('p,expected',[
 ('LG화학은 500억원을 투자하기로 약정했다.','판단 보류'),
 ('LG화학은 신규 공장 가동을 시작했다.','상승 요인'),
 ('LG화학은 신규 공장 가동을 시작했으나 수익성 우려가 제기됐다.','판단 보류')])
def test_investment_needs_operational_progress_without_dispute(p,expected):
    a=article(p,[ref(0,'LG화학',p,'development')])
    assert ledger.render(a,choice('development'))['direction']==expected


def test_relevance_rescue_uses_target_local_event_only():
    from app.news_selection import explicit_target_event
    st={'code':'071050','name':'한국금융지주'}
    assert explicit_target_event(st,['한국금융지주의 순이익이 4321억원으로 전망됐다.'])==0
    assert explicit_target_event(st,['한국금융지주는 비교 대상이다. 삼성증권 순이익 4321억원.']) is None
    assert explicit_target_event({'code':'055550','name':'신한지주'},['▶신한지주, (정정)주식소각결정(사유: 자기주식 취득 완료)'])==0


def test_capacity_is_not_realized_sales():
    p='LG화학은 연간 100만톤을 생산할 수 있는 체제를 갖췄다.'
    a=article(p,[ref(0,'LG화학',p,'sales')])
    assert ledger.render(a,choice('sales_opportunity'))['direction']=='판단 보류'

def test_soil_legal_brand_alias_does_not_include_group():
    assert '에쓰오일' in ledger.target_names({'code':'010950','name':'S-Oil'})
    assert '현대차그룹' not in ledger.target_names({'code':'005380','name':'현대차'})


def test_posco_holdings_does_not_alias_steel_subsidiary():
    names=ledger.target_names({'code':'005490','name':'POSCO홀딩스'})
    assert '포스코홀딩스' in names and '포스코' not in names


def test_group_metrics_link_with_scope_but_affiliate_profit_does_not():
    st={'code':'086790','name':'하나금융지주'}
    p='하나금융그룹의 올해 3분기 순익은 1조2262억원으로 8.3% 증가할 전망이다.'
    a={'id':'group','title':'실적','body':p}
    a['fact_ledger']=ledger.materialize(a,[ref(0,'하나금융그룹',p,'earnings')],st)
    assert '그룹 전체 지표' in ledger.render(a,choice('earnings_up'))['counterpoint']
    assert not ledger.group_scope(st,'하나금융그룹','하나금융그룹의 비은행 부문 순익은 증가했다.')
    assert not ledger.group_scope(st,'하나은행','하나은행의 순익은 증가했다.')


def test_omitted_risk_is_retained_and_forecast_cannot_override_it():
    p='LG화학의 내년 영업이익은 3조원으로 증가할 전망이다.'
    risk='다만 공급과잉과 수익성 악화 우려가 남아 있다.'
    a=article(p+'\n'+risk,[ref(0,'LG화학',p,'earnings')])
    f=ledger.render(a,choice('earnings_up'))
    assert f['direction']=='판단 보류' and risk in f['counterpoint']


def test_forecast_level_without_growth_comparison_is_not_improvement():
    p='LG화학의 내년 영업이익은 3조원으로 전망된다.'
    a=article(p,[ref(0,'LG화학',p,'earnings')])
    assert ledger.render(a,choice('earnings_up'))['direction']=='판단 보류'


def test_actual_earnings_growth_is_not_erased_by_future_risk():
    p='LG화학은 올해 영업이익이 전년보다 20% 증가했다고 발표했다.'
    a=article(p+'\n내년 공급과잉은 위험이다.',[ref(0,'LG화학',p,'earnings')])
    assert ledger.render(a,choice('earnings_up'))['direction']=='상승 요인'


def test_exact_quote_unique_location_repairs_wrong_index_without_rewriting():
    p='포스코홀딩스가 호주 사업을 추진한다.'
    a={'id':'posco','title':'사업','body':p+'\n사업은 2031년 가동 목표다.'}
    r=ref(1,'포스코홀딩스',p,'development',anchor=0)
    a['fact_ledger']=ledger.materialize(a,[r],{'code':'005490','name':'POSCO홀딩스'})
    assert a['fact_ledger']['facts'][0]['paragraph_index']==0
    ledger.verify(a,a['fact_ledger'])
