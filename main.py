import settings
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount, MyPlexUser
from plexapi.library import Library
import re
import torrse
import json
from debrid import RealDebrid
from tqdm import tqdm

# from debrid import RealDebrid
from py1337x import py1337x
from difflib import SequenceMatcher
import trakt
from threading import Thread
import country_converter as coco
from jackett import Jackett

cc = coco.CountryConverter()
trakt.APPLICATION_ID = "101039"
RD = RealDebrid(api_key=settings.CONFIG["Debrid Services"]["Real Debrid"]["api_key"])
jack = Jackett(
    api_key=settings.CONFIG["Scraper Settings"]["Sources"]["jackett"]["api_key"]
)
PlexAccount = None


def preflight():
    library = False
    content = False
    debrid = False
    for type in settings.CONFIG["Library Services"]:
        if settings.CONFIG["Library Services"][type]["active"]:
            if len(settings.CONFIG["Library Services"][type]["users"]) > 0:
                library = True
                break
    for type in settings.CONFIG["Content Services"]:
        if settings.CONFIG["Content Services"][type]["active"]:
            if len(settings.CONFIG["Content Services"][type]["users"]) > 0:
                content = True
                break
    for type in settings.CONFIG["Debrid Services"]:
        if settings.CONFIG["Debrid Services"][type]["active"]:
            if settings.CONFIG["Debrid Services"][type].get("api_key", False):
                debrid = True
                break
    # True means ready to run
    if library and content and debrid:
        return True
    return False


def library_collection(library):

    if library.lower() == "plex":
        for user in settings.CONFIG["Library Services"][library]["users"]:
            print("Starting Plex Library check for", user["name"])
            plex_server = PlexServer(
                baseurl=settings.CONFIG["Library Services"][library]["server_location"],
                token=user["token"],
            )
            # return plex_server.library.all()
            return plex_server.library


def content_collection(type):
    watchlists = []
    global PlexAccount
    if type.lower() == "plex":
        for user in settings.CONFIG["Content Services"][type]["users"]:
            print("Starting Plex watchlisht check for", user["name"])
            PlexAccount = MyPlexAccount(token=user["token"])
            return PlexAccount.watchlist(filter="released", unwatched="True")
            # watchlists.extend(plex.watchlist())
    #         for w in watchlist:
    #             print(w.title, w.type, w.year, w.guid.split("/")[-1])
    # # Convert to plex ids to easily diff later
    # # if type.lower() == "trakt":
    # #     print(settings.CONFIG["Content Services"][type].keys())
    # #     for user in settings.CONFIG["Content Services"][type]["users"]:
    # #         try:
    # #             trakt.init(user["pin"])
    # #             for l in trakt.lists:
    # #                 print(l)
    # #         except Exception as e:
    # #             print(e)
    # #             continue

    return watchlists


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def compare_names(name1, name2):
    name1 = re.sub(r"[\s\_\-\.\(\)\'\"\n\:]", "", name1.strip())
    name2 = re.sub(r"[\s\_\-\.\(\)\'\"\n\:]", "", name2.strip())
    if name1.lower() == name2.lower():
        return 3

    sub_score = similar(name1.lower(), name2.lower())
    if sub_score > 0.90:
        # print("90% but skipping", name1.lower(), name2.lower())
        return 0
        return 2
    if name1.lower().startswith(name2.lower()):
        # print("starts with but skipping", name1.lower(), name2.lower())
        return 0
        return 1
    return 0
    if sub_score > 0.50:
        return sub_score
    print(sub_score)
    return 0


def show_classify(title, target_title, get_score=True):

    m1 = settings.RE_TV_SHOW.search(title)
    m2 = settings.RE_RESOLUTION.search(title)

    seasons = []
    episodes = []
    resolution = 0
    file_name = title
    complete = False
    need_episodes = True
    if m1:
        if m1.group(1):
            file_name = m1.group(1)

        if m1.group(2):
            if m1.group(2) == "00":
                seasons = []
            elif "-" in m1.group(2):
                s_temp = m1.group(2).split("-")
                seasons = [int(s.lstrip("0")) for s in s_temp]
            else:
                seasons = [int(m1.group(2).lstrip("0"))]
        if m1.group(3):
            if m1.group(3).strip().lower() in ["complete", "crr"]:
                # print("found real complete", m1.group(3).strip().lower())
                complete = True
        if m1.group(4) and need_episodes:
            if m1.group(4) == "00":
                episodes = []
            elif "-" in m1.group(4):
                e_temp = m1.group(4).split("-")
                episodes = [int(e.lstrip("0")) for e in e_temp]
            else:
                episodes = [int(m1.group(4).lstrip("0"))]
        # still playing with the best way to do this
        elif len(seasons) > 0:
            complete = True

    if m2:
        if m2.group(1):
            resolution = settings.RESOLUTION_SCORE.get(m2.group(1).upper(), 0)
    if get_score:
        score = compare_names(file_name, target_title)
    else:
        score = 4
    # if "custom" in title.lower():
    #     score -= 2
    return file_name, seasons, episodes, resolution, score, complete


