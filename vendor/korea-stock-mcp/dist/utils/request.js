import { buildUrl } from "./url.js";
export function validateDartJsonResponse(data) {
    if (data.status && !["000", "013"].includes(data.status)) {
        throw new Error(`DART API 오류 (status: ${data.status}): ${data.message}`);
    }
}
export async function dartRequest(url) {
    if (!process.env.DART_API_KEY) {
        throw Error("There is no DART API KEY");
    }
    const response = await fetch(buildUrl(url, {
        crtfc_key: process.env.DART_API_KEY,
    }), {signal: AbortSignal.timeout(20000)});
    if (!response.ok) {
        throw Error(`DART API HTTP 오류 (status: ${response.status}): ${response.statusText}`);
    }
    return response;
}
export async function krxRequest(url) {
    if (!process.env.KRX_API_KEY) {
        throw Error("There is no KRX API KEY");
    }
    const response = await fetch(url, {
        signal: AbortSignal.timeout(20000),
        headers: {
            "Content-Type": "application/json",
            AUTH_KEY: process.env.KRX_API_KEY,
        },
    });
    if (!response.ok) {
        throw Error(`KRX API HTTP 오류 (status: ${response.status}): ${response.statusText}`);
    }
    return response;
}
