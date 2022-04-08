import os
import sys
import requests
from pprint import pprint
import datetime
import time
import json
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
import io
import hashlib

BINARY_CHOICE_1 = ["y", "Y", "н", "Н"]
BINARY_CHOICE_0 = ["n", "N", "т", "Т"]
SIGNS = ("<", ">", ":", "/", "?", "|", "*", "\\", "~", "#", "%", "&", "+", "{", "}", "%", '"')


class Vk:
    URL = "https://api.vk.com/method/"

    def __init__(self, file_tok):
        with open(file_tok, 'r') as tk:
            self.token_vk = tk.read().strip()
        url = self.URL + "users.get"
        params = {
            "access_token": self.token_vk,
            "v": "5.131"
        }
        res = requests.get(url, params=params)
        self.user_id = res.json()['response'][0]['id']

    def get_photo_inf(self, user_id, album_id):
        url = self.URL + "photos.get"
        params = {
            "user_id": user_id,
            "access_token": self.token_vk,
            "v": "5.131",
            "extended": "1",
            "album_id": album_id,
            "photo_sizes": "1",
            "count": "1000"
        }
        res = requests.get(url, params=params)
        return res.json()

    @staticmethod
    def get_sorted_url_dict(doc, tmp_ph_count=0):
        full_sorted_dict = {}
        try:
            ph_counter = int(doc['response']['count'])
            if ph_counter <= 50:
                rounds = 1
                last_round = 0
            else:
                rounds = ph_counter // 50
                last_round = ph_counter % 50
                ph_counter = 50

            def date_time(time_data):
                formatted_time = (datetime.datetime.fromtimestamp(time_data)).strftime("%d.%m.%Y_%H.%M.%S")
                return formatted_time

            def tmp_func(step):
                temp_sorted_dict = {}
                temp_sorted_dict2 = {}
                sorted_dict = {}
                temp_list1 = []
                temp_list2 = []

                for i in range(tmp_ph_count, step):
                    temp_sorted_dict[doc['response']['items'][i]['sizes'][-1]['url']] = \
                        [doc['response']['items'][i]['likes']['count'], doc['response']['items'][i]['date'],
                         doc['response']['items'][i]['sizes'][-1]['type']]
                    temp_list1.append(int(doc['response']['items'][i]['likes']['count']))
                temp_list_set1 = list(set(n for n in temp_list1 if temp_list1.count(n) > 1))
                temp_sorted_dict = dict(sorted(temp_sorted_dict.items(), key=lambda x: int(x[1][1])))
                for k, v in temp_sorted_dict.items():
                    if int(v[0]) not in temp_list_set1:
                        temp_sorted_dict2[k] = [str(v[0]), str(v[2])]
                    else:
                        temp_sorted_dict2[k] = [f'{v[0]}-{date_time(int(v[1]))}', str(v[2])]
                        temp_list2.append(f'{v[0]}-{date_time(int(v[1]))}')
                temp_list_set2 = list(set(n for n in temp_list2 if temp_list2.count(n) > 1))
                if len(temp_list_set2) > 0:
                    i = 0
                    for k, v in temp_sorted_dict2.items():
                        if (v[0]) not in temp_list_set2:
                            sorted_dict[k] = v
                        else:
                            counter = temp_list2.count(v[0])
                            sorted_dict[k] = [str(v[0]) + "_{}".format(i + 1), str(v[1])]
                            i += 1
                            if i == counter:
                                i = 0
                else:
                    sorted_dict = temp_sorted_dict2
                return sorted_dict

            for j in range(rounds):
                full_sorted_dict.update(tmp_func(ph_counter))
                tmp_ph_count += 50
                time.sleep(0.5)

            if last_round != 0:
                full_sorted_dict.update(tmp_func(tmp_ph_count + last_round))
            return full_sorted_dict
        except KeyError:
            print("\nУпс! Пользователь не найден или страница закрыта. Хм...     "
                  "|  (o__0)  |")
            time.sleep(1)
            print("\nДавай-ка попробуем еще раз!     |  (o__0)  |")
            time.sleep(2)
            normal_buddy_print()
            saver_start()

    def get_albums_dict(self, user_id):
        albums_dict = {}
        url = self.URL + "photos.getAlbums"
        params = {
            "user_id": user_id,
            "access_token": self.token_vk,
            "v": "5.131"
        }
        try:
            res = requests.get(url, params=params)
            for i in range(int(res.json()['response']['count'])):
                albums_dict[res.json()['response']['items'][i]['id']] = [res.json()['response']['items'][i]['size'],
                                                                         res.json()['response']['items'][i]['title']]

        except KeyError:
            print("\nУпс! Пользователь не найден или страница закрыта, а может и альбомов нет вовсе. Хм...     "
                  "|  (o__0)  |")
            time.sleep(1)
            print("\nДавай-ка попробуем еще раз!     |  (o__0)  |")
            time.sleep(2)
            normal_buddy_print()
            saver_start()
        if len(albums_dict) == 0:
            return
        else:
            return albums_dict


