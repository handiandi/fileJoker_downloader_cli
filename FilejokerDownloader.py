#!/usr/bin/env python3
import sys
import os
import ctypes
import platform
import requests
import urllib.request
from collections import defaultdict
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import multiprocessing as mp
import concurrent.futures
import time


class FileJoker():

    def __init__(self, email, pwd, urls, names, file_w_urls, path, thread):
        self.s = self.login_requests(email, pwd)
        self.driver = self.login_selenium(email, pwd)

        with concurrent.futures.ThreadPoolExecutor(max_workers=int(thread)) as executor:
            for count, url in enumerate(urls):
                wait_for = executor.submit(self.Process_executor, url, path)

    def Process_executor(self, url, path):
        url_id = url[url.rfind('/')+1:]
        self.driver.get(url)
        if not self.check_for_free_disk_space(path, self.find_size_of_file()):
            print("Not enough disk space")
            sys.exit(-1)
        self.link = self.find_download_link()

        if self.link is None:
            print("Couldn't find the download-link for {}".format(url))
            return False

        self.filename = urllib.request.unquote(self.link[self.link.rfind("/")+1:])
        new_filename = None
        if url in names:
            new_filename = names[url]+filename[filename.rfind('.'):].strip()
        new_filename_text = "(renamed to '{}')".format(new_filename) \
            if new_filename else ""
        que_text = " - ({} of {} files in que)".format(count+1, len(urls)) \
            if len(urls) > 1 else ""

        print("Downloading file '{}' {} [{}]{}".format(
             self.filename, new_filename_text, url_id, que_text))
        self.download(self.s, self.link, self.filename, path)
        if new_filename:
            os.rename(path+filename, path+new_filename)
        if(file_w_urls):
            p = mp.Process(name="deleteID+"+str(count),
                           target=delete_id_from_file,
                           args=(file_w_urls, url_id))
            p.start()

    def login_requests(self, email, pwd):
        s = requests.Session()
        s.post('https://filejoker.net/login',
               data={'email': email,
                     'op': 'login',
                     'password': pwd,
                     'rand': '',
                     'redirect': ''})
        return s


    def login_selenium(self, email, pwd):
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap['phantomjs.page.settings.userAgent'] = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36")
        driver = webdriver.PhantomJS(desired_capabilities=dcap, service_args=[
                                     '--ignore-ssl-errors=true', '--ssl-protocol=any', '--web-security=false'])
        driver.get('https://filejoker.net/login')
        login_email_box = None
        login_pwd_box = None
        login_button = None
        try:
            login_email_box = driver.find_element(By.NAME, 'email')
            login_pwd_box = driver.find_element(By.NAME, 'password')
            login_button = driver.find_element(By.XPATH, '//*[@id="loginbtn"]')
        except Exception as e:
            sys.exit("Couldn't find login elements")

        if login_email_box is not None and login_pwd_box is not None and login_button is not None:
            try:
                login_email_box.send_keys(email)
                login_pwd_box.send_keys(pwd)
                login_button.click()
            except Exception as e:
                sys.exit("Couldn't login")
        return driver
  
    def download(self, session, url, filename, path):
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


    def delete_id_from_file(self, file, fj_id):
        lines = []
        with open(file, 'r+') as f:
            for line in f:
                lines.append(line.strip())
            f.seek(0)
            for item in lines:
                idd = item[item.rfind('/')+1:item.rfind(
                    '-->')].strip() if item.rfind(
                    '-->') > -1 else item[item.rfind('/')+1:].strip()
                if fj_id != idd or item.startswith('#'):
                    f.write(item+"\n")
            f.truncate()


    def reach_download_limit(self, s):
        goal = 'There is not enough traffic available to download this file.'
        if [m.start() for m in re.finditer(goal, s)]:
            return True
        return False


    def find_download_link(self):
        time.sleep(0.3)
        get_download_link_button = self.driver.find_element(By.XPATH, '//*[@id="download"]/div/div[2]/form/button')
        get_download_link_button.click()

        if self.reach_download_limit(self.driver.page_source):
            print("You have reached your download limit. You can't download any more files right now. Try again later")
            sys.exit()

        link = None
        try:
            link = self.driver.find_element(
                By.XPATH, '//*[@id="download"]/div[1]/div[2]/a')
        except Exception:
            print("Couldn't find download link. Probably it's a file you can stream")
            print("Trying to find the link in another way")
        if link is None:
            try:
                link = self.driver.find_element(
                    By.XPATH, '//*[@id="main"]/center/a')  # When streaming video
            except Exception:
                return None
        return link.get_attribute('href')


    def find_size_of_file(self):
        file_size_tex_elem = self.driver.find_element(
            By.XPATH, '//*[@id="download"]/div/div[1]/small')
        file_size_text = file_size_tex_elem.get_attribute('innerHTML')
        size = defaultdict(dict)
        size['size'] = float(file_size_text[1:file_size_text.rfind(' ')].strip())
        size['size_value'] = file_size_text[file_size_text.rfind(' ')+1:-1].strip()
        return size


    def check_for_free_disk_space(self, path, size, ratio=0.6):
        totalAvailSpace = None
        if platform.system() == 'Windows':
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
            totalAvailSpace = free_bytes.value
        else:
            st = os.statvfs(path)
            totalAvailSpace = st.f_bavail * st.f_frsize

        rules = {'b': totalAvailSpace,
                 'kb': totalAvailSpace/1024,
                 'mb': totalAvailSpace/1024/1024,
                 'gb': totalAvailSpace/1024/1024/1024}
        if size['size'] / rules[size['size_value'].lower()] <= ratio:
            return True
        return False


def read_file(file):
    links = []
    lines = []
    names = {}
    with open(file, 'r') as f:
        for line in f:
            if not line.startswith("#"):
                lines.append(line.strip())
    for line in lines:
        result = line.split('-->')
        if len(result) == 2:
            names[result[0].strip()] = result[1].strip()
        links.append(result[0].strip())
    return list(set(links)), names


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
    arg_parser.add_argument("-t", "--thread", metavar="STRING",
                            dest="thread", help="define number process to download simultaneous.")
    base_path = os.path.realpath(__file__)
    base_path = base_path[:base_path.rfind("/")+1]
    save_path = None
    args = arg_parser.parse_args()
    links = []
    names = []
    if args.email is None:
        arg_parser.error("Missing email for login")
    if args.pwd is None:
        arg_parser.error("Missing password for login")
    if args.link is None and args.file is None:
        arg_parser.error("Missing download link (or links)")
    if args.file:
        links, names = read_file(args.file)
    if args.link:
        links.append(args.link)

    if args.thread is None:
        args.thread = "1"

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

    FileJoker(args.email, args.pwd, links,
              names, args.file, save_path, args.thread)
