from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import uvicorn
import httpx
import base64
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
import traceback
import os
from playwright.async_api import async_playwright
from pathlib import Path

dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path)
print("Loaded API Key:", os.getenv("GEMINI_API_KEY"))
# Removed genai.list_models() as it does not exist in the google.generativeai module

# Create FastAPI instance
app = FastAPI(
    title="Orchids Challenge API",
    description="A starter FastAPI template for the Orchids Challenge backend",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#------------- Defaults -------------#
# Pydantic models
class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None


# In-memory storage for demo purposes
items_db: List[Item] = [
    Item(id=1, name="Sample Item", description="This is a sample item"),
    Item(id=2, name="Another Item", description="This is another sample item")
]

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Hello from FastAPI backend!", "status": "running"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchids-challenge-api"}

# Get all items
@app.get("/items", response_model=List[Item])
async def get_items():
    return items_db

# Get item by ID
@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item.id == item_id:
            return item
    return {"error": "Item not found"}

# Create new item
@app.post("/items", response_model=Item)
async def create_item(item: ItemCreate):
    new_id = max([item.id for item in items_db], default=0) + 1
    new_item = Item(id=new_id, **item.dict())
    items_db.append(new_item)
    return new_item

# Update item
@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemCreate):
    for i, existing_item in enumerate(items_db):
        if existing_item.id == item_id:
            updated_item = Item(id=item_id, **item.dict())
            items_db[i] = updated_item
            return updated_item
    return {"error": "Item not found"}

# Delete item
@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item.id == item_id:
            deleted_item = items_db.pop(i)
            return {"message": f"Item {item_id} deleted successfully", "deleted_item": deleted_item}
    return {"error": "Item not found"}

#------------- Defaults -------------#


class URLRequest(BaseModel):
    url: str

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables")

# Correct way to configure the API key for google.generativeai
genai.configure(api_key=api_key)

async def take_screenshot_with_playwright(url: str) -> Optional[str]:
    """
    Takes a screenshot of the given URL using Playwright and returns it as a base64 encoded string.
    Returns None if an error occurs.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=60000) # Increased timeout for slower pages
            screenshot_bytes = await page.screenshot(type='png') # Specify PNG for definite MIME type
            await browser.close()

            base64_encoded_screenshot = base64.b64encode(screenshot_bytes).decode('utf-8')
            print(f"Successfully took screenshot for {url}")
            return base64_encoded_screenshot
    except Exception as e:
        print(f"Error taking screenshot with Playwright for {url}: {e}")
        traceback.print_exc() # Print full traceback for debugging
        return None

@app.post("/scrape-and-analyze")
# Endpoint to scrape a URL and return cleaned text content
async def scrape_and_analyze(request: URLRequest):
    url = request.url
    print(f"Received URL to clone: {url}")

    try:
        async with httpx.AsyncClient() as http_client:
            # Fetch the HTML content of the URL
            response = await http_client.get(url, timeout=10)
            response.raise_for_status() # Check if the request was successful by status code 400 or higher
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch URL: {response.status_code}")
            # Get the HTML content as text
            html_content = response.text
            print(f"Fetched HTML content from {url}")

    # Take screenshot
    base64_screenshot = await take_screenshot_with_playwright(url)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
            # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'lxml')

    # --- Start Image Scraping ---
    img_tags = soup.find_all('img')
    print(f"Found {len(img_tags)} image tags.")

    async with httpx.AsyncClient() as image_client:
        for img_tag in img_tags:
            src = img_tag.get('src')
            if not src:
                print("Image tag found with no src, skipping.")
                continue

            try:
                # Make URL absolute
                abs_src = urljoin(url, src)
                print(f"Attempting to download image: {abs_src}")

                # Fetch image data
                img_response = await image_client.get(abs_src, timeout=10)
                img_response.raise_for_status() # Check for HTTP errors

                # Convert image to base64
                img_content = img_response.content
                mime_type = img_response.headers.get('content-type', 'image/png') # Default to png if not found
                base64_encoded_img = base64.b64encode(img_content).decode('utf-8')

                # Update img tag src with base64 data URI
                img_tag['src'] = f"data:{mime_type};base64,{base64_encoded_img}"
                print(f"Successfully processed and embedded image: {abs_src}")

            except httpx.HTTPStatusError as e:
                print(f"HTTP error downloading image {abs_src}: {e.response.status_code} - {e.response.text}")
                img_tag['alt'] = img_tag.get('alt', '') + f" (Image not found: {abs_src})"
            except httpx.RequestError as e:
                print(f"Request error downloading image {abs_src}: {e}")
                img_tag['alt'] = img_tag.get('alt', '') + f" (Image not found: {abs_src})"
            except Exception as e:
                print(f"Error processing image {abs_src}: {e}")
                img_tag['alt'] = img_tag.get('alt', '') + f" (Image processing error: {abs_src})"
    # --- End Image Scraping ---

    # Extract relevant information from the soup object
    # Extract text content & tags
    for tag in soup.find_all(['script', 'meta', 'noscript', 'header', 'footer', 'nav', 'form', 'iframe', 'aside', 'input', 'button', 'svg']):
        tag.decompose()

    html_structure = soup.prettify()
    print("Parsed HTML structure successfully.")

    
    # Send to Gemini
    # Construct the prompt for Gemini
    prompt_parts = [
        "You are an expert web cloning assistant. Your goal is to replicate a webpage as accurately as possible, visually and structurally.",
        "You will be given the HTML structure (which now includes original CSS and base64 embedded images) and a base64 encoded screenshot of the original page.",
        "Prioritize the visual accuracy based on the screenshot.",
        "Ensure the generated HTML page uses embedded CSS to style elements. The provided HTML may already contain <style> tags or <link rel=\"stylesheet\"> tags; preserve and utilize these.",
        "Images in the provided HTML are already embedded as base64 data URIs. Ensure these are correctly rendered.",
        "Pay close attention to layout, element positioning, fonts, colors, spacing, and overall visual hierarchy as depicted in the screenshot.",
        "Return a single, complete HTML page starting with <!DOCTYPE html>.",
        "Here is the HTML structure (with embedded CSS and images):",
        html_structure,
    ]

    if base64_screenshot:
        prompt_parts.extend([
            "And here is the base64 encoded PNG screenshot of the original page for visual reference:",
            f"data:image/png;base64,{base64_screenshot}",
            "Use this screenshot as your primary guide for visual replication."
        ])
    else:
        prompt_parts.append("A screenshot could not be captured, so rely solely on the provided HTML structure and embedded styles/images.")

    prompt_parts.append("Generate the full HTML page now.")
    prompt = "\n\n".join(prompt_parts)

    try:
        # Instantiate the model directly
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        response = model.generate_content(prompt)

        # Safely access the summary text
        if response.text:
            html_output = response.text
        else:
            html_output = "<p>Could not generate HTML from LLM.</p>"
            print("Warning: Empty LLM response.")

        return {
            "url": url,
            "html": html_output
        }
    
    except Exception as e:
        print("LLM error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

def main():
    """Run the application"""
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
