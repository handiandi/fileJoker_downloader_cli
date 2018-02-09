#!/usr/bin/env python3
from collections import defaultdict
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from bs4 import BeautifulSoup
import multiprocessing as mp
import concurrent.futures
import sys
import os
import ctypes
import platform
import requests
import urllib.request
import re
import time

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

class FileJoker():

    def __init__(self, email, pwd, urls, names, file_w_urls, path, thread, count_total, thread_use):
        self.s = self.login_requests(email, pwd)
        self.urls = urls
        self.path = path
        self.names = names
        self.thread = thread
        self.count = 0
        self.file_w_urls = file_w_urls
        self.count_total = count_total
        self.thread_use = thread_use
        process = self.Process_executor(urls)

        # for don't break the loop force return
        if process is False:
           pass

    def Process_executor(self, url):
        time.sleep(int(self.thread)+2)
        count = self.count
        url_id = url[url.rfind('/')+1:]
        source = self.s.get(url)
        if not self.check_for_free_disk_space(self.path, self.find_size_of_file(source.text)):
            print("\033[2K\r\033[KNot enough disk space")
            sys.exit(-1)
            #return False
        self.link = self.find_download_link(source)

        if self.link is None:
            print("\033[2K\033[{}A\r\033[KCouldn't find the download-link for {}\r".format(self.fix_thread_pos()-(int(self.thread)), url))
            return True

        try:
            self.filename = urllib.request.unquote(self.link[self.link.rfind("/")+1:])
        except:
            return False
        print("\033[1K\033[10B\r"+str(self.filename))
        new_filename = None
        if url in self.names:
            new_filename = self.names[url]+self.filename[self.filename.rfind('.'):].strip()
        new_filename_text = "\033[2K\033[{}B\r\033[K(renamed to '{}')".format(2*self.fix_thread_pos(), new_filename) \
            if new_filename else ""
        que_text = " - ({} of {} files in que)".format(count+1, self.count_total) \
            if len(self.urls) > 1 else ""
    
        print("\033[1K\033[{}B\rDownloading file '{}' {} [{}]{}".format(
              2*self.fix_thread_pos(),self.filename, new_filename_text, url_id, que_text))
        
        self.download(self.link, self.filename, self.path)

        if new_filename:
            os.rename(self.path+self.filename, self.path+new_filename)

        if(self.file_w_urls):
            p = mp.Process(name="deleteID+"+str(count),
                           target=self.delete_id_from_file,
                           args=(self.file_w_urls, url_id))
            p.start()
        self.count = self.count+1
        return True

    def login_requests(self, email, pwd):
        s = requests.Session()
        s.post('https://filejoker.net/login',
               data={'email': email,
                     'op': 'login',
                     'password': pwd,
                     'rand': '',
                     'redirect': ''})
        return s

    def download(self, url, filename, path):
        r = self.s.get(url, stream=True)
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
                        sys.stdout.write("\033[2K\033[K\r[%s%s] - %d of %d MB (%d%%)" %
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

    def fix_thread_pos(self):
        if self.thread_use == 0:
            thread_use = 1
            return thread_use
        else:
            thread_use = self.thread_use+1
            return thread_use

    def find_download_link(self, html):
        time.sleep(1)
        soup = BeautifulSoup(html.text, 'lxml')
        submit = soup.find('form', attrs={"name":u"F1"})
        op = soup.find('input', attrs={"name":u"op"})
        ids = soup.find('input', attrs={"name":u"id"})
        rand = soup.find('input', attrs={"name":u"rand"})
        referer = soup.find('input', attrs={"name":u"referer"})
        method_premium = soup.find('input', attrs={"name":u"method_premium"})
        down_direct = soup.find('input', attrs={"name":u"down_direct"})
        print()
        data = self.s.post("https://filejoker.net"+str(submit.attrs["action"]), data={"op":str(op.attrs["value"]),
                                                                                 "id":str(ids.attrs["value"]),
                                                                                 "rand":str(rand.attrs["value"]),
                                                                                 "referer":str(referer.attrs["value"]),
                                                                                 "method_premium":str(method_premium.attrs["value"]),
                                                                                 "down_direct":str(down_direct.attrs["value"])})
        if self.reach_download_limit(data.text):
            print("\033[1K\033[{}B\r\033[K{}\r".format(self.fix_thread_pos()-(int(self.thread)+2), "You have reached your download limit. " +
                                                          "You can't download any more files right now. Try again later"))
            #sys.exit()
            return None
        
        link = None
        try:
            soup = BeautifulSoup(data.text, 'lxml')
            download = soup.find("a", attrs={"class":"btn btn-green"})
            download.attrs["href"]
        except Exception:
            try:
                print("\033[2K\033[{}A\r\033[KCouldn't find download link. Probably it's a file you can stream\033[0K".format(self.fix_thread_pos()-(int(self.thread)+2)))
                print("\033[2K\033[{}A\r\033[KTrying to find the link in another way\033[0K".format(self.fix_thread_pos()-(int(self.thread)+2)))
                soup = BeautifulSoup(data.text, 'lxml')
                submit = soup.find('form', attrs={"name":u"F1"})
                op = soup.find('input', attrs={"name":u"op"})
                ids = soup.find('input', attrs={"name":u"id"})
                rand = soup.find('input', attrs={"name":u"rand"})
                referer = soup.find('input', attrs={"name":u"referer"})
                method_premium = soup.find('input', attrs={"name":u"method_premium"})
                down_direct = soup.find('input', attrs={"name":u"down_direct"})

                data = self.s.post("https://filejoker.net"+submit.attrs["action"], data={"op":op.attrs["value"],
                                   "id":ids.attrs["value"],
                                   "rand":rand.attrs["value"],
                                   "referer":referer.attrs["value"],
                                   "method_premium":method_premium.attrs["value"],
                                   "down_direct":down_direct.attrs["value"]})
                if self.reach_download_limit(data.text):
                    print("\033[2K\033[{}A\r\033[K{}".format(self.fix_thread_pos()-(int(self.thread)+2), "\nYou have reached your download limit. " +
                                                                "You can't download any more files right now. Try again later"))
                    return None
                soup = BeautifulSoup(data.text, 'lxml')
                download = soup.find("a", attrs={"class":"btn btn-green"})
                download.attrs["href"]
            except Exception:
                return None

        '''if link is None:
            try:
                link = self.driver.find_element(
                    By.XPATH, '//*[@id="main"]/center/a')  # When streaming video
            except Exception:
                return None'''
        return download.attrs["href"]

    def find_size_of_file(self, html):
        soup = BeautifulSoup(html, 'lxml')
        file_size_text = soup.find('small').text
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

    def __call__(self):
        pass

def enumerated(lists, thread):
    list_0 = []
    list_1 = []
    count = 0
    for i in lists:
        if count == int(thread):
            count = 0
            list_0.append(count)
            list_1.append(i)
            count = count + 1
        else:
            list_0.append(count)
            list_1.append(i)
            count = count + 1
    return list_0, list_1

def stop_process_pool(executor):
    for pid, processes in executor._processes.items():
        processes.terminate()
    executor.shutdown()

def main(thread, email, pwd, links, names, file, save_path, count_total, counts):
    '''for e, url in zip(counts, links):
        FileJoker(email, pwd, url, names, file, save_path, thread, count_total, e)'''
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=int(thread)) as executor:
        try:
            for future in concurrent.futures.as_completed([executor.submit(FileJoker, email, pwd, 
                                                                           url, names, file, save_path,
                                                                           thread, count_total, e) \
                                                                           for e, url in zip(counts, links)]):
                try:
                    if ("<__main__.FileJoker" not in future.result()):
                        print(future.result())
                except TypeError:
                    pass
        #except concurrent.futures._base.TimeoutError:
        #    print("This took to long...")
        #    stop_process_pool(executor)
        except concurrent.futures.process.BrokenProcessPool:
            pass

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
            #sys.exit()
        elif not os.path.isdir(save_path):
            print("Path is not a directory!: {}".format(save_path))
            #sys.exit()
        if save_path[-1] != "/":
            save_path += "/"
    else:
        save_path = base_path

    count_total = len(links)
    counts, links  = enumerated(links, args.thread)

    main(args.thread, args.email, 
         args.pwd, links, names, 
         args.file, save_path, 
         count_total, counts)