class SaverToFolder:
    def __init__(self, content, folder):
        self.content = content
        self.folder = folder
        self.log_json = []

    def write_from_sorted_dict(self, sorted_dict):
        log_json = []
        for k, v in sorted_dict.items():
            with open(str(v[0]) + ".jpeg", "wb") as f:
                f.write(requests.get(k).content)
                log_json.append({"file_name": str(v[0]) + ".jpeg", "size": v[1]})
                progress_work_buddy_print(v[0], v[1])
        self.log_json.append(log_json)
        return log_json


class GoogleDrive:
    URL = 'https://www.googleapis.com/auth/drive'

    def __init__(self, service_account_file, folder_id):
        scopes = [self.URL]
        self.log_json = []
        self.folder_id = folder_id
        self.service_account_file = service_account_file
        self.credentials = service_account.Credentials.from_service_account_file(
            self.service_account_file, scopes=scopes)

    def upload_from_sorted_dict(self, sorted_dict, parent_id):
        log_json = []
        service = build('drive', 'v3', credentials=self.credentials)

        for k, v in sorted_dict.items():
            file_metadata = {
                'name': str(v[0]),
                'parents': [parent_id]
            }
            ph = requests.get(k)
            f = io.BytesIO(ph.content)
            media = MediaIoBaseUpload(f, mimetype='image/jpeg')
            service.files().create(body=file_metadata, media_body=media).execute()
            log_json.append({"file_name": str(v[0]) + ".jpeg", "size": v[1]})
            progress_work_buddy_print(str(v[0]), v[1])
        self.log_json.append(log_json)
        return log_json

    def make_folder(self, folder_name, parent_id=None):
        service = build('drive', 'v3', credentials=self.credentials)
        body = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            body['parents'] = [parent_id]
        new_folder = service.files().create(body=body, fields='id').execute()
        return new_folder['id']

    def read_folder_id_from_txt(self):
        with open('gdrive.folder_id.txt') as f_id:
            self.folder_id = f_id.readline()
        return self.folder_id


class Yandex:
    def __init__(self, file_tok):
        with open(file_tok, 'r') as tk:
            self.token_ya = tk.read().strip()
        self.log_json = []

    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': 'OAuth {}'.format(self.token_ya)
        }

    def get_upload_link(self, disk_file_path):
        upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        headers = self.get_headers()
        params = {"path": disk_file_path, "overwrite": "true"}
        response = requests.get(upload_url, headers=headers, params=params)
        return response.json()

    def upload_from_sorted_dict(self, sorted_dict, disk_path):
        """Метод загружает файлы из отсортированного json  на яндекс диск, возвращает лог"""
        log_json = []
        for k, v in sorted_dict.items():
            href = self.get_upload_link(disk_file_path=disk_path + str(v[0]) + ".jpeg").get("href", "")
            response = requests.put(href, data=requests.get(k))
            if response.status_code == 201:
                log_json.append({"file_name": str(v[0]) + ".jpeg", "size": v[1]})
                progress_work_buddy_print(str(v[0]), v[1])

        self.log_json.append(log_json)
        return log_json

    def make_folder(self, disk_file_path):
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        headers = self.get_headers()
        params = {"path": disk_file_path}
        response = requests.put(url, headers=headers, params=params)
        return response.json()


