# %%
# Librerías
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo

# Funciones del proyecto
import scrapping_functions
from scrapping_functions import get_json_from_url, save_json, parse_json_to_model

# %% [markdown]
# ##### Categorías

# %%
categories_payload = [
  {
    "operationName": "GetCategoryTree",
    "variables": {
      "getCategoryInput": {
        "clientId": "CADENA_REAL",
        "storeReference": "2"
      }
    },
    "query": "fragment CategoryFields on CategoryModel {\n  active\n  boost\n  hasChildren\n  categoryNamesPath\n  isAvailableInHome\n  level\n  name\n  path\n  reference\n  slug\n  photoUrl\n  imageUrl\n  shortName\n  isFeatured\n  isAssociatedToCatalog\n  __typename\n}\n\nfragment CategoriesRecursive on CategoryModel {\n  subCategories {\n    ...CategoryFields\n    subCategories {\n      ...CategoryFields\n      subCategories {\n        ...CategoryFields\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CategoryModel on CategoryModel {\n  ...CategoryFields\n  ...CategoriesRecursive\n  __typename\n}\n\nquery GetCategoryTree($getCategoryInput: GetCategoryInput!) {\n  getCategory(getCategoryInput: $getCategoryInput) {\n    ...CategoryModel\n    __typename\n  }\n}"
  },
  {
    "operationName": "getDynamicHome",
    "variables": {
      "getDynamicHomeInput": {
        "breakpointId": "medium",
        "storeReference": "2",
        "targetType": "WEB",
        "clientId": "CADENA_REAL"
      }
    },
    "query": "query getDynamicHome($getDynamicHomeInput: GetDynamicHomeInput!) {\n  getDynamicHome(getDynamicHomeInput: $getDynamicHomeInput)\n}"
  }
]

# %%
json_response = get_json_from_url(
    url = "https://nextgentheadless.instaleap.io/api/v3",
    method = "POST",
    payload = categories_payload
)


# %%
save_json(
    data=json_response[0]["data"]["getCategory"],
    name="real_categories",
    subfolder="real/categories"
)

# %%
if json_response:
    items = json_response[0]["data"]["getCategory"]
    df = pd.DataFrame(items)
    df["ingestion_time"] = datetime.now(ZoneInfo("America/Asuncion"))
    df["supermarket"] = "real"

# %%
df.head()

# %% [markdown]
# ##### Productos

# %%
categories = df["reference"].unique()
np.random.shuffle(categories)
print(f"Number of categories -> {categories.size}")
categories

