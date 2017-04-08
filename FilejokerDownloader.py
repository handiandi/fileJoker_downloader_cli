#!/usr/bin/env python3
import sys
import os
import requests
import re
from collections import defaultdict
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter


def login(email, pwd, url, path):
    s = requests.Session()
    s.post('https://filejoker.net/login',
           data={'email': email,
                 'op': 'login',
                 'password': pwd,
                 'rand': '',
                 'redirect': ''})
    values = find_values(s.get(url).text)
    link = find_download_link(s.post(url, data=values).text)
    filename = link[link.rfind("/")+1:]
    r = s.get(link, stream=True)
    total_length = r.headers.get('content-length')
    total_length = int(total_length)
    dl = 0
    if r.status_code == 200:
        with open(path+filename, 'wb') as f:
            for chunk in r.iter_content(1024):
                if chunk:
                    dl += len(chunk)
                    f.write(chunk)
                    done = int(50 * dl / total_length)
                    sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)))
                    sys.stdout.flush()
    sys.stdout.write("\n")


def find_download_link(s):
    goal = '<div class="premium-download">'
    result = [m.start() for m in re.finditer(goal, s)][0]
    result2 = [m.start() for m in re.finditer('" class', s[result:])][0]
    return s[result+len(goal)+10:result+result2]


def find_values(s):
    result = [m.start() for m in re.finditer('<input', s)]
    values = defaultdict(dict)
    for i, index in enumerate(result):
        substring = s[index:] if i == len(result)-1 else s[index:result[i+1]]
        value_index = [m.start() for m in re.finditer('value="', substring)][0]
        name_index = [m.start() for m in re.finditer('name="', substring)][0]
        name = substring[name_index+6:substring[name_index+6:].find('"') +
                         name_index+6]
        value = substring[value_index+7:substring[value_index+7:].find('"') +
                          value_index+7]
        values[name] = value
    return values


if __name__ == '__main__':
    arg_parser = ArgumentParser(description='CLI for premium download for FileJoker.net',
                                formatter_class=RawTextHelpFormatter)
    arg_parser.add_argument("-e", "--email", dest="email", metavar="STRING",
                            help="Email for login")
    arg_parser.add_argument("-p", "--pass", dest="pwd", metavar="STRING",
                            help="Password for login")
    arg_parser.add_argument("-l", "--link", metavar="STRING",
                            dest="link", help="FileJoker download link")
    arg_parser.add_argument("-path", "--path", metavar="STRING",
                            dest="path", help="Relative path for saving file (an already created directory)")
    base_path = os.path.realpath(__file__)
    base_path = base_path[:base_path.rfind("/")+1]
    save_path_relative = None
    save_path = None
    args = arg_parser.parse_args()
    if args.email is None:
        arg_parser.error("Missing email for login")
    if args.pwd is None:
        arg_parser.error("Missing password for login")
    if args.link is None:
        arg_parser.error("Missing download link for login")
    if args.path is not None:
        if args.path[0] == "/":
            save_path = base_path + args.path[1:]
        else:
            save_path = base_path + args.path
        if not os.path.exists(save_path):
            print("Path doesn't exist: {}".format(save_path))
        elif not os.path.isdir(save_path):
            print("Path is not a directory!: {}".format(save_path))
        if save_path[-1] != "/":
            save_path += "/"
    else:
        save_path = base_path

    login(args.email, args.pwd, args.link, save_path)
