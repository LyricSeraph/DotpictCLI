#!/usr/bin/env python3
# coding=utf-8

import copy
import getopt
import hashlib
import json
import sys
import time

import requests

X_TOKEN = None
LAST_X_TOKEN_UPDATE = 0

TOKEN_CONFIG = {}
SAVED_ID_RECORDS = {}
NEW_SAVED_ID_RECORDS = {}
OUTPUT_DATA = []
COLLECTED_WORK_IDS = set()

TOKEN_CONFIG_FILENAME = "token-config.json"
OUTPUT_FILENAME = "output.json"
SAVE_FILENAME = "save.json"


def init():
    global TOKEN_CONFIG_FILENAME
    global SAVE_FILENAME
    global TOKEN_CONFIG
    global SAVED_ID_RECORDS
    global NEW_SAVED_ID_RECORDS

    with open(TOKEN_CONFIG_FILENAME) as f:
        TOKEN_CONFIG = json.load(f)
    try:
        with open(SAVE_FILENAME, "r") as f:
            SAVED_ID_RECORDS = json.load(f)
    except:
        SAVED_ID_RECORDS = {}
    NEW_SAVED_ID_RECORDS = copy.deepcopy(SAVED_ID_RECORDS)


def output():
    global NEW_SAVED_ID_RECORDS
    with open(SAVE_FILENAME, "w") as f:
        f.write(json.dumps(NEW_SAVED_ID_RECORDS))

    global OUTPUT_DATA
    with open(OUTPUT_FILENAME, "a+") as f:
        f.write(json.dumps(OUTPUT_DATA, ensure_ascii=False))
    return 1


def get_xtoken():
    global TOKEN_CONFIG
    global X_TOKEN
    global LAST_X_TOKEN_UPDATE
    if X_TOKEN is None or time.time() - LAST_X_TOKEN_UPDATE > 10:
        now_minute = int((time.time() - 10) / 60) * 60
        # print("now_minute: %d" % now_minute)
        content1 = TOKEN_CONFIG["prefix1"] + str(now_minute)
        content2 = TOKEN_CONFIG["prefix2"] + str(now_minute)
        # print("content: %s, %s" % (content1, content2))
        token1 = hashlib.md5(content1.encode()).hexdigest()
        token2 = hashlib.md5(content2.encode()).hexdigest()
        # print("token: %s, %s" % (token1, token2))
        LAST_X_TOKEN_UPDATE = time.time()
        X_TOKEN = {
            'X-TOKEN1': token1,
            'X-TOKEN2': token2
        }
    return X_TOKEN


def load_ids_from_file(filepath):
    with open(filepath, 'r') as f:
        return [line for line in f]


def get_by_user_ids_file(filepath):
    loaded_ids = load_ids_from_file(filepath)
    get_by_user_ids(loaded_ids)


def get_by_user_ids(ids):
    for i in ids:
        get_by_user_id(i)


def get_by_following_users(my_user_id):
    url = "https://api.dotpicko.net/v2/users/%s/followed?work_count=1" % my_user_id
    resp = requests.get(url, headers=get_xtoken())
    # print("result: " + resp.text)

    try:
        users = resp.json()['data']['user_summaries']
    except Exception as e:
        print("get_by_following_users error url: " + url + " content: " + resp.text, e)
        sys.exit(1)

    while len(users) > 0:
        user_ids = [str(u['user']['id']) for u in users]
        get_by_user_ids(user_ids)
        next_url = resp.json()['data']['next_url']
        resp = None
        while resp == None:
            try:
                resp = requests.get(next_url, headers=get_xtoken())
            except requests.exceptions.ConnectionError:
                print("encountered connection error, wait 60s for cooldown")
                time.sleep(60)
        users = resp.json()['data']['user_summaries']
        # print("result: " + resp.text)


def get_by_user_id(user_id):
    global SAVED_ID_RECORDS
    global NEW_SAVED_ID_RECORDS

    user_id = user_id.strip()
    id_greater_than = SAVED_ID_RECORDS[user_id] if user_id in SAVED_ID_RECORDS else 0
    new_max_id = id_greater_than

    print("processing user: %s" % str(user_id), end="", flush=True)
    request_max_id = 0
    total_count = 0
    while True:
        get_works_url = "https://api.dotpicko.net/users/%s/works" % user_id
        if request_max_id != 0:
            get_works_url = ("https://api.dotpicko.net/users/%s/works" % user_id) + ("?max_id=%d" % request_max_id)
        resp = None
        while resp is None:
            try:
                resp = requests.get(get_works_url, headers=get_xtoken())
            except requests.exceptions.ConnectionError:
                print("encountered connection error, wait 60s for cooldown")
                time.sleep(60)
        try:
            username = resp.json()['data']['user']['name']
            works = resp.json()['data']['works']
        except Exception as e:
            print("get_by_user_id error url: " + get_works_url + " content: " + resp.text, e)
            sys.exit(1)

        stop = False
        if len(works) != 0:
            for item in works:
                item_id = int(item['id'])
                if item_id <= id_greater_than:
                    stop = True
                    break;
                if item_id > new_max_id:
                    new_max_id = item_id
                get_by_user_id_work_id(user_id, username, str(item_id).strip(), item['title'], item['ogp_image_url'])
                request_max_id = item_id
                total_count += 1
        if len(works) == 0 or stop:
            break
        print(".", end="", flush=True)
        time.sleep(1)

    NEW_SAVED_ID_RECORDS[user_id] = new_max_id
    print("")
    print("total processed works for user %s(%s): %d, with max work id: %d" % (
        username, str(user_id), total_count, new_max_id))


def get_extension(url):
    last_dot = url.rfind(".")
    return url[last_dot:]


def get_by_user_id_work_id(user_id, username, work_id, title, url):
    global OUTPUT_DATA
    global COLLECTED_WORK_IDS
    get_extension(url)
    record = {
        "user_id": user_id,
        "user_name": username,
        "work_id": work_id,
        "title": title,
        "url": url
    }
    if work_id not in COLLECTED_WORK_IDS:
        COLLECTED_WORK_IDS.add(work_id)
        OUTPUT_DATA.append(record)
        # print("record: " + json.dumps(record))


def usage():
    print("""
usage: this_script.py <options>
options:
    --following-user-id=
        Get dotpic records with this user's following list. e.g. --following-user-id=123456
    --target-user-id=
        Get dotpic records uploaded by this user id. e.g. --target-user-id=123456
    --target-user-id-list-file=
        Get dotpic records by user id in the file row by row. e.g. --target-user-id-list-file=./userids.txt
    """)


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "", ["following-user-id=", "target-user-id-list-file=", "target-user-id="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        help()
        return 2

    my_user_id = ''
    target_user_id = ''
    target_user_id_list_file = ''
    for opt, arg in opts:
        if opt == '--following-user-id':
            my_user_id = arg
        elif opt == '-target-user-id-list-file':
            target_user_id_list_file = arg
        elif opt == '--target-user-id':
            target_user_id = arg
        else:
            assert False, "unhandled option"
    if my_user_id or target_user_id or target_user_id_list_file:
        init()
        if my_user_id:
            get_by_following_users(my_user_id)
        elif target_user_id:
            get_by_user_id(target_user_id)
        elif target_user_id_list_file:
            get_by_user_ids_file(target_user_id_list_file)
        output()
    else:
        usage()
        return 1
    return 0


if __name__ == '__main__':
    exit(main(sys.argv[1:]))