class Odnoklassniki:
    URL = "https://api.ok.ru/fb.do"

    def __init__(self, file_tok_odn):
        with open(file_tok_odn) as tk:
            self.apl_key = tk.readline().strip()
            self.sess_s_key = tk.readline().strip()
            self.access_token = tk.readline().strip()
        self.log_json = []

    def get_private_photo_inf(self, fid):
        url = self.URL
        string = f'application_key={self.apl_key}fid={fid}method=photos.getUserPhotos{self.sess_s_key}'
        sig = hashlib.md5(string.encode()).hexdigest().lower()
        params = {
            "application_key": self.apl_key,
            "method": "photos.getUserPhotos",
            "sig": sig,
            "fid": fid,
            "access_token": self.access_token
        }
        res = requests.get(url, params=params)
        return res.json()

    def get_albums_photo_inf(self, aid, fid):
        url = self.URL
        string = f'aid={aid}application_key={self.apl_key}count=100fid={fid}method=photos.' \
                 f'getUserAlbumPhotos{self.sess_s_key}'
        sig = hashlib.md5(string.encode()).hexdigest().lower()
        params = {
            "application_key": self.apl_key,
            "method": "photos.getUserAlbumPhotos",
            "sig": sig,
            "fid": fid,
            "count": "100",
            "aid": aid,
            "access_token": self.access_token
        }
        res = requests.get(url, params=params)
        return res.json()

    def get_albums_dict(self, fid):
        albums_dict = {}
        url = self.URL
        string = f'application_key={self.apl_key}fid={fid}method=photos.getAlbums{self.sess_s_key}'
        sig = hashlib.md5(string.encode()).hexdigest().lower()
        params = {
            "application_key": self.apl_key,
            "method": "photos.getAlbums",
            "sig": sig,
            "fid": fid,
            "access_token": self.access_token
        }
        res = requests.get(url, params=params).json()
        try:
            for i in range(len(res['albums'])):
                sorted_title = ''.join(i for i in res['albums'][i]['title'] if i not in SIGNS)
                albums_dict[res['albums'][i]['aid']] = sorted_title
            return albums_dict
        except KeyError:
            print("\nУпс! Пользователь не найден или страница закрыта. Хм...     "
                  "|  (o__0)  |")
            time.sleep(1)
            print("\nДавай-ка попробуем еще раз!     |  (o__0)  |")
            time.sleep(2)
            normal_buddy_print()
            saver_start()

    @staticmethod
    def get_sorted_dict(doc):
        try:
            sorted_dict = {}
            ph_counter = len(doc['photos'])

            for i in range(ph_counter):
                url = doc['photos'][i]['standard_url']
                fid = str(doc['photos'][i]['fid'])
                m_arg = str(doc['photos'][i]['mark_avg'])
                m_count = str(doc['photos'][i]['mark_count'])
                sorted_dict[url] = [fid + "_" + m_arg + "x" + m_count, "ok_size"]
            return sorted_dict
        except KeyError:
            print("\nУпс! Пользователь не найден или страница закрыта. Хм...     "
                  "|  (o__0)  |")
            time.sleep(1)
            print("\nДавай-ка попробуем еще раз!     |  (o__0)  |")
            time.sleep(2)
            normal_buddy_print()
            saver_start()


class VkSaverToFolder(Vk, SaverToFolder):

    def __init__(self, file_tok):
        super().__init__(file_tok)
        self.log_json = []


class VkSaverToYaDisk(Vk, Yandex):

    def __init__(self, file_tok_vk, file_tok_ya):
        super().__init__(file_tok_vk)
        with open(file_tok_ya, 'r') as tk:
            self.token_ya = tk.read().strip()
        self.log_json = []


class VKSaverToGoogleDrive(Vk, GoogleDrive):
    def __init__(self, service_account_file, file_tok):
        super().__init__(file_tok)
        self.log_json = []
        scopes = ['https://www.googleapis.com/auth/drive']
        self.service_account_file = service_account_file
        self.credentials = service_account.Credentials.from_service_account_file(
            self.service_account_file, scopes=scopes)
        self.folder_id = self.read_folder_id_from_txt()


