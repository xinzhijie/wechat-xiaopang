# -*- coding: utf-8 -*-

import json
import requests


class Music(object):
    def __init__(self) -> None:
        pass

    def getMusic(self, cy: str) -> str:
        cyList = cy.split("-")
        if len(cyList) == 1:
            cyList = (cy + "-").split("-")
        url = "https://service-2j4s0ber-1257248029.bj.apigw.tencentcs.com/search?keywords=" + cyList[0][1:]
        rsp = requests.get(url=url, headers=None, data=None)
        songsList = json.loads(rsp.text)["result"]["songs"]
        num = 0
        for i in range(len(songsList)):
            if songsList[i]["artists"][0]["name"] == cyList[1]:
                num = i
                break

        songsId = json.loads(rsp.text)["result"]["songs"][num]["id"]
        result = "https://service-2j4s0ber-1257248029.bj.apigw.tencentcs.com/song/url?id=" + str(songsId)
        rsp2 = requests.get(url=result, headers=None, data=None)
        url = cy + "----" + json.loads(rsp2.text)["data"][0]["url"]
        url = cyList[0][1:] + "\n https://music.163.com/#/song?id=" + str(songsId) + "&thirdfrom=baidualading&market=playlist"
        return url


music = Music()

if __name__ == "__main__":
    answer = music.getMusic("#无感")
    print(answer)
