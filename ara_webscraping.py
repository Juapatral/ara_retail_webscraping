# Modules

# json
import json

# Dates
from datetime import datetime

# Dataframes
import pandas as pd

# Webscraping tools
import requests

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

pd.set_option("display.max.columns", None)


# Constants
REGIONS = [None, "norte", "sur", "oriente", "occidente", "centro"]


def webscraping_ara(regions: list) -> pd.DataFrame:
    """Webscraping Ara retail Website.

    Args:
        regions (list): Region list to scrap products info.

    Returns:
        pd.DataFrame: Dataframe with products info.
    """
    # Get date
    now = datetime.now()
    products_dataframe_list = []
    print("---------- ARA WEBSCRAPING INITIALIZING ----------")
    print(f"---------- Extracting products on: {now.date()} ----------")

    # For each region
    for region in regions:
        url = f"https://aratiendas.com/rebajon/{region}/"
        if region is None:  # AKA National search
            url = "https://aratiendas.com/rebajon/"

        # Get driver and network info
        web_driver = _create_web_driver()
        web_driver.get(url)
        browser_log = web_driver.get_log("performance")
        events = [_process_browser_log_entry(entry) for entry in browser_log]

        # Admin network has product data
        for number_event, event in enumerate(events):
            if str(event).find("admin") != -1:
                first_event = number_event
                break

        # Get network response
        products = web_driver.execute_cdp_cmd(
            "Network.getResponseBody",
            {"requestId": events[first_event]["params"]["requestId"]},
        ).get("body")

        if not products:
            continue

        json_products = json.loads(products)
        list_products = json_products.get("data")

        # Start processing each product
        print("------- Processing region:", region, "-------")
        print("Total products:", len(list_products))

        list_products_info = []
        for product in list_products:
            # Get all product info and add some more
            product_info = _get_product_info(product)
            product_info["extracted_region"] = region
            product_info["extracted_datetime"] = now
            product_info["extracted_date"] = now.strftime("%Y%m%d")
            product_info["extracted_time"] = now.strftime("%H:%M:%S")
            list_products_info.append(product_info)

        # Concat products  of a region
        region_product_dataframe = pd.DataFrame(list_products_info)
        products_dataframe_list.append(region_product_dataframe)

    # Concat all products from all regions
    products_dataframe = pd.concat(products_dataframe_list).reset_index(drop=True)

    return products_dataframe


# Private functions

# Get newtwork responses
# https://stackoverflow.com/questions/
# 52633697/selenium-python-how-to-capture-network-traffics-response

# Create selenium driver
def _create_web_driver() -> WebDriver:
    """Create webdriver with specific options.

    Returns:
        WebDriver: Webdriver with options.
    """
    # Get logs for each networkd
    caps = DesiredCapabilities.CHROME
    caps["goog:loggingPrefs"] = {"performance": "ALL"}

    # Set options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("w3c", True)
    web_driver = webdriver.Chrome(
        "chromedriver", options=chrome_options, desired_capabilities=caps
    )
    return web_driver


# Select product info
def _get_product_info(product_info: dict) -> dict:
    """Extract product info from a product json.

    Args:
        product_info (dict): Product information in json format

    Returns:
        dict: Desired product info.
    """
    # Get dict
    product_scraped = {}

    product_scraped["id"] = product_info.get("ID")

    product_scraped["image_url"] = product_info.get("image")

    product_scraped["post_type"] = product_info.get("post_type")

    product_scraped["post_date"] = product_info.get("post_date")

    product_scraped["post_modified"] = product_info.get("post_modified")

    product_scraped["post_status"] = product_info.get("post_status")

    product_scraped["post_name"] = product_info.get("post_name")
    product_scraped["product_name"] = product_info.get("post_name")

    product_scraped["post_title"] = product_info.get("post_title")

    meta = product_info.get("meta")

    # Meta has some extra description for the product, each element as a list.
    if meta:
        product_scraped["comunicacion_type"] = _get_first_element(meta, "comunicacion")

        product_scraped["product_description"] = _get_first_element(meta, "descripcion")

        product_scraped["sale_price"] = _get_first_element(meta, "precio_promocion_")

        product_scraped["price"] = _get_first_element(meta, "precio_referente")

        product_scraped["price_type"] = _get_first_element(
            meta, "tipo_de_precio_referente"
        )

        product_scraped["brand"] = _get_first_element(meta, "marca")

        product_scraped["outstanding"] = _get_first_element(meta, "producto_destacado")

        product_scraped["sap_ean_code"] = _get_first_element(meta, "sap-ean")

        product_scraped["region"] = _get_first_element(meta, "region")

        product_scraped["measure"] = _get_first_element(meta, "unidad_de_medida")

    # Get product url and category
    product_name = product_scraped.get("product_name")
    product_type = product_scraped.get("post_type")

    product_url = f"https://aratiendas.com/{product_type}/{product_name}/"
    product_request = requests.get(product_url).url.replace("%", "")
    category = (
        product_request.replace("https://aratiendas.com/", "")
        .replace(f"{product_type}/", "")
        .replace(f"/{product_name}/", ""),
    )

    product_scraped["product_url"] = product_url
    product_scraped["category"] = category

    return product_scraped


# Get Network data from a website
def _process_browser_log_entry(entry) -> dict:
    """Get logs from the websites networks.

    Args:
        entry (_type_): Logs.

    Returns:
        dict: Logs of each network.
    """
    response = json.loads(entry["message"])["message"]
    return response


# Get first element of a list in a dict
def _get_first_element(origin_dict_: dict, key: str) -> str:
    """Get first element of a list if it exists in a dict.

    Args:
        origin_dict_ (dict): Dict to search for the key.
        key (str): Key searched.

    Returns:
        str: First element of list, if exists, as string format.
    """
    found_key = origin_dict_.get(key)
    value = ""
    if isinstance(found_key, list):
        value = str(key[0])
    return value
