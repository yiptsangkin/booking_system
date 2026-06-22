# 经销商油漆下单系统

完整的 B2B 经销商油漆下单、仓储发货、多物流对接、物流轨迹和签收 POD 闭环系统。

## 目录

```text
backend/   FastAPI + SQLAlchemy
frontend/  Vue 3 + Vite + Pinia + Vue Router + 项目内管理控件样式
```

## 后端本地运行

```bash
cd /Users/administrator/Documents/project/booking_system
./scripts/start_backend_crp.sh
```

脚本默认使用 `conda run -n crp`，监听 `127.0.0.1:8000`。需要改端口可用 `BACKEND_PORT=8001 ./scripts/start_backend_crp.sh`；需要热更新可加 `BACKEND_RELOAD=1`。

默认数据库是 `sqlite:///./dev.db`。生产 MySQL 可改为：

```text
DATABASE_URL=mysql+pymysql://user:pass@host/db
```

## 前端本地运行

```bash
cd /Users/administrator/Documents/project/booking_system
./scripts/start_frontend.sh
```

默认登录账号：

```text
dealer@example.com / dealer123
admin@example.com / admin123
```

## 真实物流 API 配置

系统没有 mock 发货。`POST /api/shipments/create` 会调用所选物流公司的真实 HTTP 端点，缺少凭据或 URL 时会返回错误。

需要在 `backend/.env` 配置：

- 发货仓：`SHIPPER_NAME`、`SHIPPER_PHONE`、`SHIPPER_ADDRESS`
- 顺丰丰桥：`SF_PARTNER_ID`、`SF_CHECK_WORD`、`SF_GATEWAY_URL`、`SF_CREATE_SERVICE_CODE`、`SF_TRACK_SERVICE_CODE`、`SF_WEBHOOK_SECRET`
- 京东 JOS：`JD_APP_KEY`、`JD_APP_SECRET`、`JD_GATEWAY_URL`、`JD_CREATE_METHOD`、`JD_TRACK_METHOD`、`JD_ACCESS_TOKEN`
- 一米滴答：`YIMI_APP_KEY`、`YIMI_APP_SECRET`、`YIMI_GATEWAY_URL`、`YIMI_CREATE_METHOD`、`YIMI_TRACK_METHOD`、`YIMI_WEBHOOK_SECRET`

公开资料核对后的实现口径：

- 顺丰开放平台公开入口是 `https://open.sf-express.com/`。代码优先使用丰桥标准网关结构：`partnerID`、`requestID`、`serviceCode`、`timestamp`、`msgDigest`、`msgData`；`msgDigest` 由 `msgData + timestamp + checkWord` 计算。默认生产网关为 `https://sfapi.sf-express.com/std/service`。
- 京东物流官网提供企业物流服务入口，开放 API 通常走京东开放平台/宙斯体系。代码支持 JOS 网关参数：`method`、`app_key`、`access_token`、`timestamp`、`format`、`v`、`sign_method`、`360buy_param_json`、`sign`；`sign` 由 appSecret 包裹排序参数后 MD5 大写生成。
- 壹米滴答官网公开页没有抓到无需登录的开发文档入口，因此代码不硬编码未经确认的字段；按商务/服务商提供的 REST 网关方法名配置 `YIMI_CREATE_METHOD`、`YIMI_TRACK_METHOD`，请求里统一带 `appKey`、`timestamp`、`sign`、业务 `data`。

实现位置：

- `backend/app/carriers/sf.py`
- `backend/app/carriers/jd.py`
- `backend/app/carriers/yimi.py`
- `backend/app/carriers/base.py`
- `backend/app/carriers/dispatcher.py`

这些实现包含 request/header 构造、MD5 或 HMAC-SHA256 签名、OAuth2 token、响应解析、retry 和错误处理。

顺丰与京东的企业文档经常需要登录应用后台查看具体 `serviceCode` 或 `method`。如果你拿到企业账号文档，只需要把方法名、网关地址和凭据写进 `.env`，不用改业务流程。

调研和配置说明见 `docs/logistics-integration-notes.md`。

## API

```text
POST /api/auth/login
GET  /api/products
GET  /api/products/families
GET  /api/products/colors
POST /api/products
PATCH /api/products/{id}
POST /api/products/{id}/stock
POST /api/orders
GET  /api/orders
GET  /api/orders/{order_no}
POST /api/orders/{order_no}/complete
POST /api/shipments/create
POST /api/shipments/{id}/bind
POST /api/shipments/{id}/status
POST /api/shipments/{id}/pod
GET  /api/tracking/{order_no}
GET  /api/tracking/{order_no}?sync=true
POST /api/webhook/logistics/status
POST /api/webhook/logistics/pod
```