# will eventually integrate max/min resolution checjk here
def torrent_decision_tree(items, media, type="show"):
    # todo add movie
    media["available_sources"] = []
    if type in ["episode", "season", "show"]:
        for item in items:
            get_score = True
            if (media["ids"].get("imdb", "01") == item.get("Imdb", "00")) or (
                media["ids"].get("tmdb", "01") == item.get("TMDb", "00")
            ):
                get_score = False
            file_name, seasons, episodes, resolution, score, complete = show_classify(
                item["Title"], media["title"], get_score=get_score
            )
            if media["season"] not in seasons:
                # print("wrong seasons", media["season"], "-", seasons)
                continue
            if not complete and media["episode"] not in episodes:
                # print("no episode", media["episode"], "-", episodes)
                continue
            if score == 0:
                # print(
                #     "Scored too low:",
                #     score,
                #     "\nSkipping",
                #     item["Title"],
                #     "compared to",
                #     media["title"],
                # )
                continue
            if resolution < settings.MINIMUM_RESOLUTION:
                print("Skipping low res")
                continue

            if item.get("Link", False):
                link = item["Link"]

            elif item.get("MagnetUri", False):
                link = item["MagnetUri"]
            if link.startswith("magnet"):
                link_type = "magnet"
            else:
                link_type = "file"
            aggregate_score = score + resolution
            if complete:
                aggregate_score += 3

            media["available_sources"].append(
                {
                    "link": link,
                    "link_type": link_type,
                    "score": score,
                    "resolution": resolution,
                    "torrent_name": file_name,
                    "complete": complete,
                    "aggregate_score": aggregate_score,
                }
            )
            # eventually rework to make this seasons without episodes
            # if complete and media["season"] in seasons:
            #     if (
            #         not media.get("link", False)
            #         or media.get("resolution", -1) < resolution
            #         or media.get("score", -1) < score
            #         or not media.get("complete_season", False)
            #     ):
            #         if item.get("Link", False):
            #             media["link"] = item["Link"]
            #             media["link_type"] = "file"
            #         elif item.get("MagnetUri", False):
            #             media["link"] = item["MagnetUri"]
            #             media["link_type"] = "magnet"
            #         if media["link"].startswith("magnet"):
            #             media["link_type"] = "magnet"
            #         media["score"] = score
            #         media["resolution"] = resolution
            #         media["torrent_name"] = file_name
            #         media["complete_season"] = complete
            #         continue
            # elif media["episode"] in episodes and media["season"] in seasons:
            #     if (
            #         not media.get("link", False)
            #         or media.get("resolution", -1) < resolution
            #         or media.get("score", -1) < score
            #         or not media.get("complete_season", False)
            #     ):
            #         if item.get("Link", False):
            #             media["link"] = item["Link"]
            #             media["link_type"] = "file"
            #         elif item.get("MagnetUri", False):
            #             media["link"] = item["MagnetUri"]
            #             media["link_type"] = "magnet"
            #         if media["link"].startswith("magnet"):
            #             media["link_type"] = "magnet"
            #         media["score"] = score
            #         media["resolution"] = resolution
            #         media["torrent_name"] = file_name
            #         media["complete_season"] = complete
            #         continue
        return media


def get_watchlist_thread():
    print("Starting watchlist(s) collection")
    needs_to_be_collected = []
    for content in settings.CONFIG["Content Services"]:
        if settings.CONFIG["Content Services"][content]["active"] and len(
            settings.CONFIG["Content Services"][content]["users"]
        ):
            data = content_collection(content)
            needs_to_be_collected.extend(data)
    return needs_to_be_collected


