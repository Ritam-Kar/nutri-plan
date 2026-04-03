import os
import sys
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.mcp_tool import MCPToolset
from mcp.client.stdio import StdioServerParameters

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_CLOUD_PROJECT"] = "nutri-plan-26"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

MODEL = "gemini-2.5-flash"

# --- MCP Toolsets ---

nutrition_tools = MCPToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=["/app/nutrition_mcp_server.py"]
    )
)

maps_tools = MCPToolset(
    connection_params=StdioServerParameters(
        command="google-maps-mcp-server",
        env={"GOOGLE_MAPS_API_KEY": os.environ.get("GOOGLE_MAPS_API_KEY", "")}
    )
)

calendar_tools = MCPToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=["-m", "google_calendar_mcp"],
        env={
            "GOOGLE_APPLICATION_CREDENTIALS": "/app/service-account.json",
            "GOOGLE_CALENDAR_ID": os.environ.get("GOOGLE_CALENDAR_ID", "primary")
        }
    )
)

# --- Sub Agents ---

profile_agent = LlmAgent(
    name="profile_agent",
    model=MODEL,
    instruction="""You are a profile extraction assistant.
    Extract the following from the user's message and save to session state as 'user_profile':
    - dietary_restrictions (e.g. vegetarian, vegan, lactose intolerant, gluten free)
    - weekly_budget_inr (number)
    - num_people (number)
    - location (neighbourhood and city)
    If anything is missing, use sensible defaults:
    - dietary_restrictions: none
    - weekly_budget_inr: 2000
    - num_people: 2
    - location: Bangalore
    Save as a clear JSON object to session state key 'user_profile'.
    Respond with: "Got your profile! Planning your meals now..." """
)

meal_planner_agent = LlmAgent(
    name="meal_planner_agent",
    model=MODEL,
    instruction="""You are an expert Indian meal planner.
    Read 'user_profile' from session state.
    Create a practical 7-day Indian meal plan with breakfast, lunch and dinner for each day.
    Rules:
    - Strictly respect all dietary restrictions
    - Use simple, commonly available Indian ingredients
    - Keep within the weekly budget
    - Prefer meals that share ingredients to reduce waste
    - Include a good variety across the week
    Save the complete plan as JSON to session state key 'meal_plan'.
    Respond with: "Meal plan ready! Fetching recipes and nutrition info..." """
)

recipe_nutrition_agent = LlmAgent(
    name="recipe_nutrition_agent",
    model=MODEL,
    tools=[nutrition_tools],
    instruction="""You are a nutrition analyst.
    Read 'meal_plan' from session state.
    For a representative sample of 5-6 key ingredients in the meal plan,
    use the get_nutrition tool to fetch their nutrition data.
    Use search_recipes for 2-3 main dishes to get recipe details.
    Summarise the overall nutritional profile of the week's plan.
    Save enriched data to session state key 'enriched_plan'.
    Respond with: "Nutrition analysis done! Building your grocery list..." """
)

grocery_agent = LlmAgent(
    name="grocery_agent",
    model=MODEL,
    instruction="""You are a grocery planning assistant.
    Read 'meal_plan' and 'enriched_plan' from session state.
    Read 'user_profile' to know number of people and budget.
    Create a complete consolidated grocery list for the week:
    - List every ingredient needed
    - Combine duplicates and sum quantities
    - Estimate realistic cost in INR for each item (Indian market prices)
    - Group items by category: Vegetables, Fruits, Dairy, Grains, Spices, Other
    - Show total estimated cost
    Save to session state key 'grocery_list'.
    Respond with: "Grocery list ready! Finding stores near you..." """
)

storefinder_agent = LlmAgent(
    name="storefinder_agent",
    model=MODEL,
    tools=[maps_tools],
    instruction="""You are a local store finder.
    Read 'user_profile' from session state to get the user's location.
    Read 'grocery_list' from session state.
    Use the nearby_search tool to find the 3 closest supermarkets or grocery stores.
    Use distance_matrix to get walking/driving time to each.
    Save store results to session state key 'store_results'.
    Then present the complete output to the user in this format:

    🗓️ YOUR 7-DAY MEAL PLAN
    [summarise the meal plan neatly]

    🛒 GROCERY LIST
    [show categorised grocery list with costs]
    💰 Total estimated cost: ₹XXX

    🏪 NEAREST STORES
    [list stores with distance and travel time]

    Finally ask:
    "Would you like me to block time on your Google Calendar for grocery shopping?
    I can add a 1-hour slot with your full shopping list. Just tell me which day and time!" """
)

calendar_agent = LlmAgent(
    name="calendar_agent",
    model=MODEL,
    tools=[calendar_tools],
    instruction="""You are a calendar scheduling assistant.
    Read 'grocery_list' from session state.
    Read 'store_results' from session state to get the nearest store name.
    When the user confirms a day and time for grocery shopping:
    - Create a Google Calendar event titled "🛒 Weekly Grocery Run"
    - Duration: 1 hour
    - Location: the nearest store name and address
    - Description: the full grocery list formatted as a checklist with checkboxes
    - Add a reminder 30 minutes before
    Confirm back with:
    "✅ Done! Added to your calendar:
    📅 [day and date]
    ⏰ [time] - [end time]
    📍 [store name]
    Your grocery list is in the event description!" """
)

# --- Root Coordinator Agent ---

root_agent = LlmAgent(
    name="nutri_plan",
    model=MODEL,
    instruction="""You are NutriPlan, a friendly AI meal planning assistant.

    When a user gives you their dietary preferences, budget and location:
    1. Hand off to profile_agent to extract their details
    2. Hand off to meal_planner_agent to create the 7-day plan
    3. Hand off to recipe_nutrition_agent to enrich with nutrition data
    4. Hand off to grocery_agent to build the shopping list
    5. Hand off to storefinder_agent to find nearby stores and present everything

    After the full plan is presented, if the user agrees to add grocery shopping
    to their calendar, hand off to calendar_agent with their preferred day and time.

    Be warm, friendly and encouraging throughout.
    If the user just says hi or asks what you do, explain:
    "Hi! I'm NutriPlan 🥗 I can plan your week of meals based on your diet and budget,
    build your grocery list, find stores near you, and even block time on your calendar
    for shopping. Just tell me your dietary needs, weekly budget, and location!" """,
    sub_agents=[
        profile_agent,
        meal_planner_agent,
        recipe_nutrition_agent,
        grocery_agent,
        storefinder_agent,
        calendar_agent
    ]
)