class OKSaverToFolder(Odnoklassniki, SaverToFolder):
    def __init__(self, tok_odn):
        super().__init__(tok_odn)
        self.log_json = []


class OKSaverToYaDisk(Odnoklassniki, Yandex):
    def __init__(self, file_tok_odn, file_tok_ya):
        super().__init__(file_tok_odn)
        with open(file_tok_ya, 'r') as tk:
            self.token_ya = tk.read().strip()
        self.log_json = []


class OkSaverToGDrive(Odnoklassniki, GoogleDrive):
    def __init__(self, file_tok_odn, service_account_file):
        super().__init__(file_tok_odn)
        scopes = ['https://www.googleapis.com/auth/drive']
        self.service_account_file = service_account_file
        self.credentials = service_account.Credentials.from_service_account_file(
            self.service_account_file, scopes=scopes)
        self.folder_id = self.read_folder_id_from_txt()


def good_work_buddy_print():
    print()
    print()
    print(f'                               \../')
    print(f'      Готово, босс!           (o__0)')
    print(f'                           *___/||\  ')
    print(f'                                ||')
    print()


def normal_buddy_print():
    print()
    print()
    print(f'                               \../')
    print(f'      Жду указаний, босс!     (o__0)')
    print(f'                               /||\  ')
    print(f'                                ||')
    print()


def greet_buddy_print():
    print()
    print(f'                                 \../')
    print(f'      Приветствую, босс!       \(o__0)')
    print(f'                                ` ||\  ')
    print(f'                                  || ')
    print()


def bye_buddy_print():
    print()
    print(f'                                 \../')
    print(f'       До встречи, босс!       \(o__0)')
    print(f'                                ` ||\  ')
    print(f'                                  || ')
    print()


def progress_work_buddy_print(name, size):
    print()
    print(f'file_name: {name}.jpg     |  (o__0)  |     size: {size}')
    print()


def main_menu_start(opt_dict):
    option_choice = ""
    for opt_number, opt_inf in opt_dict.items():
        print(f'{opt_number}---{opt_inf[1]} ')
    while not option_choice.isdigit() or option_choice not in list(str(opt_dict.keys())):
        option_choice = input("\nВведите цифру выбора опции закачки: ").strip()

    opt_dict[int(option_choice)][0]()


def log_write_json(client):
    if not os.path.isdir("logs"):
        os.mkdir("logs")
    os.chdir("logs")
    with open("log_" + "_{}".format(datetime.datetime.now().strftime("%d.%m.%Y_%H.%M.%S")) + ".json", 'w') as log1:
        json.dump(client.log_json, log1, indent=2)


def get_id_choice(user, id_choice="", user_id=""):
    while id_choice not in BINARY_CHOICE_1 and id_choice not in BINARY_CHOICE_0:
        id_choice = input("Скачиваем свои фото? (Y/N): ").strip()
    if id_choice in BINARY_CHOICE_1:
        user_id = user.user_id
    elif id_choice in BINARY_CHOICE_0:
        while not user_id.isdigit() and not 1 < len(user_id.split()) <= 11:
            user_id = input("Введите id владельца фото: ").strip()
    return user_id


def get_fid_choice(fid=""):
    while not fid.isdigit() and not 1 < len(fid.split()) <= 11:
        fid = input("Введите id владельца фото: ").strip()
    return fid


def change_folder():
    folder = ""
    while not os.path.isdir(folder):
        folder = input("Скопируйте адрес для сохранения фото: ")
    os.chdir(folder)
    return folder


def remove_signs(value, signs=SIGNS):
    for c in signs:
        value = str(value).replace(c, '')
    return value


def vk_save_to_folder_profile():
    client = VkSaverToFolder("tkn.vk.txt")
    user_id = get_id_choice(client)
    inf = client.get_photo_inf(user_id, "profile")
    sorted_dict = client.get_sorted_url_dict(inf)
    change_folder()
    client.write_from_sorted_dict(sorted_dict)
    log_write_json(client)
    good_work_buddy_print()


