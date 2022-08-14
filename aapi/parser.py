import datetime
import hashlib
import logging
import json
import os
import platform
import random
from abc import abstractmethod
from enum import Enum
from typing import (
    List,
    Dict,
    Any
)
from urllib.parse import urlparse

from aiohttp import hdrs


class RequestType(Enum):
    """
    请求体类型
    """
    NONE = 'none'
    FORM_DATA = 'formdata'
    X_WWW_FORM_URLENCODED = 'urlencoded'
    RAW = 'raw'


class EventScript(object):
    """
    请求过程中事件对象
    """

    def __init__(self, lines: List[str], script_type: str = ''):
        self._script_type = script_type
        self._lines = lines

    @property
    def script_type(self) -> str:
        """
        脚本类型
        :return:
        """
        return self._script_type

    @property
    def lines(self) -> List[str]:
        """
        脚本列表，按行进行切割
        :return:
        """
        return self._lines


class RequestPre(object):
    """
    请求前置过程抽象
    """

    def __init__(self, event: str, script: EventScript):
        self._event = event
        self._script = script

    @property
    def event(self) -> str:
        """
        事件类型
        :return:
        """
        return self._event

    @property
    def script(self) -> EventScript:
        """
        脚本数据
        :return:
        """
        return self._script


class RequestBody(object):
    """
    请求体抽象类
    """

    def __init__(self, mode: RequestType, data: Dict):
        self._mode = mode
        self._data = data

    @property
    def mode(self) -> RequestType:
        """
        请求体类型
        :return:
        """
        return self._mode

    @abstractmethod
    def content(self) -> Any:
        """
        请求体内容
        :return: 根据请求类型的不同返回不同类型的值
        """
        pass


class FormDataRequestBody(RequestBody):
    """
    表单请求体类型对象
    """

    def __init__(self, data: Dict):
        super().__init__(RequestType.FORM_DATA, data)

    def content(self) -> Any:
        return self._data


class UrlEncodedRequestBody(RequestBody):
    """
    url encode 请求体类型对象
    """

    def __init__(self, data: Dict):
        super().__init__(RequestType.X_WWW_FORM_URLENCODED, data)

    def content(self) -> Any:
        return '&'.join(['{k}={v}'.format(k=k, v=v) for k, v in self._data.items()])


class RawRequestBody(RequestBody):
    """
    json 字符串类型请求体对象
    """

    def __init__(self, data: Dict):
        super().__init__(RequestType.RAW, data)

    def content(self) -> Any:
        return json.dumps(self._data)


class RequestCase(object):
    """
    请求对象，将请求进行抽象
    """

    def __init__(self, name: str, host: str, uri: str, method: str,
                 headers: Dict, query: Dict = None, params: Dict = None,
                 body: RequestBody = None, expect_result: bool = True):
        self._name = name
        self._host = host
        self._uri = uri
        self._method = method
        self._headers = headers
        self._query = query
        self._params = params
        self._body = body
        self._expect_result = expect_result

    @property
    def name(self) -> str:
        return self._name

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def host(self) -> str:
        return self._host

    @property
    def method(self) -> str:
        return self._method

    @property
    def headers(self) -> Dict:
        return self._headers

    @property
    def query(self) -> Dict:
        return self._query

    @property
    def params(self) -> Dict:
        return self._params

    @property
    def body(self) -> RequestBody:
        return self._body

    @property
    def expect_result(self) -> bool:
        return self._expect_result


class ResponseCase(object):
    pass


