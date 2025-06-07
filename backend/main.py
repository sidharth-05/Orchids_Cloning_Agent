from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import base64
from playwright.async_api import async_playwright
import openai
import requests
from bs4 import BeautifulSoup
import openai
import os
from dotenv import load_dotenv
import re

load_dotenv()

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

# Request schema
class CloneRequest(BaseModel):
    url: str

@app.post("/api/clone")
async def clone_website(req: CloneRequest):
    try:
        html, inline_styles = await scrape_website(req.url)
        html = html.decode("utf-8") if isinstance(html, (bytes, bytearray)) else str(html)
        prompt = build_prompt(html, inline_styles)
        cloned_html = await call_llm(prompt)
        return {"cloned_html": cloned_html}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


async def scrape_website(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("load")

        # Grab rendered HTML
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Extract inline <style> content
        style_tags = soup.find_all("style")
        inline_styles = "\n".join(tag.get_text() for tag in style_tags)

        await browser.close()
        return soup.prettify(), inline_styles


def build_prompt(html: str, styles: str) -> str:
    return f"""
You are a frontend developer AI. Recreate a clean HTML clone of the following website.

Use only inline CSS. Do not include external images or stylesheets. Use placeholder images and links where needed. Just return the HTML content, nothing else.


Here is the DOM:
{html}

Here is the CSS:
{styles}

Output a single standalone HTML page.
"""

def clean_llm_output(text: str) -> str:
    # Remove anything before the actual HTML content
    match = re.search(r"(<!(DOCTYPE html|doctype html)|<html)", text, re.IGNORECASE)
    if match:
        return text[match.start():].strip()
    return text.strip()


async def call_llm(prompt: str) -> str:
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",  # Switch to "gpt-4" if you have access
        messages=[
            {"role": "system", "content": "You are a helpful assistant skilled at recreating websites."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    raw_output = response["choices"][0]["message"]["content"]

    match = re.search(r"```html\s*(.*?)\s*```", raw_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    return clean_llm_output(raw_output)