def vk_save_to_folder_albums():
    sorted_alb_dict = {}
    choice = ""
    client = VkSaverToFolder("tkn.vk.txt")
    user_id = get_id_choice(client)
    albums_dict = client.get_albums_dict(user_id)
    for k, v in albums_dict.items():
        if int(v[0]) > 0:
            sorted_alb_dict[k] = v[1]
    choice_dict = dict(enumerate(sorted_alb_dict.items()))
    choice_dict[len(sorted_alb_dict)] = "Скачать все альбомы за раз по папкам"
    print()
    pprint(choice_dict)
    while not choice.isdigit():
        choice = input("\nВведите цифру опции выбора альбома  или полной закачки: ").strip()
    if choice == str(list(choice_dict.keys())[-1]):
        folder = change_folder()
        for k, v in sorted_alb_dict.items():
            ph_inf = client.get_photo_inf(user_id, str(k))
            pprint(ph_inf)
            sorted_dict = client.get_sorted_url_dict(ph_inf)
            if not os.path.isdir(str(v)):
                os.mkdir("{}".format(str(v)))
            else:
                print(f'\nПапка "{str(v)}" уже существует!\n')
            os.chdir(str(v))
            client.write_from_sorted_dict(sorted_dict)
            os.chdir(folder)
    else:
        folder = change_folder()
        ph_inf = client.get_photo_inf(user_id, str(choice_dict[int(choice)][0]))
        pprint(ph_inf)
        sorted_dict = client.get_sorted_url_dict(ph_inf)
        if not os.path.isdir(str(choice_dict[int(choice)][1])):
            os.mkdir("{}".format(str(choice_dict[int(choice)][1])))
        else:
            print(f'\nПапка "{str(choice_dict[int(choice)][1])}" уже существует!\n')
        os.chdir(folder + "/" + str(choice_dict[int(choice)][1]))
        client.write_from_sorted_dict(sorted_dict)
        os.chdir(folder)
    log_write_json(client)
    good_work_buddy_print()


def vk_save_to_yadisk_profile():
    client = VkSaverToYaDisk("tkn.vk.txt", "tkn.ya.txt")
    user_id = get_id_choice(client)
    inf = client.get_photo_inf(user_id, "profile")
    sorted_dict = client.get_sorted_url_dict(inf)
    folder_name = input(f'Введите название папки для создания на Ядиске\n({SIGNS} '
                        f'- недопустимы и будут удалены): \n').strip("".join(list(SIGNS)))
    client.make_folder(folder_name)
    client.upload_from_sorted_dict(sorted_dict, "/{}/".format(folder_name))
    log_write_json(client)
    good_work_buddy_print()


def vk_save_to_yadisk_albums():
    choice = ""
    sorted_alb_dict = {}
    client = VkSaverToYaDisk("tkn.vk.txt", "tkn.ya.txt")
    user_id = get_id_choice(client)
    albums_dict = client.get_albums_dict(user_id)
    folder_name = input(f'Введите название папки для создания на Ядиске\n({SIGNS} '
                        f'- недопустимы и будут удалены): \n').strip("".join(list(SIGNS)))
    client.make_folder(folder_name)
    for k, v in albums_dict.items():
        if int(v[0]) > 0:
            sorted_alb_dict[k] = v[1]
    choice_dict = dict(enumerate(sorted_alb_dict.items()))
    choice_dict[len(sorted_alb_dict)] = ("", "* Скачать все альбомы по папкам")
    print()
    for k, v in choice_dict.items():
        print(f'{k} --- {v[1]}')
    while not choice.isdigit():
        choice = input("\nВведите цифру опции выбора альбома  или полной закачки: ").strip()
    if choice == str(list(choice_dict.keys())[-1]):
        for k, v in sorted_alb_dict.items():
            ph_inf = client.get_photo_inf(user_id, str(k))
            sorted_dict = client.get_sorted_url_dict(ph_inf)
            client.make_folder("/{}/".format(folder_name) + v)
            client.upload_from_sorted_dict(sorted_dict, "/{}/{}/".format(folder_name, v))
    else:
        ph_inf = client.get_photo_inf(user_id, str(choice_dict[int(choice)][0]))
        sorted_dict = client.get_sorted_url_dict(ph_inf)
        client.make_folder("/{}/".format(folder_name) + str(choice_dict[int(choice)][1]))
        client.upload_from_sorted_dict(sorted_dict, "/{}/{}/".format(folder_name, str(choice_dict[int(choice)][1])))
    log_write_json(client)
    good_work_buddy_print()


