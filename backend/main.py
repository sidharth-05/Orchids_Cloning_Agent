from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import uvicorn
import httpx
from bs4 import BeautifulSoup
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
import traceback
import os
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
            # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'lxml')

    # Extract relevant information from the soup object
    # Extract text content & tags
    for tag in soup.find_all(['script', 'style', 'meta', 'noscript', 'header', 'footer', 'nav', 'form', 'iframe', 'aside', 'input', 'button', 'svg', 'link']):
        tag.decompose()

    html_structure = soup.prettify()
    print("Parsed HTML structure successfully.")

    
    # Send to Gemini
    prompt = f"""
You are a web cloning assistant. Based on the HTML below, generate a full HTML page that visually looks like the original website.

Focus on layout, text content, structure, and style. Use embedded CSS and placeholders for assets (like images or icons).

{html_structure}

Return a complete HTML page starting with <!DOCTYPE html>.

Please return a full HTML page with embedded CSS that mimics the layout, fonts, and colors as best as possible. You can use placeholder images or links where needed.
"""

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
