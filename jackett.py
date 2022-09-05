import requests
import urllib.parse
import time


class Jackett:
    def __init__(self, api_key, base_url="http://localhost:9117"):
        self.api_key = api_key
        self.base_url = base_url

    def search(self, query, categories=[2000, 5000]):
        cat_string = ""
        for c in categories:
            cat_string += "&Category%5B%5D=" + str(c)
        response = requests.get(
            f"{self.base_url}/api/v2.0/indexers/all/results?apikey={self.api_key}&Query={urllib.parse.quote_plus(query)}{cat_string}&_={str(int(time.time()))}"
        )
        if response.status_code != 200:
            print("Unknown error:", response.status_code)
            return []
        return response.json()["Results"]

    def get_torrent_file(self, url, save_path=None):
        return requests.get(url).content


if __name__ == "__main__":
    j = Jackett(api_key="")
    data = j.search("The Challenge: All Stars S02", categories=[5000])
    for res in data:
        print(res["Title"])
        if res["MagnetUri"] or res["Link"]:
            if res["Link"]:
                print("link", res["Link"], "\n")
            if res["MagnetUri"]:
                print("magnet", res["MagnetUri"], "\n")
