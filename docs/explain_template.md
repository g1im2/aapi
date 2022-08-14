# 模板文件语法规则

## 用例构建文件说明

用例构建文件，用来填写请求参数的等价类值和边界值集合，根据以下规则进行文件的配置，就能快速构建 postman 或者 eolinker 自动化测试用例。

## 目录编排规则

 - 规则：uri 的层级关系即目录结构
 - 最外层存放 prequest.json 用来配置前置或者后置脚本

### 示例

假设一个 api 的 uri 为 /erp/sc/data/mws/listing，那么我们可以构建与 uri 的层级关系相同的目录层级关系，最后的资源名为 json 文件，即文件相对路径为 ./erp/sc/data/mws/listing.json

```shell
# /erp/sc/data/mws/listing
├── erp
│   └── sc
│       └── data
│           └── mws
│               └── listing.json
└── prerequest.json  # 前置脚本文件

```

## 模板文件规则说明

请求模板文件采用 http 协议的 json 文本来展示，标签规则根据 http 协议来命名。

### 标签

 - **method**：请求方法
 - **event**：请求事件（脚本事件等）
 - **headers**：请求头
 - **query**：请求参数
 - **params（选填）**：当请求方法为 get 时选填该选项
 - **body（选填）**：当请求方法为 post 是选填该选项

### method

method 标签为请求方法，这里只支持 get 和 post 方法

```json
{
  "method": "get"
}
```

### event

event 标签为请求事件，用于设置自动化脚本

```json
{
  "event": {
      "prerequest": {
        "type": "text/javascript",
        "exec": [
          "console.log(\"hello world\")",
          "console.log(\"halo\")"
        ]
    }
  }
}
```

### headers

headers 标签为请求头

```json
{
  "headers": {
    "Accept": "*/*",
    "Accept-Encoding": "gzip,deflate,br",
    "Connection": "keep-alive",
    "Content-Type": "application/json,text/plain,*/*"
  }
}
```

### query

query 为请求参数，该参数直接携带，不参与配置组合，也就是说，每次生成的请求都会携带该参数

```json
{
  "query": {
    "timestamp": "{{timestamp}}",
    "ak_test_ip": "{{ak_test_ip}}",
    "access_token": "{{access_token}}",
    "app_key": "{{appId}}",
    "sign": "{{sign}}"
  }
}
```

### 参数化配置说明

在该配置文件格式中，我们将 params 和 body 设置为参数信息存放槽。它们的参数信息全部都存放在字典里，这里的字典，需要设置两个参数，一个为 true 字段，另一个为 false 字段，这两个字段存放的数据类型为列表。

 - **true**：存放的是请求正确的参数列表，列表中的值的个数最小为1，最大暂时没有做限制
 - **false**：存放的是请求错误的参数列表，列表中的值的个数最小为1，最大暂时没有做限制

### params

在请求方法（method）为 get 时，使用该字段进行参数化配置。如下，

#### 格式

**param_name** 为 key，这里的 value 统一为字典格式，字典里包含两个字段 **"true"** 和 **"false"** ，值为列表格式。

```json
{
  "params": {
    "param_name": {
      "true": [],
      "false": []
    }
  }
}
```

#### 示例

```json
{
  "params": {
    "page": {
      "true": ["1", "2"],
      "false": ["100", "200"]
    },
    "sid_arr": {
      "true": [
        ["1", "2"],
        ["3", "1"]
      ],
      "false": [
        ["11", "22"],
        ["33"]
      ]
    }
  }
}
```

### body

在请求方法（method）为 get 时，使用该字段进行参数化配置。如下

#### 格式

 - **mode**：请求体为什么类型的，这里支持 **raw**、**formdata**、**urlencode** 三种格式类型
 - **param_name**: 为 key，这里的 value 统一为字典格式，字典里包含两个字段 **"true"** 和 **"false"** ，值为列表格式。

```json
{
  "body": {
    "mode": "[raw\formdata\urlencode]",
    "data": {
      "param_name": {
      "true": [],
      "false": []
    }
    }
  }
}
```

#### 示例

```json
{
    "body": {
    "mode": "raw",
    "data": {
      "sid": {
        "true": [32, 32],
        "false": [0, 99999]
      },
      "is_pair": {
        "true": [1, 1],
        "false": [0, 0]
      },
      "offset": {
        "true": [0, 0],
        "false": [1, 100, -1]
      },
      "length": {
        "true": [10000, 10000],
        "false": [11, 23]
      }
    }
  }
}
```

### 范例

```python
{
  "method": "get",  # http 操作方法，支持 get 和 post
  "headers": {},  # 请求头
  "query": {},  # 请求参数
  
  # 以下为用例可能值的填写
  "params": {},  # 需要配置的参数
  "body": {}  # 需要配置请求体参数
}
```

### post 示例

```json
{
  "method": "post",
  "headers": {
    "Accept": "*/*",
    "Accept-Encoding": "gzip,deflate,br",
    "Connection": "keep-alive",
    "Content-Type": "application/json,text/plain,*/*"
  },
  "query": {
    "timestamp": "{{timestamp}}",
    "ak_test_ip": "{{ak_test_ip}}",
    "access_token": "{{access_token}}",
    "app_key": "{{appId}}",
    "sign": "{{sign}}"
  },
  "body": {
    "mode": "raw",
    "data": {
      "sid": {
        "true": [32],
        "false": [0, 99999]
      },
      "is_pair": {
        "true": [1],
        "false": [0, 0]
      },
      "offset": {
        "true": [0, 0],
        "false": [1, 100, -1]
      },
      "length": {
        "true": [10000],
        "false": [11, 23]
      }
    }
  }
}
```

### get 方法的示例

```json
{
  "method": "get",
  "headers": {
    "Accept": "*/*",
    "Accept-Encoding": "gzip,deflate,br",
    "Connection": "keep-alive",
    "Content-Type": "application/json,text/plain,*/*"
  },
  "query": {
    "timestamp": "{{timestamp}}",
    "ak_test_ip": "{{ak_test_ip}}",
    "access_token": "{{access_token}}",
    "app_key": "{{appId}}",
    "sign": "{{sign}}"
  },
  "params": {
      "sid": {
        "true": [32, 32],
        "false": [0, 99999]
      },
      "is_pair": {
        "true": [1, 1],
        "false": [0, 0]
      },
      "offset": {
        "true": [0, 0],
        "false": [1, 100, -1]
      },
      "length": {
        "true": [10000, 10000],
        "false": [11, 23]
      }
  }
}
```