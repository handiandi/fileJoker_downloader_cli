#!/usr/bin/env python3
import sys
import os
import requests
import re
from collections import defaultdict
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
import multiprocessing as mp
import time


def login_and_download(email, pwd, urls, file_w_urls, path):
    s = requests.Session()
    s.post('https://filejoker.net/login',
           data={'email': email,
                 'op': 'login',
                 'password': pwd,
                 'rand': '',
                 'redirect': ''})
    for count, url in enumerate(urls):
        page = s.get(url)
        values = find_values(page.text)
        size = find_size_of_file(page.text)
        if not check_for_free_disk_space(path, size):
            print("Not enough disk space")
            sys.exit(-1)
        html = s.post(url, data=values).text
        if reach_download_limit(html):
            print("You have reached your download limit. You can't download any more files right now. Try again later")
            sys.exit()
        link = find_download_link(html)
        filename = link[link.rfind("/")+1:]
        if len(urls) > 1:
            print("Downloading file '{}' [{}]- ({} of {} files in que)".
                  format(filename, values['id'],
                         count+1,
                         len(urls)))
        else:
            print("Downloading file '{}' [{}]".format(filename, values['id']))
        download(s, link, filename, path)
        if(file_w_urls):
            p = mp.Process(name="deleteID+"+str(count), target=delete_id_from_file,
                           args=(file_w_urls, values['id']))
            p.start()


def reach_download_limit(s):
    goal = 'You have reached your download limit:'
    if [m.start() for m in re.finditer(goal, s)]:
        return True
    return False


def download(session, url, filename, path):
    r = session.get(url, stream=True)
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
                    sys.stdout.write("\r[%s%s] - %d of %d MB (%d%%)" %
                                     ('=' * done, ' ' * (50-done),
                                      int(dl/1024/1024),
                                      int(total_length/1024/1024),
                                      done*2))
                    sys.stdout.flush()
    sys.stdout.write("\n")


def find_download_link(s):
    goal = '<div class="premium-download">'
    result = [m.start() for m in re.finditer(goal, s)][0]
    result2 = [m.start() for m in re.finditer('" class', s[result:])][0]
    return s[result+len(goal)+10:result+result2]


def find_size_of_file(s):
    size = defaultdict(dict)
    result = [m.start() for m in re.finditer('<div class="name-size">', s)][0]
    result2 = [m.start() for m in re.finditer('</div>', s[result:])][0]
    sub_string = s[result:(result+result2)]
    temp = sub_string[sub_string.find("<small>(")+8:
                      sub_string.find(")</small>")]
    size['size'] = float(temp[:-2].strip())
    size['size_value'] = temp[-2:].strip()
    return size


def find_values(s):
    result = [m.start() for m in re.finditer('<input', s)]
    values = defaultdict(dict)
    for i, index in enumerate(result):
        substring = s[index:] if i == len(result)-1 else s[index:result[i+1]]
        value_index = [m.start() for m in re.finditer('value="', substring)]
        if len(value_index) == 0:
            continue
        value_index = value_index[0]
        name_index = [m.start() for m in re.finditer('name="', substring)]
        if len(name_index) == 0:
            continue
        name_index = name_index[0]
        name = substring[name_index+6:substring[name_index+6:].find('"') +
                         name_index+6]
        value = substring[value_index+7:substring[value_index+7:].find('"') +
                          value_index+7]
        values[name] = value
    return values


def check_for_free_disk_space(path, size, ratio=0.6):
    disk = os.statvfs(path)
    totalAvailSpace = float(disk.f_bsize*disk.f_bfree)
    rules = {'b': totalAvailSpace,
             'kb': totalAvailSpace/1024,
             'mb': totalAvailSpace/1024/1024,
             'gb': totalAvailSpace/1024/1024/1024}
    if size['size'] / rules[size['size_value'].lower()] <= ratio:
        return True
    return False


def delete_id_from_file(file, fj_id):
    with open(file, 'r+') as f:
        d = f.read().splitlines()
        ids = [item[item.rfind('/')+1:] if item[-1] != '/'
               else item[item[:-1].rfind('/')+1:-1]
               for item in d]
        f.seek(0)
        [f.write("https://filejoker.net/"+i+"\n") if i != fj_id
         else None for i in ids]
        f.truncate()


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
    arg_parser.add_argument("-f", "--file", metavar="FILE",
                            dest="file", help="A text file with FileJoker links (one per line)")
    base_path = os.path.realpath(__file__)
    base_path = base_path[:base_path.rfind("/")+1]
    save_path_relative = None
    save_path = None
    args = arg_parser.parse_args()
    links = []
    if args.email is None:
        arg_parser.error("Missing email for login")
    if args.pwd is None:
        arg_parser.error("Missing password for login")
    if args.link is None and args.file is None:
        arg_parser.error("Missing download link (or links)")
    if args.file:
        with open(args.file, 'r') as f:
            links = f.read().splitlines()
            links = list(set(links))
    if args.link:
        links.append(args.link)
    if args.path is not None:
        if args.path[0] == "/":
            save_path = base_path + args.path[1:]
        else:
            save_path = base_path + args.path
        if not os.path.exists(save_path):
            print("Path doesn't exist: {}".format(save_path))
            sys.exit()
        elif not os.path.isdir(save_path):
            print("Path is not a directory!: {}".format(save_path))
            sys.exit()
        if save_path[-1] != "/":
            save_path += "/"
    else:
        save_path = base_path

    login_and_download(args.email, args.pwd, links, args.file, save_path)
