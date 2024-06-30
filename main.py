import os
import re
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


def get_raindrops(collection_id, token):
    url = "https://api.raindrop.io/rest/v1"
    endpoint = "/raindrops"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    query = {
        "perpage": 50,
    }

    r = requests.get(
        f"{url}{endpoint}/{collection_id}",
        headers=headers,
        params=query,
    )

    if r.status_code != requests.codes.ok:
        print(r.text)
        exit()

    time.sleep(1)
    return r


def fetch_tagged_raindrops(items, tags, has_tag=True):
    filtered_items = []
    for item in items:
        for tag in item["tags"]:
            if tag in tags:
                filtered_items.append(item)

    if has_tag:
        return filtered_items
    else:
        return [item for item in items if item["_id"] not in [fi["_id"] for fi in filtered_items]]


def tag_raindrop(items, collection, tag, token):
    url = "https://api.raindrop.io/rest/v1"
    endpoint = "/raindrops"

    tags = [tag]
    resp = requests.put(
        f"{url}{endpoint}/{collection}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        params={"perpage": 50},
        json={
            "ids": items,
            "collectionId": collection,
            "tags": tags,
        },
    )

    if resp.status_code != requests.codes.ok:
        print(resp.text)
        exit(1)

    time.sleep(1)
    return resp


def create_raindrop(items, collection_id, access_token):
    url = "https://api.raindrop.io/rest/v1"
    endpoint = "/raindrops"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    query = {
        # "sort": "domain",
        # "page": 1,
        "perpage": 50,
        # "dengerAll": True,
    }

    for item in items:
        item["collectionId"] = collection_id
    body = {"items": items}

    resp = requests.post(
        f"{url}{endpoint}",
        headers=headers,
        params=query,
        json=body,
    )

    if resp.status_code != requests.codes.ok:
        print(resp.text)
        exit(1)

    time.sleep(1)
    return resp


def to_kmn_url(link, service):
    user_id = None
    if "fantia" in service:
        user_id = link.split("/")[-1]
        key = "fantia"
    elif "patreon" in service:
        user_id = link.split("=")[-1]
        key = "patreon"
    elif "fanbox" in service:
        r = requests.get(link)
        soup = BeautifulSoup(r.text, "html.parser")
        meta = soup.find("meta", property="og:image")
        user_id = None
        if len(meta["content"].split("/")) < 9:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(link)
                page.get_by_role("button", name=re.compile("はい", re.IGNORECASE)).click()
                c = page.content()
                s = BeautifulSoup(c, "html.parser")
                user_id = (
                    list(
                        s.find_all(
                            "div",
                            style=lambda value: value and "background-image:" in value,
                        )
                    )[0]["style"]
                    .split('"')[1]
                    .split("/")[9]
                )
                page.screenshot(path="hogehgoehoge.png")
                browser.close()
        else:
            user_id = meta["content"].split("/")[9]
        print(user_id)
        key = "fanbox"

    else:
        return None

    resp = requests.get(f"https://www.kemono.su/{key}/user/{user_id}")
    time.sleep(1)
    return resp


def is_exist_kmn(url):
    if "https://www.kemono.su/artists" == url:
        print("There is no user pages in kemono")
        return False
    else:
        return True


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("RD_TOKEN")
    subscribe = int(os.getenv("SUBSCRIBE"))  # collection_id
    kmn_subscribe = int(os.getenv("KMN"))

    resp = get_raindrops(subscribe, token)
    items = resp.json()["items"]
    tags = ["fansite_notfound", "fansite_marked"]
    items = fetch_tagged_raindrops(items, tags, has_tag=False)
    if len(items) == 0:
        exit("No new item")

    # Get support site raindrops
    marked_id = []
    not_found_id = []
    kmn_id = []
    for item in items:
        domain = item["domain"]
        if (
            ("fanbox" not in domain)
            and ("fantia" not in domain)
            and ("patreon" not in domain)
        ):
            print("not supported site found")
            continue

        r = to_kmn_url(item["link"], domain)
        if not is_exist_kmn(r.url):
            not_found_id.append(item["_id"])
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title").text
        kmn_id.append(
            {
                "link": r.url,
                "title": title,
            }
        )
        marked_id.append(item["_id"])
        print(title)
    
    if marked_id:
        r = tag_raindrop(marked_id, subscribe, "fansite_marked", token)
    if not_nound_id:
        r = tag_raindrop(not_found_id, subscribe, "fansite_notfound", token)
    if kmn_id:
        r = create_raindrop(kmn_id, kmn_subscribe, token)
