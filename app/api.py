import asyncio
import time
import base64
import uuid
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Query
from app import db, graph, providers, dart_rag
from app.config import MODEL, provider_status
from app.models import Stock, RegisterStock, AnalyzeRequest

app = FastAPI(title="천기누설", version="0.1.0")
analysis_lock = asyncio.Lock()


class NewsMemorySearch(BaseModel):
    query: str = Field(min_length=1,max_length=1500)
    as_of: str | None = None
    limit: int = Field(default=5,ge=1,le=20)


@app.get('/stocks/{code}/news-memory')
def list_news_memory(code: str):
    from app import news_memory
    try:
        return {'items':news_memory.records(code)}
    except ValueError:
        raise HTTPException(400,'6자리 종목코드를 입력해 주세요.') from None


@app.post('/stocks/{code}/news-memory/search')
async def search_news_memory(code: str, request: NewsMemorySearch):
    from app import news_memory
    try:
        return {'items':await news_memory.search(code,request.query,request.as_of,request.limit)}
    except ValueError:
        raise HTTPException(400,'종목코드 또는 시간대가 포함된 기준 시각을 확인해 주세요.') from None
    except Exception:
        raise HTTPException(503,'저장된 근거 검색을 완료하지 못했습니다. 다시 시도해 주세요.') from None


@app.post('/stocks/{code}/news-memory/sync')
async def sync_news_memory(code: str):
    from app import news_memory
    try:
        async with analysis_lock:
            return await news_memory.sync(code)
    except ValueError:
        raise HTTPException(400,'종목코드를 확인해 주세요.') from None
    except Exception:
        raise HTTPException(503,'근거는 보관되어 있지만 검색 색인을 갱신하지 못했습니다.') from None

class CsvPreview(BaseModel):
    content: str = Field(max_length=1_400_000)

class CsvCommit(BaseModel):
    token: str = Field(pattern=r'^[0-9a-f]{32}$')
    rows: list[int] = Field(min_length=1,max_length=500)

class PhotoPreview(BaseModel):
    content: str = Field(max_length=6_700_000)

@app.post('/stocks/import/photo')
async def preview_photo(request: PhotoPreview):
    from app.photo_import import extract,inspect_photo
    try:
        raw=base64.b64decode(request.content,validate=True)
        catalog=await asyncio.wait_for(providers.stock_catalog(),60)
        extracted=await asyncio.wait_for(extract(raw),70)
        rows=inspect_photo(extracted,catalog,db.stocks())
    except ValueError as exc: raise HTTPException(400,str(exc)) from None
    except Exception:
        raise HTTPException(502,'사진 추출 또는 상장 목록 조회를 완료하지 못했습니다. 등록된 종목은 없습니다. 다시 시도해 주세요.') from None
    token=uuid.uuid4().hex
    # Keep only identifiers and validation outcomes, never the uploaded photograph.
    db.cache_put('csv-preview:'+token,rows,1800)
    return {'token':token,'rows':rows}

@app.post('/stocks/import/preview')
async def preview_csv(request: CsvPreview):
    from app.stock_import import inspect_csv
    try:
        raw=base64.b64decode(request.content,validate=True)
        catalog=await asyncio.wait_for(providers.stock_catalog(),60)
        rows=inspect_csv(raw,catalog,db.stocks())
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from None
    except Exception:
        raise HTTPException(502,'상장 종목 목록을 확인하지 못했습니다. 비상장으로 판정하지 않았습니다. 다시 시도해 주세요.') from None
    token=uuid.uuid4().hex
    db.cache_put('csv-preview:'+token,rows,1800)
    return {'token':token,'rows':rows}

@app.post('/stocks/import/commit')
async def commit_csv(request: CsvCommit):
    rows=db.cached('csv-preview:'+request.token)
    if rows is None: raise HTTPException(400,'미리보기가 만료되었습니다. 다시 검사해 주세요.')
    allowed={r['row']:r for r in rows if r['valid']}
    if any(i not in allowed for i in request.rows):
        raise HTTPException(400,'등록 가능한 행만 선택해 주세요.')
    try:
        catalog={s['code']:s for s in await asyncio.wait_for(providers.stock_catalog(),60)}
        selected=[]
        for i in dict.fromkeys(request.rows):
            row=allowed[i]; current=catalog.get(row['code'])
            if not current or current['market'] not in ('KOSPI','KOSDAQ') or current['name']!=row['name']:
                raise ValueError('상장 정보가 달라졌습니다. CSV를 다시 검사해 주세요.')
            selected.append({**current,'kind':row['kind']})
        saved=db.import_stocks(selected)
        return {'added':saved,'skipped':len(selected)-len(saved)}
    except ValueError as exc: raise HTTPException(400,str(exc)) from None
    except Exception: raise HTTPException(502,'등록 전 상장 정보를 재확인하지 못했습니다. 다시 시도해 주세요.') from None

