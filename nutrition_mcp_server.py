import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("nutrition-mcp-server")

@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="search_recipes",
            description="Search for recipes and nutrition info by food name or ingredient",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Food name or ingredient to search for"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_nutrition",
            description="Get detailed nutrition facts for a specific ingredient or food item",
            inputSchema={
                "type": "object",
                "properties": {
                    "ingredient": {
                        "type": "string",
                        "description": "Name of the ingredient or food"
                    }
                },
                "required": ["ingredient"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_recipes":
        query = arguments["query"]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://world.openfoodfacts.org/cgi/search.pl",
                    params={
                        "search_terms": query,
                        "json": 1,
                        "page_size": 5,
                        "fields": "product_name,nutriments,ingredients_text,categories"
                    }
                )
                data = resp.json()
                products = data.get("products", [])
                results = []
                for p in products[:3]:
                    results.append({
                        "name": p.get("product_name", "Unknown"),
                        "ingredients": p.get("ingredients_text", "Not available"),
                        "calories_per_100g": p.get("nutriments", {}).get("energy-kcal_100g", "N/A"),
                        "protein_per_100g": p.get("nutriments", {}).get("proteins_100g", "N/A"),
                        "carbs_per_100g": p.get("nutriments", {}).get("carbohydrates_100g", "N/A"),
                        "fat_per_100g": p.get("nutriments", {}).get("fat_100g", "N/A")
                    })
                return [types.TextContent(type="text", text=str(results))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error fetching recipes: {str(e)}")]

    elif name == "get_nutrition":
        ingredient = arguments["ingredient"]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.nal.usda.gov/fdc/v1/foods/search",
                    params={
                        "query": ingredient,
                        "api_key": "DEMO_KEY",
                        "pageSize": 3,
                        "dataType": "Foundation,SR Legacy"
                    }
                )
                data = resp.json()
                foods = data.get("foods", [])
                results = []
                for food in foods[:2]:
                    nutrients = {n["nutrientName"]: n["value"]
                                for n in food.get("foodNutrients", [])
                                if n["nutrientName"] in [
                                    "Energy", "Protein",
                                    "Carbohydrate, by difference",
                                    "Total lipid (fat)", "Fiber, total dietary"
                                ]}
                    results.append({
                        "name": food.get("description", "Unknown"),
                        "nutrients_per_100g": nutrients
                    })
                return [types.TextContent(type="text", text=str(results))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error fetching nutrition: {str(e)}")]

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())