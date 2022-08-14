import json
import logging
import os
from abc import abstractmethod
from typing import (
    Dict,
    List,
    Any
)

from aapi import (
    RequestPre,
    RequestBody,
    RequestType,
    RequestCase
)


class ApiCreator(object):

    def __init__(self):
        pass

    @abstractmethod
    def create_apis(self, groups: Dict[str, Any]) -> Any:
        pass


class PostmanCreator(ApiCreator):

    def __init__(self, name, output_url: str):
        super().__init__()
        self._name = name
        self._output_url = output_url

    def create_info(self) -> Dict:
        return {
            'name': self._name,
            'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
        }

    @staticmethod
    def create_case_events(case: RequestCase) -> List[Dict]:
        return [{
            "listen": "test",
            "script": {
                "exec": [
                    "pm.test(\"返回处理码为 1\", function () {",
                    "    var jsonData = pm.response.json();",
                    "    pm.expect(jsonData.code).to.eql({result});".format(
                        result="1" if case.expect_result else "0"),
                    "});"
                ],
                "type": "text/javascript"
            }
        }]

    @staticmethod
    def create_events(prerequests: List[RequestPre] = None) -> List[Dict]:
        if prerequests is None:
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
        return [{
            'listen': r.event,
            'script': {
                'type': r.script.script_type,
                'exec': r.script.lines
            }
        } for r in prerequests]

    @staticmethod
    def create_body(body: RequestBody) -> Any:
        if body.mode == RequestType.FORM_DATA:
            contents = []
            data = body.content()
            file_data = data.get('files')
            if file_data is not None:
                contents.extend([{
                    'key': fk,
                    'type': 'file',
                    'src': fs
                } for fk, fs in body.content()['files'].items()])
                data.remove('files')
            contents.extend([{
                'key': dk,
                'type': 'text',
                'value': dv
            } for dk, dv in data.items()])
            return contents
        elif body.mode == RequestType.RAW:
            return body.content()
        elif body.mode == RequestType.X_WWW_FORM_URLENCODED:
            items = []
            for v in body.content().split('&'):
                item = {'type': 'text'}
                vs = v.split('=')
                if len(vs) == 1:
                    item.update({
                        'key': vs[0],
                        'value': ''
                    })
                elif len(vs) == 2:
                    item.update({
                        'key': vs[0],
                        'value': vs[1]
                    })
                items.append(item)
            return items

    def create_request(self, request_case: RequestCase) -> Dict:
        request_content = {
            'auth': {
                'type': 'noauth'
            },
            'method': request_case.method,
            'header': [{
                'key': hk,
                'value': hv
            } for hk, hv in request_case.headers.items()],
            'url': {
                'raw': '{host}{api}?{query}'.format(
                    host=request_case.host,
                    api=request_case.uri,
                    query='&'.join(['{k}={v}'.format(k=k, v=v) for k, v in request_case.query.items()])
                ) if request_case.query is not None else '{host}{api}'.format(
                    host=request_case.host,
                    api=request_case.uri
                ),
                'host': request_case.host,
                'path': [p for p in request_case.uri.split('/') if p]
            }
        }

        if request_case.body is not None:
            request_content['body'] = {
                'mode': request_case.body.mode.value,
                request_case.body.mode.value: self.create_body(request_case.body)
            }

        if request_case.query is not None:
            request_content['url']['query'] = [{
                'key': qk,
                'value': str(qv)
            } for qk, qv in request_case.query.items()]

        if request_case.params is not None:
            query_values = [{
                'key': qk,
                'value': str(qv)
            } for qk, qv in request_case.params.items()]
            if 'params' in request_content['url']:
                request_content['url']['query'].extend(query_values)
            else:
                request_content['url']['query'] = query_values

        return request_content

    @staticmethod
    def create_response() -> list:
        return []

    def create_apis(self, groups: Dict[str, Any]) -> Any:
        event_data = groups.get('prerequest')
        if event_data is None:
            event = self.create_events()
        else:
            event = self.create_events(event_data)
            del groups['prerequest']

        json_data = {
            'info': self.create_info(),
            'item': [{
                'name': name,
                'item': [{
                    'name': case.name,
                    'event': self.create_case_events(case),
                    'request': self.create_request(case),
                    'response': self.create_response()
                } for case in data]
            } for name, data in groups.items()],
            'event': event
        }

        # 将结果文件输出到指定路径
        output_path = self._output_url
        if os.path.exists(self._output_url) and os.path.isdir(self._output_url):
            output_path = os.path.join(self._output_url, self._name)
        if '.json' not in output_path:
            output_path = '{}.json'.format(output_path)

        with open(output_path, 'w') as f:
            logging.info('%s-%s', 'Convert Case', 'output: {}'.format(output_path))
            json.dump(json_data, f)