订单状态机强制：

```text
已创建 -> 已分配库存 -> 已发货 -> 运输中 -> 已签收 -> 已完成
```

API 响应中 `status` 为中文状态，`status_code` 为内部状态码。禁止跳跃状态，非法流转会返回 `409`。

订单对外只使用业务订单号 `order_no`，格式为日期加当日序号，例如 `PO202606220001`；数据库内部自增 `id` 不作为前端路由或业务接口参数使用。

核心业务约束：

- 商品主数据拆成“商品款式”和“色号 SKU”：`product_families` 维护款式，`products.family_id` 关联具体色号、价格和库存。
- 前端商品页按 `family_id` 展示同一款油漆的多个色号，不按商品名称做临时聚合。
- 库存页按商品款式展示，一款商品一行；进入“管理色号”后维护该商品下的多个 SKU。
- 色号维护包含色号名称输入和 color picker 色值选择，色值保存到 `products.color_hex`，前端只使用接口返回值展示色卡。
- 只有经销商角色可以提交订单；管理员负责库存、发货和物流回传。
- 下单时立即校验并扣减库存，订单进入“已分配库存”。
- 一个订单只能生成或绑定一个运单，重复发货会返回 `409`。
- 同一承运商下运单号不能重复。
- 真实物流同步只能由管理员触发；经销商只能查看已有轨迹。
- 只有已签收订单能由所属经销商确认完成；完成后不能再写入轨迹或 POD。

## POD 要求

`POST /api/webhook/logistics/pod` 必须传入：

```json
{
  "carrier": "sf",
  "tracking_no": "SF123",
  "order_no": "PO202606220001",
  "image_url": "https://oss.example.com/pod/SF123.jpg",
  "signed_at": "2026-06-22T12:00:00Z",
  "gps_location": "31.2304,121.4737"
}
```

图片只保存 OSS/http(s) URL，不使用本地文件存储。

## Vercel

`vercel.json` 已配置：

- `/api/*` 路由到 FastAPI serverless 入口 `backend/api/index.py`
- 前端由 `frontend/package.json` 静态构建

Vercel 环境变量中应配置 MySQL `DATABASE_URL` 和真实物流凭据。SQLite 适合本地默认运行，不适合作为 Vercel 持久化生产库。

临时演示如果不接外部数据库，可以把仓库内的 `backend/dev.db` 作为初始演示数据库，并在 Vercel 环境变量中配置：

```env
DATABASE_URL=sqlite:////tmp/paint_order_demo.db
AUTH_SECRET=replace-with-a-long-random-secret
```

启动时后端会把 `backend/dev.db` 复制到 `/tmp/paint_order_demo.db`。这种方式只适合演示，Vercel 重部署或实例切换后数据可能回到初始数据库。

## 验收脚本

启动后端：

```bash
cd /Users/administrator/Documents/project/booking_system
./scripts/start_backend_crp.sh
```

后端进程内端到端测试，不绑定端口、不调用真实快递：

```bash
cd /Users/administrator/Documents/project/booking_system
conda run -n crp python scripts/test_backend_inprocess.py
```

本地业务闭环，不调用承运商下单接口，适合先验系统状态机、webhook、POD：

```bash
cd /Users/administrator/Documents/project/booking_system
conda run -n crp python scripts/smoke_local_flow.py
```

真实承运商下单接口，必须先配置对应物流 `.env`：

```bash
cd /Users/administrator/Documents/project/booking_system
conda run -n crp python scripts/real_carrier_flow.py --carrier sf --sync-tracking
```

前端构建：

```bash
cd /Users/administrator/Documents/project/booking_system
./scripts/run_frontend_build.sh
```

如果 npm 被本机代理变量卡住，可临时去掉代理再安装：

```bash
cd /Users/administrator/Documents/project/booking_system/frontend
env -u http_proxy -u https_proxy -u all_proxy npm install --registry=https://registry.npmmirror.com
npm run build
```

## 前端功能

- 经销商：登录、商品筛选、按款式选择色号、加入购物车、提交订单、查看订单列表和订单详情、查看物流轨迹和 POD。
- 管理员：查看全部订单、调用真实物流创建发货单、在未接入真实物流时手工绑定运单、录入轨迹、录入 POD、按 SKU 维护商品色号/价格/分类/库存。
- UI：顶部支持主题切换，主题会保存在本地浏览器中。