def vk_save_to_gdrive_profile():
    client = VKSaverToGoogleDrive("gdrive.json.key.json", "tkn.vk.txt")
    user_id = get_id_choice(client)
    inf = client.get_photo_inf(user_id, "profile")
    sorted_dict = client.get_sorted_url_dict(inf)
    folder_name = input(f'Введите название папки для фото с профиля на GDrive\n({SIGNS} '
                        f'- недопустимы и будут удалены): \n').strip("".join(list(SIGNS)))
    folder_id = client.make_folder(folder_name, client.folder_id)
    client.upload_from_sorted_dict(sorted_dict, folder_id)
    good_work_buddy_print()


def vk_save_to_gdrive_albums():
    choice = ""
    sorted_alb_dict = {}
    client = VKSaverToGoogleDrive("gdrive.json.key.json", "tkn.vk.txt")
    user_id = get_id_choice(client)
    albums_dict = client.get_albums_dict(user_id)
    for k, v in albums_dict.items():
        if int(v[0]) > 0:
            sorted_alb_dict[k] = v[1]
    choice_dict = dict(enumerate(sorted_alb_dict.items()))
    choice_dict[len(sorted_alb_dict)] = ("", "* Скачать все альбомы по папкам")
    print()
    for k, v in choice_dict.items():
        print(f'{k} --- {v[1]}')
    while not choice.isdigit():
        choice = input("\nВведите цифру опции выбора альбома  или полной закачки: \n").strip()
    if choice == str(list(choice_dict.keys())[-1]):
        for k, v in sorted_alb_dict.items():
            ph_inf = client.get_photo_inf(user_id, str(k))
            sorted_dict = client.get_sorted_url_dict(ph_inf)
            folder_id = client.make_folder(v, client.folder_id)
            client.upload_from_sorted_dict(sorted_dict, folder_id)
    else:
        ph_inf = client.get_photo_inf(user_id, str(choice_dict[int(choice)][0]))
        sorted_dict = client.get_sorted_url_dict(ph_inf)
        folder_id = client.make_folder(str(choice_dict[int(choice)][1]), client.folder_id)
        client.upload_from_sorted_dict(sorted_dict, folder_id)
    log_write_json(client)
    good_work_buddy_print()


def ok_save_to_folder_profile():
    client = OKSaverToFolder("tkn.odn.txt")
    fid = get_fid_choice()
    inf = client.get_private_photo_inf(fid)
    sorted_dict = client.get_sorted_dict(inf)
    change_folder()
    client.write_from_sorted_dict(sorted_dict)
    log_write_json(client)
    good_work_buddy_print()


def ok_save_to_folder_albums():
    choice = ""
    client = OKSaverToFolder("tkn.odn.txt")
    fid = get_fid_choice()
    albums_dict = client.get_albums_dict(fid)
    if len(albums_dict) > 0:
        choice_dict = dict(enumerate(albums_dict.items()))
        choice_dict[len(albums_dict)] = ("", "* Скачать все альбомы по папкам")
        print()
        for k, v in choice_dict.items():
            print(f'{k} --- {v[1]}')
        while not choice.isdigit():
            choice = input("\nВведите цифру опции выбора альбома  или полной закачки: ").strip()
        if choice == str(list(choice_dict.keys())[-1]):
            folder = change_folder()
            for k, v in albums_dict.items():
                alb_inf = client.get_albums_photo_inf(str(k), fid)
                sorted_dict = client.get_sorted_dict(alb_inf)
                if not os.path.isdir(str(v)):
                    os.mkdir(str(v))
                else:
                    print(f'\nПапка - "{str(v)}" уже существует!\n')
                os.chdir(str(v))
                client.write_from_sorted_dict(sorted_dict)
                os.chdir(folder)
        else:
            folder = change_folder()
            ph_inf = client.get_albums_photo_inf(str(choice_dict[int(choice)][0]), fid)
            sorted_dict = client.get_sorted_dict(ph_inf)
            if not os.path.isdir(str(choice_dict[int(choice)][1])):
                os.mkdir("{}".format(str(choice_dict[int(choice)][1])))
            else:
                print(f'\nПапка "{str(choice_dict[int(choice)][1])}" уже существует!\n')
            os.chdir(folder + "/" + str(choice_dict[int(choice)][1]))
            client.write_from_sorted_dict(sorted_dict)
            os.chdir(folder)
        log_write_json(client)
        good_work_buddy_print()
    else:
        print(f'\nУпс! Кажется у  пользователя c id №{fid} нету альбомов.')
        time.sleep(1)
        print("\nДавай-ка попробуем еще раз!     |  (o__0)  |")
        time.sleep(2)
        normal_buddy_print()
        saver_start()