class ApiParser(object):
    """
    解析器，用于将自定义的 json 文件转换为请求对象
    """

    def __init__(self, host: str, dir_url: str):
        self._host = host
        self._dir_url = dir_url

    def get_all_files(self):
        file_paths = []

        def loop_file(url):
            for f_url in os.listdir(url):
                file_path = os.path.join(url, f_url)
                if os.path.isdir(file_path):
                    loop_file(file_path)
                elif '.json' in file_path:
                    file_paths.append(file_path)

        loop_file(self._dir_url)
        return file_paths

    def _parse_get_json_data(self, name: str, uri: str, data: Dict) -> List[RequestCase]:
        """
        解析操作为 get 的 json 数据
        :param name:
        :param uri:
        :param data:
        :return:
        """
        params = data.get('params')
        if params is None:
            raise ValueError("GET case can't found params data")

        if not params:
            data_name = data.get('name')
            data_uri = data.get('uri')
            return [RequestCase(
                name='{name}_true_{date}'.format(name=name if data_name is None else data_name,
                                                 date=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')),
                host=self._host,
                uri=uri if data_uri is None else data_uri,
                method=hdrs.METH_GET,
                headers=data.get('headers'),
                params={},
                query=data.get('query'),
                expect_result=True
            )]

        cases = []
        for flag in ['true', 'false']:
            for pa in self.create_params(params, flag):
                data_name = data.get('name')
                data_uri = data.get('uri')
                cases.append(RequestCase(
                    name='{name}_{flag}_{date}'.format(name=name if data_name is None else data_name,
                                                       flag=flag,
                                                       date=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')),
                    host=self._host,
                    uri=uri if data_uri is None else data_uri,
                    method=hdrs.METH_GET,
                    headers=data.get('headers'),
                    params=pa,
                    query=data.get('query'),
                    expect_result=True if flag == 'true' else False
                ))
        return cases

    def _parse_post_json_data(self, name: str, uri: str, data: Dict) -> List[RequestCase]:
        """
        解析操作为 post 的 json 数据
        :param name:
        :param uri:
        :param data:
        :return:
        """
        body = data.get('body')
        if body is None:
            raise ValueError("POST case can't found body data")

        cases = []
        for flag in ['true', 'false']:
            for pa in self.create_params(body['data'], flag):
                data_name = data.get('name')
                data_uri = data.get('uri')
                mode = body['mode']
                body_obj = None
                if mode == RequestType.FORM_DATA.value:
                    body_obj = FormDataRequestBody(pa)
                elif mode == RequestType.X_WWW_FORM_URLENCODED.value:
                    body_obj = UrlEncodedRequestBody(pa)
                elif mode == RequestType.RAW.value:
                    body_obj = RawRequestBody(pa)
                cases.append(RequestCase(
                    name='{name}_{flag}_{date}'.format(name=name if data_name is None else data_name,
                                                       flag=flag,
                                                       date=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')),
                    host=self._host,
                    uri=uri if data_uri is None else data_uri,
                    method=hdrs.METH_POST,
                    headers=data.get('headers'),
                    query=data.get('query'),
                    body=body_obj,
                    expect_result=True if flag == 'true' else False
                ))

        return cases

    def parse_json_data(self, name: str, uri: str, data: Dict) -> List[RequestCase]:
        """
        解析 json 数据过程
        :param name:
        :param uri:
        :param data:
        :return:
        """
        method = data.get('method')
        if method is None:
            raise ValueError("can't found method in case json file with: {}".format(name))

        method = method.upper()

        if method == hdrs.METH_GET:
            return self._parse_get_json_data(name, uri, data)

        if method == hdrs.METH_POST:
            return self._parse_post_json_data(name, uri, data)

    @staticmethod
    def parse_event_data(uri: str, data: Dict) -> List[RequestPre]:
        """
        解析事件数据
        :param uri:
        :param data:
        :return:
        """
        if 'prerequest' not in data and 'test' not in data:
            raise ValueError("can't found script flag in json file:{}".format(uri))
        return [RequestPre(
            event=k, script=EventScript(
                script_type=v['type'],
                lines=v['exec']
            )
        ) for k, v in data.items()]

    def create_request_cases(self) -> Dict[str, List]:
        """
        构建并返回请求对象并返回
        :return:
        """
        groups = {}
        for case_path in self.get_all_files():
            with open(case_path, encoding='utf-8') as case_f:
                json_data = json.load(case_f)
                file_path = case_path.replace(self._dir_url, '').replace('.json', '')
                if file_path == '/prerequest' or (platform.system().lower() == 'windows' and file_path == 'prerequest'):
                    groups['prerequest'] = self.parse_event_data(file_path, json_data)
                    continue

                uri = file_path
                if platform.system().lower() == 'windows':
                    uri = '/{}'.format('/'.join(uri.split('\\')))
                    uri = uri.replace('//', '/')

                code = hashlib.md5(str(json_data).encode(encoding='utf-8')).hexdigest()
                groups['{path}@{code}'.format(path=uri, code=code)] = self.parse_json_data(
                    name=uri,
                    uri=uri,
                    data=json_data)
        return groups

    @staticmethod
    def same_removal(data: List[Dict]):
        temp = []
        for d in data:
            temp += [] if d in temp else [d]
        return temp

    def create_params(self, params: Dict, flag: str) -> List[Dict]:
        """
        对参数进行解析
        :param params:
        :param flag:
        :return:
        """
        items_flag = []
        for k, v in {pk: pv[flag] for pk, pv in params.items()}.items():
            for real_v in v:
                json_params = {k: real_v}
                for kk, vv in {s_pk: s_pv[flag] for s_pk, s_pv in params.items() if s_pk != k}.items():
                    if not vv:
                        json_params[kk] = ''
                        continue
                    json_params[kk] = random.choice(vv)
                items_flag.append(json_params)

        new_items = self.same_removal(items_flag)
        return new_items


class FileParser(object):
    TYPE_RAW = 'text/plain;charset=UTF-8'
    TYPE_FORM_DATA = 'application/json;charset=UTF-8'

    def __init__(self, dir_path: str, file_path: str):
        self._file_path = file_path
        self._dir_path = dir_path

    # 过滤 .har 中的资源请求
    @staticmethod
    def stop_with(uri: str):
        for tag in ['.png', '.ico', '.gif', '.css', '.js', '/']:
            if uri.endswith(tag):
                return True

    def _init_root_dir(self):
        if not os.path.exists(self._dir_path) or not os.path.isdir(self._dir_path):
            os.makedirs(self._dir_path)

    def _load_file(self):
        # 载入 .har 文件
        with open(self._file_path, encoding='utf-8') as har_file:
            har_data = json.load(har_file)

        return har_data

    @abstractmethod
    def create_json(self):
        pass


class TemplateParser(FileParser):

    @abstractmethod
    def create_json(self):
        pass


class PostmanParser(FileParser):

    def __init__(self, dir_path: str, file_path: str, group_name: str):
        super().__init__(dir_path, file_path)
        self._group_name = group_name
        self._output_url = '.'

    def create_info(self) -> Dict:
        return {
            'name': self._group_name,
            'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
        }

    @staticmethod
    def create_case_events() -> List[Dict]:
        return [{
            "listen": "test",
            "script": {
                "exec": [
                    ""
                ],
                "type": "text/javascript"
            }
        }]

    @staticmethod
    def create_events() -> List[Dict]:
        return [
            {
                "listen": "prerequest",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        ""
                    ]
                }
            },
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        ""
                    ]
                }
            }
        ]

    @abstractmethod
    def create_json(self):
        pass


