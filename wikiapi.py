# -*- coding: utf-8 -*-
import requests
import json


def move(session, api_url, fromPage, toPage):
    token = session.get(api_url, params={'format': 'json', 'action': 'query', 'meta': 'tokens', })
    post_data = {'format': 'json', 'action': 'move', 'from': fromPage, 'to': toPage, 'noredirect': True, 'token': token.json()['query']['tokens']['csrftoken']}
    r = session.post(api_url, data=post_data)
    return r

def read_wiki(session, api_url, title):
    res = session.post(api_url, data={'format': 'json', 'action': 'query', 'assert': 'user', 'titles': title, 'prop': 'revisions', 'rvprop': 'content'})
    
    ret = json.loads(res.text)['query']['pages']
    for k in ret:
        ret = ret[k]
        break
    
    return ret["revisions"][0]["*"]

def read_wiki_exist(session, api_url, title, num_trial=3):
    for attempt in range(num_trial):
        try:
            res = session.post(api_url, data={'format': 'json', 'action': 'query', 'assert': 'user', 'titles': title})

            ret = json.loads(res.text)['query']['pages']
            if '-1' in ret:
                return False
            else:
                return True
        except:
            if attempt < num_trial - 1:
                print("Error: Read {} Fail. Try again.".format(title))
            else:
                raise RuntimeError(res.text)
    return None


def read_wiki_repeat(session, api_url, title, num_trial=5):
    for attempt in range(num_trial):
        try:
            res = session.post(api_url, data={'format': 'json', 'action': 'query', 'assert': 'user', 'titles': title, 'prop': 'revisions', 'rvprop': 'content'})
            
            ret = json.loads(res.text)['query']['pages']
            for k in ret:
                ret = ret[k]
                break
            return ret["revisions"][0]["*"]
        except:
            if attempt < num_trial - 1:
                print("Error: Read {} Fail. Try again.".format(title))
            else:
                raise RuntimeError(res.text)
    return None

def write_wiki(session, api_url, title, text, summary, **others):
    num_trial = 3
    for attempt in range(num_trial):
        try:
            token = session.get(api_url, params={'format': 'json', 'action': 'query', 'meta': 'tokens', })
            post_data = {'format': 'json', 'action': 'edit', 'assert': 'user', 'text': text, 'summary': summary, 'title': title,
                         'token': token.json()['query']['tokens']['csrftoken'], 'bot': 1}
            for k in others:
                post_data[k] = others[k]
            r = session.post(api_url, data=post_data)
            # print(r.text)
            return
        except:
            if attempt < num_trial - 1:
                print("Error: Write {} Fail. Try again.".format(title))
            else:
                raise RuntimeError
    return None

def write_wiki_minor(session, api_url, title, text, summary, **others):
    num_trial = 3
    for attempt in range(num_trial):
        try:
            token = session.get(api_url, params={'format': 'json', 'action': 'query', 'meta': 'tokens', })
            post_data = {'format': 'json', 'action': 'edit', 'assert': 'user', 'text': text, 'summary': summary, 'title': title,
                         'token': token.json()['query']['tokens']['csrftoken'], 'minor': 1}
            for k in others:
                post_data[k] = others[k]
            r = session.post(api_url, data=post_data)
            # print(r.text)
            return
        except:
            if attempt < num_trial - 1:
                print("Error: Write {} Fail. Try again.".format(title))
            else:
                raise RuntimeError
    return None


def login_wiki(username, password, api_url):
    session = requests.Session()
    lgtoken = session.get(api_url, params={'format': 'json', 'action': 'query', 'meta': 'tokens', 'type': 'login',})
    
    lgtoken.raise_for_status()
    res = session.post(api_url, data={'format': 'json', 'action': 'login', 'lgname': username, 'lgpassword': password,
                                      'lgtoken': lgtoken.json()['query']['tokens']['logintoken'],})
    if res.json()['login']['result'] != 'Success':
        raise RuntimeError(res.json()['login']['reason'])
        
    return session