def ok_save_to_yadisk_profile():
    client = OKSaverToYaDisk("tkn.odn.txt", "tkn.ya.txt")
    fid = get_fid_choice()
    inf = client.get_private_photo_inf(fid)
    sorted_dict = client.get_sorted_dict(inf)
    folder_name = input(f'Введите название папки для создания на Ядиске\n({SIGNS} '
                        f'- недопустимы и будут удалены): \n').strip("".join(list(SIGNS)))
    client.make_folder(folder_name)
    client.upload_from_sorted_dict(sorted_dict, "/{}/".format(folder_name))
    log_write_json(client)
    good_work_buddy_print()


def ok_save_to_yadisk_albums():
    choice = ""
    client = OKSaverToYaDisk("tkn.odn.txt", "tkn.ya.txt")
    fid = get_fid_choice()
    albums_dict = client.get_albums_dict(fid)
    folder_name = input(f'Введите название папки для создания на Ядиске\n({SIGNS} '
                        f'- недопустимы и будут удалены): \n').strip("".join(list(SIGNS)))
    client.make_folder(folder_name)
    if len(albums_dict) > 0:
        choice_dict = dict(enumerate(albums_dict.items()))
        choice_dict[len(albums_dict)] = ("", "* Скачать все альбомы по папкам")
        print()
        for k, v in choice_dict.items():
            print(f'{k} --- {v[1]}')
        while not choice.isdigit():
            choice = input("\nВведите цифру опции выбора альбома  или полной закачки: ").strip()
        if choice == str(list(choice_dict.keys())[-1]):
            for k, v in albums_dict.items():
                ph_inf = client.get_albums_photo_inf(str(k), fid)
                pprint(ph_inf)
                sorted_dict = client.get_sorted_dict(ph_inf)
                client.make_folder("/{}/".format(folder_name) + v)
                client.upload_from_sorted_dict(sorted_dict, "/{}/{}/".format(folder_name, v))
        else:
            ph_inf = client.get_albums_photo_inf(str(choice_dict[int(choice)][0]), fid)
            sorted_dict = client.get_sorted_dict(ph_inf)
            client.make_folder("/{}/".format(folder_name) + str(choice_dict[int(choice)][1]))
            client.upload_from_sorted_dict(sorted_dict, "/{}/{}/".format(folder_name, str(choice_dict[int(choice)][1])))
        log_write_json(client)
        good_work_buddy_print()
    else:
        print(f'\nУпс! Кажется у  пользователя c id №{fid} нету альбомов.')
        time.sleep(1)
        print("\nДавай-ка попробуем еще раз!     |  (o__0)  |")
        time.sleep(2)
        normal_buddy_print()
        saver_start()


def ok_save_to_gdrive_profile():
    client = OkSaverToGDrive("tkn.odn.txt", "gdrive.json.key.json")
    fid = get_fid_choice()
    inf = client.get_private_photo_inf(fid)
    sorted_dict = client.get_sorted_dict(inf)
    folder_name = input(f'Введите название папки для фото с профиля на GDrive\n({SIGNS} '
                        f'- недопустимы и будут удалены): \n').strip("".join(list(SIGNS)))
    folder_id = client.make_folder(folder_name, client.folder_id)
    client.upload_from_sorted_dict(sorted_dict, folder_id)
    good_work_buddy_print()