class Har2Template(TemplateParser):

    @staticmethod
    def _make_template_data(request_data: Dict):
        # template 数据
        request_method = request_data['method']
        template_data = {
            'method': request_method,
            'headers': {h['name']: h['value'] for h in request_data['headers']},
        }
        if request_method.upper() == hdrs.METH_GET:
            template_data['params'] = {
                q['name']: {
                    'true': [q['value']],
                    'false': []
                } for q in request_data['queryString']}
        if request_method.upper() == hdrs.METH_POST:
            post_data = request_data['postData']
            mode = 'formdata'
            mimetype = post_data['mimeType']
            if mimetype == FileParser.TYPE_FORM_DATA:
                mode = RequestType.FORM_DATA.value
            elif mimetype == FileParser.TYPE_RAW:
                mode = RequestType.RAW.value

            template_data.update({
                'query': {q['name']: q['value'] for q in request_data['queryString']}
            })
            body_data = json.loads(post_data['text'])
            if type(body_data) is dict:
                template_data.update(
                    {'body': {
                        'mode': mode,
                        'data': {k: {
                            'true': [v],
                            'false': []
                        } for k, v in body_data.items()}
                    }})

        return template_data

    def _create_template_json(self, uri: str, template_data: Dict):
        # 分割地址
        url_paths = uri.split('/')
        file_name = url_paths.pop(-1)
        file_path = '/'.join(url_paths)
        file_absolute_path = self._dir_path + file_path

        # 创建文件夹
        if not os.path.exists(file_absolute_path):
            os.makedirs(file_absolute_path)

        # 根据模板数据创建 .json 模板文件
        create_file_path = os.path.join(file_absolute_path, '{}.json'.format(file_name))
        if not os.path.exists(create_file_path):
            with open(create_file_path, 'w') as json_file:
                logging.info('%s-%s', '.har to json', 'output:{}'.format(create_file_path))
                json.dump(template_data, json_file)

    def create_json(self):
        har_data = self._load_file()
        entries_data = har_data['log']['entries']
        for d in entries_data:
            request_data = d['request']
            url_parse = urlparse(request_data['url'])
            logging.info('%s-%s', '.har to json', 'parse request url: {}'.format(request_data['url']))
            logging.info('%s-%s', '.har to json', 'path: {}'.format(url_parse.path))

            # 过滤条件
            if self.stop_with(url_parse.path):
                continue

            self._create_template_json(url_parse.path, self._make_template_data(request_data))