# %%
def build_payload(category_reference, page):
    return [{
        "operationName": "GetProductsByCategory",
        "variables": {
            "getProductsByCategoryInput": {
                "categoryReference": category_reference,
                "categoryId": "null",
                "clientId": "CADENA_REAL",
                "storeReference": "2",
                "currentPage": page,
                "pageSize": 100,
                "filters": {},
                "googleAnalyticsSessionId": ""
            }
        },
        "query": "fragment CategoryFields on CategoryModel {\n  active\n  boost\n  hasChildren\n  categoryNamesPath\n  isAvailableInHome\n  level\n  name\n  path\n  reference\n  slug\n  photoUrl\n  imageUrl\n  shortName\n  isFeatured\n  isAssociatedToCatalog\n  __typename\n}\n\nfragment CatalogProductTagModel on CatalogProductTagModel {\n  description\n  enabled\n  textColor\n  filter\n  tagReference\n  backgroundColor\n  name\n  __typename\n}\n\nfragment CatalogProductFormatModel on CatalogProductFormatModel {\n  format\n  equivalence\n  unitEquivalence\n  clickMultiplier\n  minQty\n  maxQty\n  __typename\n}\n\nfragment Taxes on ProductTaxModel {\n  taxId\n  taxName\n  taxType\n  taxValue\n  taxSubTotal\n  __typename\n}\n\nfragment PromotionCondition on PromotionCondition {\n  quantity\n  price\n  priceBeforeTaxes\n  taxTotal\n  taxes {\n    ...Taxes\n    __typename\n  }\n  __typename\n}\n\nfragment Promotion on Promotion {\n  type\n  isActive\n  conditions {\n    ...PromotionCondition\n    __typename\n  }\n  description\n  endDateTime\n  startDateTime\n  __typename\n}\n\nfragment PromotedModel on PromotedModel {\n  isPromoted\n  onLoadBeacon\n  onClickBeacon\n  onViewBeacon\n  onBasketChangeBeacon\n  onWishlistBeacon\n  __typename\n}\n\nfragment SpecificationModel on SpecificationModel {\n  title\n  values {\n    label\n    value\n    __typename\n  }\n  __typename\n}\n\nfragment NutritionalDetailsInformation on NutritionalDetailsInformation {\n  servingName\n  servingSize\n  servingUnit\n  servingsPerPortion\n  nutritionalTable {\n    nutrientName\n    quantity\n    unit\n    quantityPerPortion\n    dailyValue\n    __typename\n  }\n  bottomInfo\n  __typename\n}\n\nfragment Promotions on PromotionV2 {\n  type\n  description\n  promotionReference\n  startDateTime\n  endDateTime\n  isActive\n  conditions {\n    field\n    operator\n    values\n    value\n    __typename\n  }\n  benefit {\n    type\n    label\n    value\n    values\n    imagesURL\n    __typename\n  }\n  __typename\n}\n\nfragment CatalogProductModel on CatalogProductModel {\n  name\n  price\n  photosUrl\n  unit\n  subUnit\n  subQty\n  description\n  sku\n  ean\n  maxQty\n  minQty\n  clickMultiplier\n  nutritionalDetails\n  isActive\n  slug\n  brand\n  stock\n  securityStock\n  boost\n  isAvailable\n  location\n  priceBeforeTaxes\n  taxTotal\n  promotion {\n    ...Promotion\n    __typename\n  }\n  taxes {\n    ...Taxes\n    __typename\n  }\n  categories {\n    ...CategoryFields\n    __typename\n  }\n  categoriesData {\n    ...CategoryFields\n    __typename\n  }\n  formats {\n    ...CatalogProductFormatModel\n    __typename\n  }\n  tags {\n    ...CatalogProductTagModel\n    __typename\n  }\n  specifications {\n    ...SpecificationModel\n    __typename\n  }\n  promoted {\n    ...PromotedModel\n    __typename\n  }\n  score\n  relatedProducts\n  ingredients\n  stockWarning\n  nutritionalDetailsInformation {\n    ...NutritionalDetailsInformation\n    __typename\n  }\n  productVariants\n  isVariant\n  isDominant\n  promotions {\n    ...Promotions\n    __typename\n  }\n  seals\n  previousPrice\n  previousPricePerSubUnit\n  pricePerSubUnit\n  hasAgeRestriction\n  __typename\n}\n\nfragment CategoryWithProductsModel on CategoryWithProductsModel {\n  name\n  reference\n  level\n  path\n  hasChildren\n  active\n  boost\n  isAvailableInHome\n  slug\n  photoUrl\n  categoryNamesPath\n  imageUrl\n  shortName\n  isFeatured\n  products {\n    ...CatalogProductModel\n    __typename\n  }\n  __typename\n}\n\nfragment PaginationTotalModel on PaginationTotalModel {\n  value\n  relation\n  __typename\n}\n\nfragment PaginationModel on PaginationModel {\n  page\n  pages\n  total {\n    ...PaginationTotalModel\n    __typename\n  }\n  __typename\n}\n\nfragment AggregateBucketModel on AggregateBucketModel {\n  min\n  max\n  key\n  docCount\n  __typename\n}\n\nfragment AggregateModel on AggregateModel {\n  name\n  docCount\n  buckets {\n    ...AggregateBucketModel\n    __typename\n  }\n  __typename\n}\n\nfragment BannerModel on BannerModel {\n  id\n  storeId\n  title\n  desktopImage\n  mobileImage\n  targetUrl\n  targetUrlInfo {\n    type\n    url\n    __typename\n  }\n  targetCategory\n  index\n  categoryId\n  __typename\n}\n\nfragment CarouselModel on CarouselModel {\n  id\n  name\n  autoplaySpeed\n  lazyLoading\n  isActive\n  createdAt\n  updatedAt\n  banners {\n    id\n    name\n    webImageUrl\n    tabletImageUrl\n    appImageUrl\n    redirectUrl\n    redirectMode\n    isActive\n    __typename\n  }\n  position\n  __typename\n}\n\nquery GetProductsByCategory($getProductsByCategoryInput: GetProductsByCategoryInput!) {\n  getProductsByCategory(getProductsByCategoryInput: $getProductsByCategoryInput) {\n    category {\n      ...CategoryWithProductsModel\n      __typename\n    }\n    pagination {\n      ...PaginationModel\n      __typename\n    }\n    aggregates {\n      ...AggregateModel\n      __typename\n    }\n    carousels {\n      ...CarouselModel\n      __typename\n    }\n    banners {\n      ...BannerModel\n      __typename\n    }\n    promoted {\n      ...PromotedModel\n      __typename\n    }\n    __typename\n  }\n}"
    }
]

# %%
NOW = datetime.now(ZoneInfo("America/Asuncion"))
BASE_URL = "https://nextgentheadless.instaleap.io/api/v3"
PAGE_SIZE = 100

all_products = []
total_calls = 0

print(f"🔍 Iniciando scraping de {len(categories)} categorías...\n")

for i, category in enumerate(categories, start=1):
    print(f"[{i}/{len(categories)}] Scrapeando categoría: {category}")
    page = 1

    while True:
        payload = build_payload(category_reference=category, page=page)

        try:
            data = get_json_from_url(
                url=BASE_URL,
                method="POST",
                payload=payload,
                fixed_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ",
                use_random_wait=True,
                silent=True
            )
        except Exception as e:
            print(f"[❌] Fallo en categoría {category}, página {page}: {e}")
            break

        total_calls += 1

        products = (
            data[0].get("data", {})
                .get("getProductsByCategory", {})
                .get("category", {})
                .get("products", [])
        )

        if not products:
            break

        for product in products:
            product["category"] = category
            product["ingestion_time"] = NOW

        all_products.extend(products)

        print(f"    ↳ Página {page}: {len(products)} productos")
        page += 1

print(f"\n✅ Fin del scraping: {len(all_products)} productos recolectados en {total_calls} requests.")

# %%
save_json(
    data=all_products,
    name="real_products",
    subfolder="real/products"
)