def ok_save_to_gdrive_albums():
    choice = ""
    client = OkSaverToGDrive("tkn.odn.txt", "gdrive.json.key.json")
    fid = get_fid_choice()
    albums_dict = client.get_albums_dict(fid)
    if len(albums_dict) > 0:
        choice_dict = dict(enumerate(albums_dict.items()))
        choice_dict[len(albums_dict)] = ("", "* Скачать все альбомы по папкам")
        print()
        for k, v in choice_dict.items():
            print(f'{k} --- {v[1]}')
        while not choice.isdigit():
            choice = input("\nВведите цифру опции выбора альбома  или полной закачки: \n").strip()
        if choice == str(list(choice_dict.keys())[-1]):
            for k, v in albums_dict.items():
                ph_inf = client.get_albums_photo_inf(str(k), fid)
                sorted_dict = client.get_sorted_dict(ph_inf)
                folder_id = client.make_folder(v, client.folder_id)
                client.upload_from_sorted_dict(sorted_dict, folder_id)
        else:
            ph_inf = client.get_albums_photo_inf(str(choice_dict[int(choice)][0]), fid)
            sorted_dict = client.get_sorted_dict(ph_inf)
            folder_id = client.make_folder(str(choice_dict[int(choice)][1]), client.folder_id)
            client.upload_from_sorted_dict(sorted_dict, folder_id)
        log_write_json(client)
        good_work_buddy_print()
    else:
        print(f'\nУпс! Кажется у  пользователя c id №{fid} нету альбомов.')
        time.sleep(1)
        print("\nДавай-ка попробуем еще раз!     |  (o__0)  |")
        time.sleep(2)
        normal_buddy_print()
        saver_start()


options_vk = {
    1: [vk_save_to_folder_profile, "Сохранить с ВК фото профиля в папку на ПК"],
    2: [vk_save_to_folder_albums, "Сохранить с ВК фото c альбомов в папку на ПК"],
    3: [vk_save_to_yadisk_profile, "Сохранить с ВК фото профиля в папку на Яндекс Диск"],
    4: [vk_save_to_yadisk_albums, "Сохранить с ВК фото c альбомов в папку на Яндекс Диск"],
    5: [vk_save_to_gdrive_profile, "Сохранить с ВК фото профиля в папку Google Drive"],
    6: [vk_save_to_gdrive_albums, "Сохранить с ВК фото c альбомов в папку Google Drive"]
}

options_odn = {
    1: [ok_save_to_folder_profile, "Сохранить с ОК фото профиля в папку на ПК"],
    2: [ok_save_to_folder_albums, "Сохранить с ОК фото c альбомов в папку на ПК"],
    3: [ok_save_to_yadisk_profile, "Сохранить с ОК фото профиля в папку на Яндекс Диск"],
    4: [ok_save_to_yadisk_albums, "Сохранить с ОК фото c альбомов в папку на Яндекс Диск"],
    5: [ok_save_to_gdrive_profile, "Сохранить с ОК фото профиля в папку Google Drive"],
    6: [ok_save_to_gdrive_albums, "Сохранить с ОК фото c альбомов в папку Google Drive"]
}

main_option = {
    1: ["VK", options_vk],
    2: ["OK", options_odn]
}


def saver_start():
    wd = os.getcwd()
    main_choice = ""
    time.sleep(1)
    print("Откуда скачиваем фото?\n")
    for number, option in main_option.items():
        print(f'{number}---{option[0]}')
    while main_choice not in ("1", "2"):
        main_choice = input("\nВыберите опцию: ").strip()
    if main_choice == "1":
        normal_buddy_print()
        main_menu_start(options_vk)
    if main_choice == "2":
        normal_buddy_print()
        main_menu_start(options_odn)
    os.chdir(wd)


def continue_saver():
    cont_choice = ""
    while cont_choice not in BINARY_CHOICE_1 and cont_choice not in BINARY_CHOICE_0:
        cont_choice = input("Продолжим? (Y/N): ").strip()
    if cont_choice in BINARY_CHOICE_1:
        normal_buddy_print()
        saver_start()
        continue_saver()
    else:
        bye_buddy_print()
        time.sleep(2)
        sys.exit()


if __name__ == '__main__':
    greet_buddy_print()
    saver_start()
    continue_saver()
