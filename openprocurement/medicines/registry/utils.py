import os
import ast
from pytz import timezone
from datetime import datetime
from functools import partial

from xml.etree import ElementTree


SANDBOX_MODE = True if os.environ.get('SANDBOX_MODE', 'False').lower() == 'true' else False
TZ = timezone(os.environ['TZ'] if 'TZ' in os.environ else 'Europe/Kiev')


def get_now():
    return datetime.now(TZ).replace(microsecond=0)


def decode_cp1251(s):
    return s.decode('cp1251')


def file_exists(file_path):
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return True
    else:
        return False


def file_is_empty(file_path):
    if os.stat(file_path).st_size > 0:
        return False
    else:
        return True


def create_file(file_path):
    with open(file_path, 'w'):
        pass


def str_to_obj(string):
    return ast.literal_eval(string)


def get_file_last_modified(filepath):
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return datetime.fromtimestamp(os.path.getmtime(filepath), TZ).replace(microsecond=0)


def string_time_to_datetime(time='hh:mm:ss'):
    dt_str = '{} {}'.format(get_now().date(), time)

    try:
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        dt = None

    return dt


def journal_context(record=None, params=None):
    if params is None:
        params = {}

    if record is None:
        record = {}

    for k, v in params.items():
        record['JOURNAL_' + k] = v

    return record


class XMLParser:
    def __init__(self, xml):
        parser = ElementTree.XMLParser(encoding='utf-8')

        try:
            self.xml = ElementTree.fromstring(xml, parser)
        except ElementTree.ParseError:
            self.xml = None

        self.ROOT_ITEM = 'doc'

    @staticmethod
    def get_value(key, item):
        try:
            item = item.find(key).text

            return item.replace('*', '')
        except AttributeError:
            return None

    def get_values(self, key, unique=True):
        get_value = partial(self.get_value, key)

        if self.xml is not None:
            values = map(get_value, self.xml.findall(self.ROOT_ITEM))
        else:
            return list()

        if unique:
            return set(values)
        else:
            return values

    def inn2atc_atc2inn(self, root):
        _tmp = dict()

        if self.xml is not None:
            for i in self.xml:
                inn = i.find('mnn').text or ''
                atc_list = [i.find('atc1').text, i.find('atc2').text, i.find('atc3').text]
                atc = set([i.decode('utf-8') for i in atc_list if i])

                inn = inn.replace('*', '').decode('utf-8')

                if root == 'inn':
                    if inn in _tmp:
                        value = _tmp.get(inn) | atc
                        _tmp[inn] = value
                    else:
                        _tmp[inn] = atc
                elif root == 'atc':
                    for _atc in atc:
                        if _atc in _tmp:
                            value = _tmp.get(_atc) | {inn}
                            _tmp[_atc] = value
                        else:
                            _tmp[_atc] = {inn}
                else:
                    return dict()
        return {k: list(v) for k, v in _tmp.items()}

