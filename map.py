import os
import re
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


def get_from_raindrop(collection_id, access_token):
    url = "https://api.raindrop.io/rest/v1"
    endpoint = "/raindrops"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    query = {
        "perpage": 50,
    }

    resp = requests.get(
        f"{url}{endpoint}/{collection_id}",
        headers=headers,
        params=query,
    )

    if resp.status_code != requests.codes.ok:
        print(resp.text)
        exit()

    time.sleep(1)
    return resp


def move_marked_raindrop(unmark, items, marked, access_token):
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
    body = {
        "ids": items,
        "collectionId": marked,
    }

    resp = requests.put(
        f"{url}{endpoint}/{unmark}",
        headers=headers,
        params=query,
        json=body,
    )

    if resp.status_code != requests.codes.ok:
        print(resp.text)
        exit(1)

    time.sleep(1)
    return resp


def create_raindrop(collection_id, items, access_token):
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
    token = os.getenv("RAINDROPIO_ACCESS_TOKEN")
    unmark = int(os.getenv("UNMARK"))  # collection_id
    marked = int(os.getenv("MARKED"))
    notfound = int(os.getenv("NOTFOUND"))
    unmark_kmn = int(os.getenv("KMN"))

    resp = get_from_raindrop(unmark, token)
    if resp.json()["count"] == 0:
        print("There is no unmark raindrops")
        exit()

    # Get suppot site raindrops
    raindrops_to_marked = []
    raindrops_not_found = []
    raindrops_to_unmark_kmn = []
    for item in resp.json()["items"]:
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
            raindrops_not_found.append(item["_id"])
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title").text
        raindrops_to_unmark_kmn.append(
            {
                "link": r.url,
                "title": title,
            }
        )
        raindrops_to_marked.append(item["_id"])
        print(title)

    r = move_marked_raindrop(unmark, raindrops_to_marked, marked, token)
    r = move_marked_raindrop(unmark, raindrops_not_found, notfound, token)
    r = create_raindrop(unmark_kmn, raindrops_to_unmark_kmn, token)
