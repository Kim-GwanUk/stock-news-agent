"""Isolate interpretation after relevance; keep full-pipeline audits separate."""
import asyncio,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import audit_locked_v16 as audit
async def supplied(stock,articles):
    for a in articles:a.update(relevant=True,analysis_candidate=True,relation='직접 관련')
    return articles,{},[]
audit.select=supplied
audit.CODE.append('app/earnings_basis.py')
asyncio.run(audit.main(sys.argv[1],sys.argv[2]))
