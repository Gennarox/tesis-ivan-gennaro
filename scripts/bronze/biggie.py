#!/usr/bin/env python
# coding: utf-8

# In[1]:


import curl_cffi
from curl_cffi import requests
import json
import pandas as pd
import numpy as np
import requests
import scraper_functions
from scraper_functions import VPNTester, ScraperClient
import openpyxl
import pydantic_model
from pydantic_model import categories, products
import pydantic
from pydantic import ValidationError

import random
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path


# ##### VPN Checker

# In[2]:


tester = VPNTester()
tester.vpn_check()


# ##### Fixing impersonate agent for the session

# In[3]:


FIXED_IMPERSONATE = random.choice(scraper_functions.IMPERSONATE_OPTIONS)
print(FIXED_IMPERSONATE)


# ## Product Categories

# ##### Get json

# In[4]:


url = "https://api.app.biggie.com.py/api/classifications/web?take=-1&storeType="

scraper = ScraperClient(
    url, 
    random_wait = True, 
    impersonate = FIXED_IMPERSONATE
)

json_response = scraper.get_json()


# ##### Saving raw json file

# In[5]:


ScraperClient.save_json_raw(
    json_response.get("items", []), 
    supermarket="biggie", 
    subfolder=f'/workspaces/proyecto-tesis/outputs/biggie/categories', 
    name='categories'
)


# ##### Parse JSON to Model

# In[6]:


if json_response :
    categories_model = ScraperClient.parse_json_to_model(
        json_data = json_response, 
        model_class = categories, 
        supermarket = 'biggie'
    )


# ##### Model -> Dataframe | Validation

# In[7]:


# Convert to list of dicts and then to DataFrame
df = pd.DataFrame([c.model_dump() for c in categories_model])
df.head()


# In[8]:


df.to_csv('/workspaces/proyecto-tesis/outputs/biggie/categories/biggie_categories_test.csv')


# # Product Data

# In[9]:


# Original sorting
categories = df["slug"].unique() # [15:-3] subset for testing
print(categories.size)
categories


# In[10]:


# Shuffleled
categories = df["slug"].unique() # [15:-3] subset for testing
np.random.shuffle(categories)
print(categories.size)
categories

categories = ['panaderia']


# #### Get JSON
# 4 min 47s for last three categories //
# 1 min for last category //
# 35 min 11s for full scrap (1st test on 29/06)

# In[11]:


# SUPER = "Biggie" # [Done at parsing to pydantic model]
NOW = datetime.now(ZoneInfo("America/Asuncion"))
# FIXED_IMPERSONATE = random.choice(scraper_functions.IMPERSONATE_OPTIONS) [Done at session level]

all_items = []
NumberResults = 24

for category in categories:
    skip_value = 0

    while True:
        url = (
            f"https://api.app.biggie.com.py/api/articles"
            f"?take={NumberResults}&skip={skip_value}&classificationName={category}"
        )

        scraper = ScraperClient(
            url=url,
            impersonate=FIXED_IMPERSONATE,  # ❗️Fijo durante toda la sesión
            random_wait=True                 # ❗️Simula comportamiento humano
        )
        json_response = scraper.get_json()

        items = json_response.get("items", [])

        if not items:
            break

        for item in items:
            item["category"] = category
            # item["supermarket"] = SUPER
            item["ingestion_time"] = NOW

        all_items.extend(items)
        skip_value += NumberResults


# ##### Saving raw json file

# In[12]:


ScraperClient.save_json_raw(
    data = all_items,
    supermarket="biggie", 
    subfolder=f'/workspaces/proyecto-tesis/outputs/biggie/products', 
    name='products'
)


# ##### Parse JSON to Model

# In[13]:


# Manual JSON Load
'''
with open('/workspaces/proyecto-tesis/outputs/biggie/products/biggie/biggie_products_2025-06-29_15-21-52.json', 'r') as f:
        all_items = json.load(f)

all_items
'''


# In[14]:


if all_items :
    products_model = ScraperClient.parse_json_to_model(
        json_data = all_items, 
        model_class = products, 
        supermarket = 'biggie'
    )


# ##### Model -> Dataframe | Validation

# In[15]:


df = pd.DataFrame([c.model_dump() for c in products_model])
df.head()


# In[16]:


df.to_csv('/workspaces/proyecto-tesis/outputs/biggie/products/biggie_products_test.csv')

