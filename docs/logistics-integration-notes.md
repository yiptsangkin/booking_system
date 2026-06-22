# 物流对接公开资料调研

## 顺丰

公开入口：`https://open.sf-express.com/`

代码实现：`backend/app/carriers/sf.py`

实现口径：

- 优先使用丰桥标准网关：`SF_GATEWAY_URL=https://sfapi.sf-express.com/std/service`
- 请求字段：`partnerID`、`requestID`、`serviceCode`、`timestamp`、`msgDigest`、`msgData`
- 签名：`Base64(MD5(urlencode(msgData + timestamp + checkWord)))`
- 下单默认服务码：`EXP_RECE_CREATE_ORDER`
- 路由默认服务码：`EXP_RECE_SEARCH_ROUTES`
- 兼容企业定制 JSON 网关：`SF_APP_ID`、`SF_APP_SECRET`、`SF_API_URL`、`SF_TRACK_URL`

需要企业后台确认：

- 生产/沙箱网关地址
- 月结号、付款方式、产品类型
- 是否有自定义 `serviceCode`
- webhook 签名头名称和签名规则

## 京东物流

公开入口：

- 京东物流官网：`https://www.jdl.com/`
- 京东开放平台/宙斯开发者中心：`https://jos.jd.com/`

代码实现：`backend/app/carriers/jd.py`

实现口径：

- 支持 JOS 网关：`JD_GATEWAY_URL=https://api.jd.com/routerjson`
- 请求字段：`method`、`app_key`、`access_token`、`timestamp`、`format`、`v`、`sign_method`、`360buy_param_json`、`sign`
- 签名：appSecret + 排序参数键值串 + appSecret，再 MD5 大写
- 访问令牌：优先使用 `JD_ACCESS_TOKEN`；如企业提供 token 刷新接口，再用 `JD_TOKEN_URL` / `JD_REFRESH_TOKEN`
- 兼容独立 OAuth JSON 网关：`JD_API_URL`、`JD_TRACK_URL`

需要企业后台确认：

- 下单 API 的 `method`
- 轨迹 API 的 `method`
- access token 获取/刷新方式
- 回包中运单号字段

## 壹米滴答

公开入口：`https://www.yimidida.com/`

代码实现：`backend/app/carriers/yimi.py`

实现口径：

- 公开官网没有暴露无需登录可抓取的开发文档入口，所以不硬编码未经确认的字段名。
- 适配器按零担物流常见 REST 网关实现：`method`、`appKey`、`timestamp`、`sign`、`data`
- 签名：`appKey + timestamp + body + secret` 组合后 MD5 大写
- 可通过 `YIMI_GATEWAY_URL`、`YIMI_CREATE_METHOD`、`YIMI_TRACK_METHOD` 配置方法名
- 兼容企业提供的固定 REST URL：`YIMI_API_URL`、`YIMI_TRACK_URL`

需要企业后台确认：

- 是否提供开放平台账号或服务商接口文档
- 下单/轨迹 URL 或 method
- 签名串拼接顺序
- webhook 签名规则
