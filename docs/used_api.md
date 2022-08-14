# 用例拓展

 - 通过 .har 文件生成请求用例模板

```python
def create_template():
    parser = HarParser('./example', 'browsertime.har')
    parser.create_template()


if __name__ == '__main__':
    create_template()
```

 - 生成 postman 的请求文件

```python
def create_postman_case():
    host = 'http://127.0.0.1'
    dict_url = '../file'
    parser = ApiParser(host=host, dir_url=dict_url)
    creator = PostmanCreator(name='file',
                             output_url='../output')
    creator.create_apis(parser.create_request_cases())

if __name__ == '__main__':
    main()
```

