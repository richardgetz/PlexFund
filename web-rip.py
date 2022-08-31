from typing import List
from datetime import datetime
import requests
from seleniumwire import webdriver  # Import from seleniumwire
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium_stealth import stealth
from selenium.webdriver import ActionChains

import m3u8_To_MP4
import json
import time

# Make browser open in background
options = webdriver.ChromeOptions()
options.add_argument("start-maximized")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("headless")
caps = DesiredCapabilities.CHROME
caps["goog:loggingPrefs"] = {"performance": "ALL"}
# Create the webdriver object
browser = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options,
    desired_capabilities=caps,
)
actionChains = ActionChains(browser)
stealth(
    browser,
    languages=["en-US", "en"],
    vendor="Google Inc.",
    platform="Win32",
    webgl_vendor="Intel Inc.",
    renderer="Intel Iris OpenGL Engine",
    fix_hairline=True,
)

import requests
import youtube_dl


def processLog(log):
    log = json.loads(log["message"])["message"]
    # print(log["method"])
    if "Network.response" in log["method"] and log.get("params", False):
        # print(log["params"])
        try:
            body = browser.execute_cdp_cmd(
                "Network.getResponseBody", {"requestId": log["params"]["requestId"]}
            )
        except:
            return None
        return body
        # return log["params"]


def get_show_playlist(tmdb_id, season, episode):
    url = f"https://www.2embed.to/embed/tmdb/tv?id={tmdb_id}&s={season}&e={episode}"
    browser.get(url)
    pending = True
    handle = browser.current_window_handle
    print(handle)
    while pending:
        try:
            pending = browser.find_element(By.XPATH, "//div[@id='content-pending']")
            if pending:
                try:
                    # pending.click()
                    button = pending.find_element(By.XPATH, "//div[@id='play-now']")
                    actionChains.move_to_element(button).click().perform()
                    # location = button.location
                    # browser.execute_script("arguments[0].click();", pending)
                    time.sleep(1)

                    browser.switch_to.window(handle)
                    # time.sleep(1 / 2)
                    # actionChains.move_to_element(button).click().perform()
                    # time.sleep(1)
                    # browser.execute_script("arguments[0].click();", pending)
                except Exception as e:
                    print("Issue", e)
                    time.sleep(3)
        except:
            time.sleep(3)
            break
    return browser.requests
    # responses = [processLog(log) for log in logs]
    # return responses


# def search():
#     print()
#
#
# # {'outtmpl': '%(id)s.%(ext)s'}


# if 'entries' in result:
#     # Can be a playlist or a list of videos
#     video = result['entries'][0]
# else:
#     # Just a video
#     video = result

# print(video)
# video_url = video['url']
# print(video_url)

if __name__ == "__main__":
    reqs = get_show_playlist(tmdb_id=126301, season=1, episode=1)
    for request in reqs:
        if request.response:
            print(
                request.url,
                request.response.status_code,
                request.response.headers["Content-Type"],
            )
    # print(r)
    # print(r)
    # ydl = youtube_dl.YoutubeDL()
    # with ydl:
    #     result = ydl.download(
    #         ["https://rabbitstream.net/44e35cd8-2cbe-4303-9c50-d3cc0a8c70ca"],
    #     )
    #     print(result)
    # get_show_base("The Challenge", 35)
    # m3u8_url = "https://b-g-ca-6.feetcdn.com:2223/v3-hls-playback/0f9839f631ff1854acba60da23a45c2567c4c7476848893b935798528a23c593f6250815cf2527762264a8eee014a32b9c3bc7f2d6549b32f9890d7af7c6ee25ed91432adf5cde1a3dc260eb27fade00fcc7d0b087806eb47d98d9322da34cd6b8c594f0af50857e33ec1e32da8be36d33afe01df9a828fdabfa40c792af2812e35786bd96e167bc51929ee742fab3a0a306b0926d6ef9daec12f2fb41d03377f415f4ce60c43f1e9d7b14a17757b61d0c53f178ad9db53543687e03d83e3670/720/index.m3u8"
    # m3u8_To_MP4.multithread_download(m3u8_url)
