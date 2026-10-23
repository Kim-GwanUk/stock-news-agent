"""Versioned evaluation with the comparison-policy code included in the snapshot."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.audit_locked_v16 import main, CODE
CODE.append("app/earnings_basis.py")

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1],sys.argv[2]))
