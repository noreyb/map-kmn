import os
import random
import re
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from raindropio.domain.raindrop import Raindrop
from raindropio.domain.raindrop_id import RaindropId
from raindropio.repository.raindropio import RaindropIO


def id_in_fantia(link):
    return link.split("/")[-1]

def id_in_fanbox(link):
    r = requests.get(link)

    user_id = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(link)

        try:
            yes_button = page.get_by_role("button", name=re.compile("はい", re.IGNORECASE))
            if yes_button.is_visible():
                yes_button.click()
        except TimeoutError:
            print("No confirm button")


        content = page.content()
        soup = BeautifulSoup(content, "html.parser")

        divs = soup.find_all("div", style=True)
        for d in divs:
            if "background-image" in d["style"]:
                user_id = d['style'].split('\"')[1].split('/')[9]
                break

        browser.close()
    return user_id

def id_in_patreon(link):
    return link.split("=")[-1]  # これとユーザー名verのurlがある


def to_kmn_url(link, service):
    user_id = None

    if "fantia" in service:
        user_id = id_in_fantia(link)
        key = "fantia"

    elif "patreon" in service:
        user_id = id_in_patreon(link)
        key = "patreon"

    elif "fanbox" in service:
        user_id = id_in_fanbox(link)
        key = "fanbox"

    else:
        return None

    if user_id is None:
        return None

    resp = requests.get(f"https://kemono.su/{key}/user/{user_id}")
    time.sleep(1)

    url = resp.url
    # soup = BeautifulSoup(resp.text, "html.parser")
    # title = soup.find("title").text

    return url


def is_exist_kmn(url):
    if "https://kemono.su/artists" == url:
        print("There is no user pages in kemono")
        return False
    else:
        return True


def raindrops_without_specific_tags(raindrops: list, tags: list):
    result = []
    for r in raindrops:
        for t in tags:
            if t not in r.tags:
                result.append(r)

    return result


if __name__ == "__main__":
    # 変数設定
    load_dotenv()
    token = os.getenv("RD_TOKEN")
    fansite = int(os.getenv("FANSITE"))  # collection_id
    kmn_subscribe = int(os.getenv("KEMONO"))  # collection_id

    # Raindropのハンドラーを設定
    handler = RaindropIO(token)
    raindrops = handler.bulk_get_all(fansite)

    # 特定のタグがないraindropを取得
    tags = ["fansite_notfound", "fansite_marked"]
    raindrops = raindrops_without_specific_tags(raindrops, tags)
    # items = fetch_tagged_raindrops(items, tags, has_tag=False)
    if len(raindrops) == 0:
        raise Exception("No new item")

    # Get support site raindrops
    # support_sites = ["fanbox", "fantia", "patreon"]
    support_sites = ["fanbox", "fantia"]  # patreonのidを安定して取得する方法がわかるまで除く
    marked_raindrops = []
    notfound_raindrops = []
    kmn_raindrops = []
    for r in raindrops:

        # 対応外のサイトはスキップする
        for s in support_sites:
            if s not in r.link:
                continue

        for s in support_sites:
            if s in r.link:
                domain = s
        kmn_url = to_kmn_url(r.link, domain)

        if kmn_url is None:
            continue

        # Raindrop に詰めなおす
        tmp = Raindrop(
            link = r.link,
            _id = RaindropId(r._id),
        )
        if not is_exist_kmn(kmn_url):
            notfound_raindrops.append(tmp)
            print(f"notfound: {kmn_url}")
            continue
        else:
            marked_raindrops.append(tmp)
            print(f"marked: {kmn_url}")

        kmn_raindrops.append(
            Raindrop(
                link = kmn_url,
                collection_id = kmn_subscribe,
            )
        )

        time.sleep(1)

    if marked_raindrops:
        # r = tag_raindrop(marked_id, subscribe, "fansite_marked", token)
        handler.bulk_update(fansite, marked_raindrops, ["fansite_marked"], fansite)
    if notfound_raindrops:
        # r = tag_raindrop(not_found_id, subscribe, "fansite_notfound", token)
        handler.bulk_update(fansite, notfound_raindrops, ["fansite_notfound"], fansite)
    if kmn_raindrops:
        # r = create_raindrop(kmn_id, kmn_subscribe, token)
        handler.bulk_create(kmn_raindrops)