class Har2Postman(PostmanParser):

    def _url_check(self, entry: Dict) -> bool:
        url_parse = urlparse(entry['request']['url'])
        return self.stop_with(url_parse.path)

    @staticmethod
    def create_request(entry: Dict) -> Dict:
        request_data = entry['request']
        url_parse = urlparse(request_data['url'])
        postman_data = {
            'auth': {
                'type': 'noauth'
            },
            'method': request_data['method'],
            'header': [{
                'key': header['name'],
                'value': header['value']
            } for header in request_data['headers']],
            'url': {
                'raw': request_data['url'],
                'host': url_parse.hostname,
                'port': url_parse.port,
                'protocol': url_parse.scheme,
                'path': [p for p in url_parse.path.split('/') if p],
                'query': [{
                    'key': query['name'],
                    'value': query['value']
                } for query in request_data['queryString']]
            }
        }

        if request_data['method'] == hdrs.METH_POST:
            postman_data.update({
                'body': {
                    'mode': 'raw',
                    'raw': request_data['postData']['text'] if 'postData' in request_data else ''
                }
            })

        return postman_data

    def create_json(self):
        har_data = self._load_file()
        entries_data = har_data['log']['entries']

        json_data = {
            'info': self.create_info(),
            'item': [{
                'name': case['request']['url'],
                'event': self.create_case_events(),
                'request': self.create_request(case),
                'response': []
            } for case in entries_data if not self._url_check(case)],
            'event': self.create_events()
        }

        # 将结果文件输出到指定路径
        output_path = self._output_url
        if os.path.exists(self._output_url) and os.path.isdir(self._output_url):
            output_path = os.path.join(self._output_url, self._group_name)
        if '.json' not in output_path:
            output_path = '{}.json'.format(output_path)

        with open(output_path, 'w') as f:
            logging.info('%s-%s', '.har to json', 'output:{}'.format(output_path))
            json.dump(json_data, f)


