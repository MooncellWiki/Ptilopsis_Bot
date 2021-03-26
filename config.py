config = {
    'api_url': 'http://prts.wiki/api.php',
    'username': 'botPtilopsis',
    'password': 'netVyc-3zurba-vupcow',
    # 'source': 'unpacker',
    'source': 'repo',
    'unpacker': {
        "serverList": {
            "cn": {
                "folder": "zh_CN",
                "updateMsg": "[CN UPDATE] Client:{0} Data:{1}",
                "tableSign": True,
                "luaSign": True,
                "url": "https://ak-hu.hycdn.cn/assetbundle/official/Android/",
                "baseUrl": "https://ak-conf.hypergryph.com/config/prod/official/Android/",
                "chatMask": "UITpAi82pHAWwnzqHRMCwPonJLIB3WCl"
            },
            "jp": {
                "folder": "ja_JP",
                "updateMsg": "[JP UPDATE] Client:{0} Data:{1}",
                "tableSign": True,
                "luaSign": True,
                "url": "https://ark-jp-static-online.yo-star.com/assetbundle/official/Android/",
                "baseUrl": "http://ark-jp-static-online.yo-star.com/assetbundle/official/Android/",
                "chatMask": "8OjXUSNSi8yXC0u98mNWvh7MRLGhyEuQ"
            },
            "us": {
                "folder": "en_US",
                "updateMsg": "[EN UPDATE] Client:{0} Data:{1}",
                "tableSign": True,
                "luaSign": True,
                "url": "https://ark-us-static-online.yo-star.com/assetbundle/official/Android/",
                "baseUrl": "http://ark-us-static-online.yo-star.com/assetbundle/official/Android/",
                "chatMask": "8OjXUSNSi8yXC0u98mNWvh7MRLGhyEuQ"
            },
            "kr": {
                "folder": "ko_KR",
                "updateMsg": "[KR UPDATE] Client:{0} Data:{1}",
                "tableSign": True,
                "luaSign": True,
                "url": "https://ark-kr-static-online-1300509597.yo-star.com/assetbundle/official/Android/",
                "baseUrl": "http://ark-kr-static-online-1300509597.yo-star.com/assetbundle/official/Android/",
                "chatMask": "8OjXUSNSi8yXC0u98mNWvh7MRLGhyEuQ"
            },
            "tw": {
                "folder": "zh_TW",
                "updateMsg": "[TC UPDATE] Client:{0} Data:{1}",
                "tableSign": False,
                "luaSign": True,
                "url": "https://akcdn.imtxwy.com/assetbundle/official/Android/",
                "baseUrl": "http://akcdn.imtxwy.com/assetbundle/official/Android/",
                "chatMask": "8OjXUSNSi8yXC0u98mNWvh7MRLGhyEuQ"
            }
        }
    },
    "repo": "https://github.com/Kengxxiao/ArknightsGameData.git"
}