def get_library_thread():
    needed = True
    all = []
    for library in settings.CONFIG["Library Services"]:
        if settings.CONFIG["Library Services"][library]["active"] and len(
            settings.CONFIG["Library Services"][library]["users"]
        ):
            all.extend(library_collection(library))

    return all


def get_needed(watchlist, library):
    final_content = []
    for m in watchlist:
        ids = {}
        for g in m.guids:
            ls = settings.RE_GUIDS.search(g.id)
            if ls:
                ids[str(ls.group(1))] = str(ls.group(2))
        if m.type == "show":

            for season in m.seasons():
                if season.index == 0:
                    continue
                PlexAccount._toOnlineMetadata([season])
                if season.isPlayed:
                    continue
                for ep in season.episodes():
                    # look into why this works later bc this was luck lol
                    if len(library.search(guid=ep.guid, libtype="episode")) == 0:
                        final_content.append(
                            {
                                "type": ep.type,
                                "season": ep.parentIndex,
                                "episode": ep.index,
                                "title": ep.grandparentTitle,
                                "query": f"{ep.grandparentTitle} S{ep.parentIndex:02d}E{ep.index:02d}",
                                "season_query": f"{ep.grandparentTitle} S{ep.parentIndex:02d}",
                                "ids": ids,
                            }
                        )

        if m.type == "movie":
            if len(library.search(guid=m.guid, libtype=m.type)) == 0:
                final_content.append(
                    {
                        "year": m.year,
                        "type": m.type,
                        "title": m.title,
                        "query": f"{str(m.title)} {str(m.year)}",
                        "ids": ids,
                    }
                )
    return final_content


def remove_watched():
    for media in library_collection("Plex").search(watched=True):
        if media.type == "episode":
            print("delete (will need an easy way to lookup)")


def attempt_and_collect(sources):
    print("starting RD collect")
    sources = sorted(sources, key=lambda d: d["aggregate_score"], reverse=True)
    for source in sources:
        try:
            print(source["aggregate_score"])
            torrent_id = None
            if source.get("link", False):
                if source["link_type"] == "magnet":
                    torrent_id = RD.add_magnet(source["link"])
                    print(torrent_id)
                if source["link_type"] == "file":
                    print("Torrent file")
                    file_data = jack.get_torrent_file(source["link"])
                    torrent_id = RD.add_torrent(file_data)
                    print(torrent_id)
        except Exception as e:
            print(e)
            continue
        if torrent_id:
            RD.select_torrent_files(torrent_id)
            return True
    return False


def main():
    if not preflight():
        print("Setup not built yet")
    library_threads = []
    content_threads = []
    magnets = set()
    watchlist_data = content_collection("Plex")
    library = library_collection("Plex")
    content_tracker = get_needed(watchlist_data, library)
    titles_collected = []
    seasons_checked = []

    # threadpool for this isntead
    for data in tqdm(content_tracker):
        print("starting", data["query"])
        if data["type"] == "episode":
            cat = 5000
        if data["type"] == "movie":
            cat = 2000
            continue
        try:
            if data["type"] == "episode":
                found = False
                if (
                    data["season_query"] in titles_collected
                    or data["query"] in titles_collected
                ):
                    print("Skipping", data["query"])
                    print(titles_collected)
                    continue
                if data["season_query"] not in seasons_checked:

                    response = jack.search(query=data["season_query"], categories=[cat])
                    if len(response) > 0:
                        data = torrent_decision_tree(response, data, type=data["type"],)
                        if len(data.get("available_sources", [])) > 0:
                            if attempt_and_collect(data["available_sources"]):
                                titles_collected.append(data["season_query"])
                                seasons_checked.append(data["season_query"])
                                found = True
                        seasons_checked.append(data["season_query"])
                if not found:
                    response = jack.search(query=data["query"], categories=[cat])
                    if len(response) > 0:
                        data = torrent_decision_tree(response, data, type=data["type"],)
                        if len(data.get("available_sources", [])) > 0:
                            if attempt_and_collect(data["available_sources"]):
                                found = True
                                titles_collected.append(data["query"])
        except Exception as e:
            print(e)
            continue

    print("Attempting library update")
    library.update()
    # with open("torrent_cache.json", "w") as f:
    #     json.dump(content_tracker, f, indent=4)


if __name__ == "__main__":
    main()
