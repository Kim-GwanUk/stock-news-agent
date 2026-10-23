import base64
import hashlib
import httpx
import pandas as pd
import streamlit as st

@st.dialog('사진으로 종목 등록',width='large')
def show(base):
    from frontend.stock_import import request
    st.caption('사진 선택 → 종목 추출·검사 → 직접 확인·선택 → 등록')
    st.info('종목명·코드만 보이도록 잘라서 올려 주세요. 추출 버튼을 누르면 사진이 OpenAI API로 전송됩니다. 앱 서버에는 사진 원본을 저장하지 않습니다.')
    uploaded=st.file_uploader('종목 목록 사진',type=['png','jpg','jpeg','webp'],key='stock_photo_file',max_upload_size=5)
    st.caption('PNG·JPG·WEBP · 최대 5MB / 2천만 화소 / 100종목 · 등록 구분은 관심으로 시작합니다.')
    if not uploaded: return
    raw=uploaded.getvalue(); digest=hashlib.sha256(raw).hexdigest()
    if st.session_state.get('photo_digest')!=digest:
        st.session_state.pop('photo_preview',None)
        st.session_state['photo_digest']=digest
    if len(raw)>5_000_000:
        st.error('사진은 5MB 이하로 올려 주세요.'); return
    from app.photo_import import prepare_image
    try: preview_image=prepare_image(raw)
    except ValueError as exc:
        st.error(str(exc)); return
    st.image(preview_image,caption='원본과 인식 결과를 비교해 주세요.',alt='등록 전 비교할 종목 목록 사진',width='stretch')
    if st.button('사진에서 종목 추출·검사',type='primary'):
        st.session_state.pop('photo_preview',None)
        with st.spinner('사진을 읽고 KRX 상장 목록과 비교합니다.'):
            try:
                with httpx.Client(timeout=150,trust_env=False) as client:
                    response=client.post(base+'/stocks/import/photo',json={'content':base64.b64encode(raw).decode()})
                if response.is_error:
                    message=response.json().get('detail')
                    st.error(message if isinstance(message,str) else '사진 형식을 확인해 주세요.')
                else: st.session_state['photo_preview']=response.json()
            except (httpx.HTTPError,ValueError): st.error('사진 추출 응답을 확인하지 못했습니다. 다시 시도해 주세요.')
    preview=st.session_state.get('photo_preview')
    if not preview: return
    rows=preview['rows']
    if not rows:
        st.warning('종목을 읽지 못했습니다. 종목명·코드가 선명한 사진을 100행 이하로 나누어 올려 주세요.'); return
    valid=[r for r in rows if r['valid']]
    st.markdown(f"**등록 가능 {len(valid)}개 · 확인 필요 또는 제외 {len(rows)-len(valid)}개**")
    data=[{'사진 행':i+1,'읽은 이름':r['read_name'],'읽은 코드':r['read_code'],
           '확인된 종목':r['name'] if r['market'] else '—','시장':r['market'],'검사 결과':r['status']} for i,r in enumerate(rows)]
    st.dataframe(pd.DataFrame(data),hide_index=True,width='stretch')
    st.caption('상장 목록과 일치해도 사진 인식 오류일 수 있습니다. 원본과 반드시 비교하세요. 불확실·불일치 항목은 제외하며, 종목 추가·검색에서 직접 찾아 등록할 수 있습니다.')
    dates=sorted({r['as_of'] for r in rows if r.get('as_of')})
    st.caption('KRX 목록 기준일 '+(', '.join(dates) or '확인된 종목 없음')+' · 미리보기 유효시간 30분')
    choices={r['row']:r for r in valid}
    picked=st.multiselect('사진과 비교해 등록할 종목 선택',list(choices),default=[],
        format_func=lambda i:f"{choices[i]['name']} · {choices[i]['code']} · {choices[i]['market']}",key='photo_selected_'+preview['token'])
    confirmed=st.checkbox('선택한 종목명과 코드를 사진과 비교했습니다.',key='photo_confirm_'+preview['token'])
    st.caption(f"선택 {len(picked)}개 · 등록 개수 제한 없음 · 기존 종목은 변경하지 않습니다.")
    if st.button('확인한 종목 등록',type='primary',disabled=not confirmed or not picked):
        result=request(base,'/stocks/import/commit',{'token':preview['token'],'rows':picked})
        if result is not None:
            st.session_state['csv_done']=f"사진에서 확인한 {len(result['added'])}개 종목을 등록했습니다. 이미 등록된 {result['skipped']}개는 건너뛰었습니다."
            st.session_state.pop('photo_preview',None)
            st.rerun()
