import z from "zod";
import { krxRequest } from "../utils/request.js";
import { buildUrl } from "../utils/url.js";
import { koreaMarket } from "../utils/const.js";
const krxBaseInfoUrl = {
    KOSPI: "https://data-dbg.krx.co.kr/svc/apis/sto/stk_isu_base_info",
    KOSDAQ: "https://data-dbg.krx.co.kr/svc/apis/sto/ksq_isu_base_info",
    KONEX: "https://data-dbg.krx.co.kr/svc/apis/sto/knx_isu_base_info",
};
export const getBaseInfoSchema = z.object({
    basDdList: z
        .array(z.string().length(8))
        .nonempty()
        .describe("기준일자(YYYYMMDD) 배열"),
    market: z.enum(koreaMarket).describe("상장된 주식시장 종류"),
    codeList: z
        .array(z.string())
        .nonempty()
        .describe("데이터를 가져올 종목들의 종목코드의 배열"),
});
async function getSingleBaseInfo(url, basDd, codeList) {
    const response = await krxRequest(buildUrl(url, { basDd }));
    const data = await response.json();
    if (!data.OutBlock_1) {
        throw new Error(`KRX API 오류: 종목 기본정보를 조회할 수 없습니다 (기준일: ${basDd})`);
    }
    // Local extension: ["*"] loads the official current symbol catalog for search.
    const filtered = codeList.includes("*") ? data.OutBlock_1 :
        data.OutBlock_1.filter((stock) => codeList.includes(stock.ISU_SRT_CD));
    return { basDd, filtered };
}
export async function getBaseInfo(params) {
    const { basDdList, market, codeList } = params;
    const url = krxBaseInfoUrl[market];
    const response = {};
    const resultPromises = basDdList.map((basDd) => getSingleBaseInfo(url, basDd, codeList));
    const results = await Promise.all(resultPromises);
    results.forEach(({ basDd, filtered }) => {
        response[basDd] = filtered;
    });
    return response;
}
