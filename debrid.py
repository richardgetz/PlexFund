import requests
import time
import dateutil.parser
from datetime import timedelta
from plexapi.server import PlexServer
import settings
import re


class RealDebrid:
    def __init__(self, api_key):

        # (required) Name of the Debrid service
        self.name = "Real Debrid"
        self.short = "RD"
        # (required) Authentification of the Debrid service, can be oauth aswell. Create a setting for the required variables in the ui.settings_list. For an oauth example check the trakt authentification.
        self.api_key = api_key
        # Define Variables
        self.session = requests.Session()
        self.base_url = "https://api.real-debrid.com/rest/1.0"
        self.downloads = []
        self.sess = requests.Session()
        self.sess.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
            "authorization": "Bearer " + self.api_key,
        }

    def auto_cleanup(self, start_page=1):
        deleted = []
        while True:
            torrents = self.get_torrents(start_page)
            if len(torrents) == 0:
                print("No more pages")
                return deleted
            for t in torrents:
                if t["status"] == "waiting_files_selection":
                    print("Select files for", t["id"])
                    self.select_torrent_files(t["id"])
                elif t["status"] == "magnet_conversion":
                    if (
                        dateutil.parser.parse(t["added"]) + timedelta(hours=2)
                    ).timestamp() <= time.time():
                        print("Magnet conversion for more than two hours", t["id"])
                        self.delete_torrent(t["id"])
                        deleted.append(t["id"])
                elif t["status"] in ["error", "magnet_error"]:
                    print("Deleting", t["id"])
                    deleted.append(t["id"])
                    self.delete_torrent(t["id"])
                # elif t["status"] == "downloaded":
                # print("Attempting unrestrict", t["id"])
                # for l in t.get("links", []):
                #     if self.unrestrict_link(l):
                #         unrestricted += 1
            start_page += 1
        return deleted

    def unrestrict_link(self, link, retry=3):
        count = 0
        while count < retry:
            time.sleep(0.5)
            response = self.sess.post(
                f"{self.base_url}/unrestrict/link", data={"link": link},
            )
            print(response.status_code)
            if response.status_code == 200:
                return True
            if response.status_code == 429:
                time.sleep(5)
            count += 1
        return False

    def select_torrent_files(self, id, files="video"):

        if files == "video":
            files = []
            info = self.get_torrent_info(id)
            for f in info["files"]:
                if f["path"].lower().startswith("/sample"):
                    continue
                if re.search(
                    r".*\.(mkv|mp4|asf|avi|mov|mpeg(?:ts)?|wmv)$",
                    f["path"],
                    flags=re.IGNORECASE,
                ):
                    files.append(str(f["id"]))
                    # print("Selecting", f["path"])
            # files = ",".join(files)
            # print("Selections", files)
        if files != "":
            response = self.sess.post(
                f"{self.base_url}/torrents/selectFiles/{id}",
                data={"files": files},
                timeout=10,
            )
        else:
            print("No valid files, deleting torrent")
            self.delete_torrent(id)
            return
        print(response.status_code)
        # I believe this 404 actually means there are none (supported) to select
        if response.status_code == 404:
            print("Unsupported, deleting", id)
            self.delete_torrent(id)

    # todo return and save id to lookup issues later
    def get_torrent_info(self, id):
        try:
            torrent_info = self.sess.get(f"{self.base_url}/torrents/info/{str(id)}",)
            return torrent_info.json()
        except:
            return None

    def add_magnet(self, magnet, retry_attempts=3):
        try:
            counter = 0
            while counter < retry_attempts:
                response = self.sess.post(
                    f"{self.base_url}/torrents/addMagnet", data={"magnet": magnet},
                )
                print(response.status_code)
                if str(response.status_code).startswith("2"):
                    return response.json()["id"]
                if response.status_code == 403:
                    print(response.reason)
                    return None
                else:
                    print(response.reason)
                    return None
                counter += 1
                time.sleep(0.2)

        except Exception as e:
            print(e)
        return None

    def add_torrent(self, data, retry_attempts=3):
        counter = 0
        while counter < retry_attempts:
            try:
                response = self.sess.put(
                    f"{self.base_url}/torrents/addTorrent", data=data,
                )
                print(response.status_code)
                if response.status_code == 201:
                    return response.json()["id"]
                if response.status_code == 403:
                    print(response.reason)
                    return None
                else:
                    print(response.reason)
                    return None
                time.sleep(0.5)
            except Exception as e:
                print(e)
            counter += 1
        return None

    def get_torrents(self, page=1):
        try:
            torrents = self.sess.get(f"{self.base_url}/torrents?page={page}")
            if torrents.status_code == 200:
                return torrents.json()
            print(torrents.status_code)

        except Exception as e:
            print(e)
            pass
        return []

    def delete_torrent(self, id):
        self.sess.delete(f"{self.base_url}/torrents/delete/{id}")


if __name__ == "__main__":
    import settings
    import json

    RD = RealDebrid(
        api_key=settings.CONFIG["Debrid Services"]["Real Debrid"]["api_key"]
    )
    # start_page = 1
    # while True:
    #     torrents = RD.get_torrents(start_page)
    #     if len(torrents) == 0:
    #         break
    #     for t in torrents:
    #         if t["status"] in [
    #             "waiting_files_selection",
    #             "queued",
    #             "downloading",
    #             "dead",
    #         ]:
    #             if "designated.survivor" in t["filename"].lower():
    #                 print("Deleting", t["filename"])
    #                 RD.delete_torrent(t["id"])
    #             # print(t["status"], t["filename"])
    #     start_page += 1
    # plex_server = PlexServer(
    #     baseurl=settings.CONFIG["Library Services"]["Plex"]["server_location"],
    #     token=settings.CONFIG["Content Services"]["Plex"]["users"][0]["token"],
    # )
    #
    start_time = time.time()
    while time.time() - start_time < (3600 * 5):
        print("Running auto clean for", time.time() - start_time)
        deleted = RD.auto_cleanup(start_page=1)
        print("Deleted:", deleted)
        # if unrestricted > 0:
        # print("Scaning library due to", unrestricted, "new links found.")
        #
        # plex_server.library.update()
        time.sleep(300)

    # waiting_files_selection, queued, downloading

    # torrents = RD.get_torrents(1)
    # print(torrents[0])
    # print(RD.get_torrent_info(torrents[0]["id"]))
    # with open("torrents.json", "w") as f:
    #     json.dump(torrents, f, indent=4)
    #  https://api.real-debrid.com/rest/1.0//hosts/domains