class Json2Template(TemplateParser):

    @staticmethod
    def _make_template_data(request_data: Dict):
        # template 数据
        request_method = 'POST' if request_data['baseInfo']['apiRequestType'] == 0 else 'GET'
        template_data = {
            'method': request_method,
            'headers': {h['headerName']: h['headerValue'] for h in request_data['headerInfo']},
        }
        if request_method.upper() == hdrs.METH_GET:
            params_data = {
                q['paramKey']: {
                    'true': [q['paramValue']],
                    'false': []
                } for q in request_data['requestInfo']}
            params_data.update({
                q['paramKey']: {
                    'true': [q['paramValue']],
                    'false': []
                } for q in request_data['urlParam']})
            template_data['params'] = params_data
        if request_method.upper() == hdrs.METH_POST:
            mode = 'raw'
            param_type = request_data['baseInfo']['apiRequestParamType']
            if param_type == 0:
                mode = RequestType.FORM_DATA.value
            elif param_type == 1:
                mode = RequestType.RAW.value
            template_data.update({
                'query': {q['paramKey']: q['paramValue'] for q in request_data['urlParam']},
                'body': {
                    'mode': mode,
                    'data': {info['paramKey']: {
                        'true': [info['paramValue']],
                        'false': []
                    } for info in request_data['requestInfo']}
                }
            })

        return template_data

    def _create_template_json(self, uri: str, template_data: Dict):
        # 分割地址
        if '{{' in uri and '}}' in uri:
            uri = uri.split('}}')[-1]
        if not uri.startswith('/'):
            uri = '/' + uri
        url_paths = uri.split('/')
        file_name = url_paths.pop(-1)
        file_path = '/'.join(url_paths)
        file_absolute_path = self._dir_path + file_path

        # 创建文件夹
        if not os.path.exists(file_absolute_path):
            os.makedirs(file_absolute_path)

        # 根据模板数据创建 .json 模板文件
        create_file_path = os.path.join(file_absolute_path, '{}.json'.format(file_name))
        if not os.path.exists(create_file_path):
            with open(create_file_path, 'w') as json_file:
                logging.info('%s-%s', '.har to json', 'output:{}'.format(create_file_path))
                json.dump(template_data, json_file)

    def create_json(self):
        entries_data = self._load_file()
        for request_data in entries_data:
            if request_data['baseInfo']['apiStatus'] != 0:
                continue
            request_url = request_data['baseInfo']['apiURI']
            url_parse = urlparse(request_url)
            logging.info('%s-%s', '.har to json', 'parse request url: {}'.format(request_url))
            logging.info('%s-%s', '.har to json', 'path: {}'.format(url_parse.path))

            self._create_template_json(url_parse.path, self._make_template_data(request_data))


class Json2Postman(PostmanParser):

    @staticmethod
    def create_request(request_data: Dict) -> Dict:
        url_parse = urlparse(request_data['baseInfo']['apiURI'])
        request_method = 'POST' if request_data['baseInfo']['apiRequestType'] == 0 else 'GET'
        postman_data = {
            'auth': {
                'type': 'noauth'
            },
            'method': request_method,
            'header': [{
                'key': header['headerName'],
                'value': header['headerValue']
            } for header in request_data['headerInfo']],
            'url': {
                'raw': request_data['baseInfo']['apiURI'],
                'host': '{{eolinker_host}}',
                'port': url_parse.port,
                'protocol': url_parse.scheme,
                'path': [p for p in url_parse.path.split('/') if p],
                'query': [{
                    'key': query['paramKey'],
                    'value': query['paramValue']
                } for query in request_data['urlParam']]
            }
        }

        if request_method == hdrs.METH_POST:
            postman_data.update({
                'body': {
                    'mode': 'raw',
                    'raw': json.dumps({
                        param['paramKey']: param['paramValue'] for param in request_data['requestInfo']
                    })
                }
            })

        return postman_data

    def create_json(self):
        entries_data = self._load_file()

        json_data = {
            'info': self.create_info(),
            'item': [{
                'name': case['baseInfo']['apiURI'],
                'event': self.create_case_events(),
                'request': self.create_request(case),
                'response': []
            } for case in entries_data],
            'event': self.create_events()
        }

        # 将结果文件输出到指定路径
        output_path = self._output_url
        if os.path.exists(self._output_url) and os.path.isdir(self._output_url):
            output_path = os.path.join(self._output_url, self._group_name)
        if '.json' not in output_path:
            output_path = '{}_eolinker_to_postman.json.json'.format(output_path)
        else:
            output_path = '{}_eolinker_to_postman.json'.format(output_path.replace('.json', ''))

        with open(output_path, 'w') as f:
            logging.info('%s-%s', 'eolinker file .json to json', 'output:{}'.format(output_path))
            json.dump(json_data, f)