@app.get("/health")
def health():
    return {"status": "ok", "providers": provider_status(), "model": MODEL}

@app.get("/stocks")
def list_stocks():
    return db.stocks()

@app.post("/rag/sync/{code}")
async def sync_dart(code: str):
    stock = next((s for s in db.stocks() if s["code"] == code), None)
    if not stock:
        raise HTTPException(404, "등록한 종목을 선택해 주세요.")
    try:
        return await dart_rag.sync(stock)
    except Exception:
        raise HTTPException(502, "DART 자료 저장에 실패했습니다. 연결 상태를 확인해 주세요.") from None

@app.get("/rag/search/{code}")
async def search_dart(code: str, q: str = Query(min_length=2, max_length=500)):
    stock = next((s for s in db.stocks() if s["code"] == code), None)
    if not stock:
        raise HTTPException(404, "등록한 종목을 선택해 주세요.")
    try:
        return {"items":await dart_rag.search(stock,q),
                "corpus":db.cached("dart-rag-status:"+code)}
    except Exception:
        raise HTTPException(502, "공시 근거 검색에 실패했습니다.") from None

@app.get("/stocks/catalog")
async def stock_catalog():
    try:
        items = await asyncio.wait_for(providers.stock_catalog(), 60)
        return {"items": sorted(items, key=lambda s: s["name"])}
    except Exception:
        raise HTTPException(502, "종목 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.") from None

@app.post("/stocks")
async def register(request: RegisterStock):
    try:
        listing = await asyncio.wait_for(providers.resolve_listing(request.code), 45)
        stock = Stock(**listing, kind=request.kind)
        # Validate code and actual market against KRX before accepting a watchlist entry.
        verified = await asyncio.wait_for(providers.price(stock.model_dump()), 45)
        stock.name = verified["name"]
        db.add_stock(stock)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except Exception:
        raise HTTPException(422, "종목 코드·시장을 확인하지 못했습니다. 입력값과 연결 상태를 확인해 주세요.") from None
    return stock

@app.get("/stocks/search")
async def search_stocks(q: str = Query(min_length=2, max_length=60)):
    if len(q.strip()) < 2:
        raise HTTPException(422, "검색어를 두 글자 이상 입력해 주세요.")
    try:
        return await asyncio.wait_for(providers.search_stocks(q), 30)
    except Exception:
        raise HTTPException(502, "종목 검색에 실패했습니다. 잠시 후 다시 시도해 주세요.") from None

@app.delete("/stocks/{code}")
def remove_stock(code: str):
    db.delete_stock(code)
    return {"deleted": code}

@app.get("/analyses/{code}")
def list_analyses(code: str):
    return db.history(code)

@app.get("/stocks/{code}/history")
async def price_history(code: str, days: int = Query(default=30, ge=7, le=90)):
    stock = next((s for s in db.stocks() if s["code"] == code), None)
    if stock is None:
        raise HTTPException(404, "등록한 종목을 선택해 주세요.")
    try:
        return await asyncio.wait_for(providers.price_history(stock, days), 90)
    except Exception:
        raise HTTPException(502, "주가 흐름을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.") from None

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    stock = next((s for s in db.stocks() if s["code"] == request.code), None)
    if stock is None:
        raise HTTPException(404, "종목을 먼저 등록해 주세요.")
    async with analysis_lock:
        history = db.history(request.code, 1)
        if (history and history[0].get("pipeline_version") == 22
                and not history[0].get('news_window')
                and history[0].get("prompt_version") == graph.analysis.PROMPT_VERSION and not request.refresh):
            from datetime import datetime
            age = time.time() - datetime.fromisoformat(history[0]["as_of"]).timestamp()
            if age < 600:
                return {**history[0], "cached": True}
        try:
            return await graph.run(stock)
        except TimeoutError:
            raise HTTPException(504, "분석·근거 저장 제한 시간을 초과했습니다. 저장된 결과를 확인해 주세요.") from None
        except Exception:
            raise HTTPException(502, "분석 실행에 실패했습니다. 연결 상태를 확인해 주세요.") from None

@app.get('/reports/morning/{code}')
def previous_morning(code: str):
    if not any(s['code']==code for s in db.stocks()):
        raise HTTPException(404,'등록한 종목을 선택해 주세요.')
    return db.cached('morning-report-v1:'+code)

@app.post('/reports/morning/{code}')
async def create_morning(code: str):
    from app import morning_report
    stock=next((s for s in db.stocks() if s['code']==code),None)
    if not stock:
        raise HTTPException(404,'등록한 종목을 선택해 주세요.')
    async with analysis_lock:
        try:
            return await asyncio.wait_for(morning_report.create(stock),300)
        except Exception:
            raise HTTPException(502,'보고서를 생성하지 못했습니다. 기존 보고서는 유지됩니다.') from None
