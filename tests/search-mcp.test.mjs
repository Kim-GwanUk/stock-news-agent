import {test} from "node:test";
import assert from "node:assert/strict";
import {filterCompanies} from "../vendor/korea-stock-mcp/dist/dart/get-corp-code.js";
const companies = [
  {corp_name:"삼성",corp_eng_name:"Samsung",stock_code:""},
  {corp_name:"삼성전자",corp_eng_name:"Samsung Electronics",stock_code:"005930"},
  {corp_name:"삼성전기",corp_eng_name:"Samsung Electro",stock_code:"009150"},
  {corp_name:"SK하이닉스",corp_eng_name:"SK hynix",stock_code:"000660"},
];
test("unlisted exact match must not hide listed partial matches",()=>{
  assert.equal(filterCompanies(companies,{corp_name:"삼성"}).length,3);
});
test("spaces and code prefixes are supported",()=>{
  assert.equal(filterCompanies(companies,{corp_name:"SK 하이닉스"})[0].stock_code,"000660");
  assert.equal(filterCompanies(companies,{stock_code:"005"})[0].corp_name,"삼성전자");
});
