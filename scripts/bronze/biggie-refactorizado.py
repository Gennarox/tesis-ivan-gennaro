# %%
import pandas
import scrapping_functions
from scrapping_functions import get_json_from_url, save_json

# %%
url = "https://api.app.biggie.com.py/api/classifications/web?take=-1&storeType="
json_response = get_json_from_url(url)

# %%
save_json(
    data=json_response.get("items", []),
    name="biggie_categories",
    subfolder="biggie/categories"
)

# %%



