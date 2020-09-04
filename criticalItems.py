# selenium webdriver python modules
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# import time module
import time
# import json module
import json
# import py mongo module
import pymongo
# importing beautiful soup to format html data
from bs4 import BeautifulSoup
# logging module to log details
import logging
import datetime
from environs import Env

env = Env()
env.read_env()  # read .env file, if it exists
# required variables
mongouser = env("MONGO_USER")
mongopass = env("MONGO_PASS")
mongohost = env("MONGO_HOST")
mongodb = env("MONGO_DB")

logging.basicConfig(filename="log",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S')
log = logging.getLogger("items")
log.setLevel(logging.INFO)

critical_objects_list = []
if __name__ == '__main__':
    try:
        myclient = pymongo.MongoClient(
            "mongodb+srv://" + mongouser + ":" + mongopass + "@" + mongohost + "/" + mongodb + "?retryWrites=true&w=majority")
        mydb = myclient.optima_db
        settingcol = mydb.settings
        myquery = {"name": "url"}
        result = settingcol.find(myquery)
        for x in result:
            SCRAPE_URL = x["value"]
        log.info(SCRAPE_URL)
        # i have kept a crawl setting in db to controll minimum seconds duration between crawls
        myquery = {"name": "crawlafterseconds"}
        result = settingcol.find(myquery)
        for x in result:
            minwaitbetweencrawl = x["value"]
        log.info(minwaitbetweencrawl)

        lastcrawledquery = {"name": "last_crawled"}
        result = settingcol.find(lastcrawledquery)
        for x in result:
            lastcrawled = x["value"]
            date_time_obj = lastcrawled
        currenttimestamp = datetime.datetime.now()
        if (currenttimestamp - date_time_obj).total_seconds() > minwaitbetweencrawl:
            log.info("running crawler")
            # chrome driver is needed for this
            # Downloads link : https://chromedriver.storage.googleapis.com/index.html?path=84.0.4147.30/
            # chrome driver path after download
            # DRIVER = './chromedriver'
            DRIVER = './chromedriver'
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            driver = webdriver.Chrome(DRIVER, options=chrome_options)
            try:
                driver.get(SCRAPE_URL)
            except Exception as exc:
                log.critical(str(exc))
                print("Unable to access the website")
                exit

            # sleep timer to fetch the full page request
            time.sleep(5)

            # fetching full page source to pass it for abstraction
            data = driver.page_source
            soup = BeautifulSoup(data, 'lxml')

            try:
                table = soup.find('div', {"class": "critical-product-table-container"}).find(
                    'div', {"class": "table"}).find('div').find('div')
                # storing critical items in list'
                i = 0
                for row in table:
                    a_dict = dict()
                    a_dict["productName"] = row.find('a').find(
                        'div', {'class': 'line-item-title'}).find(text=True)
                    availability = row.find('a').find(
                        'div', {'class': 'available'}).find(text=True)
                    a_dict["availability"] = int(
                        ''.join(j for j in availability if j.isdigit()))

                    critical_objects_list.append(a_dict)
                    i = i + 1
                log.info("critical product list updated")

                # closing the selenium web driver
                driver.quit()

                mycol = mydb.products
                if i > 0:
                    mycol.delete_many({})
                    log.info("delete existing records")

                log.info("insert updated products/updated list of products")
                for itemJson in critical_objects_list:
                    log.info(str(itemJson))
                    mycol.insert_one(itemJson)

                # save the last crawled time in mongo instance
                newvalues = {"$set": {"value": datetime.datetime.now()}}
                settingcol.update_one(lastcrawledquery, newvalues)
            except Exception as exc:
                log.critical(str(exc))
                print("Unable to fetch critical object from the website")

    except Exception as desx:
        log.critical(str(desx))
        print("Exception while dumping information to mongodb")
