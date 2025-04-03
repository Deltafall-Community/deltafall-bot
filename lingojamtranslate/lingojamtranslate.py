import json
import re
from bs4 import BeautifulSoup
import asyncio
import aiohttp
import pythonmonkey
    
class LingoJamTranslate():
    async def translate(self, text: str, lingojam_link: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(lingojam_link) as response:
                HTMLcontent = await response.text()
        HTMLcontent = BeautifulSoup(HTMLcontent, features="lxml")
        lasttagsrc=None
        variables=None
        for tag in HTMLcontent.body.find_all("script"):
            if lasttagsrc and len(tag.attrs.keys()) == 0 and lasttagsrc[:lasttagsrc.find("?")][lasttagsrc.find("/"):] == "/js/translate.js":
                variables = re.findall(r'.*var.*\n', tag.text)
                break
            lasttagsrc=tag.attrs.get("src")
        print(variables)
        jsonData = jsonData.strip().lstrip("var jsonData = ")[:-1]
        jsonData = json.loads(jsonData)
        return await self.translate_from_data(text, jsonData)

    async def translate_from_data(self, text: str, translator_data: dict):
        jsvarsstr=""
        for data in translator_data:
            array = translator_data[data].split("\n")
            if array[0]!='': jsvarsstr+=f"var {data}={array};\n"
            else: jsvarsstr+=f"var {data}=new Array();\n"
        js=open("lingojamtranslate/lingojamtranslate.js", "r").read()
        execute_str = jsvarsstr+js
        pythonmonkey.eval(execute_str)
        translate_func = pythonmonkey.eval("translate")
        pythonmonkey.new(translate_func)
        return translate_func(text)
    
translate = LingoJamTranslate()
asyncio.run(translate.translate("balls", "https://lingojam.com/WingdingsTranslator"))