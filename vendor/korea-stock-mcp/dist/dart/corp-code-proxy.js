const PROXY_URL = "https://jjlabsio.github.io/korea-stock-mcp/corp-codes.json";
const FETCH_TIMEOUT_MS = 10_000;
export async function fetchCorpListFromProxy() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
        const response = await fetch(PROXY_URL, { signal: controller.signal });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        if (!Array.isArray(data) || data.length === 0 || !data[0].c) {
            throw new Error("Invalid proxy response shape");
        }
        return data.map((entry) => ({
            corp_code: entry.c,
            corp_name: entry.n,
            corp_eng_name: entry.e ?? "",
            stock_code: entry.s ?? "",
        }));
    }
    finally {
        clearTimeout(timeoutId);
    }
}
