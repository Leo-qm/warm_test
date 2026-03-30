# WARM 前端代码分析报告 — 自动化测试准备

## 1. 技术栈概览

| 分类 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue 2 | 2.6.14 |
| UI 库 | Element UI | ^2.15.6 |
| 状态管理 | Vuex | ^3.6.2 |
| 路由 | Vue Router (hash 模式) | ^3.5.3 |
| HTTP | Axios | ^0.24.0 |
| 树形选择 | @riophae/vue-treeselect | 0.4.0 |
| 图表 | ECharts + vue-echarts | 5.4.2 / 6.5.5 |
| 构建工具 | Vue CLI | ~4.5.0 |
| CSS 预处理 | SCSS / LESS | — |
| 国际化 | vue-i18n | ^8.28.2 |

---

## 2. 路由与页面结构

### 2.1 路由模式
- **Hash 模式** (`http://domain/#/path`)
- 登录后通过 `store.dispatch('GenerateRoutes')` 动态注入业务路由

### 2.2 核心路由

| 路由路径 | 路由名称 | 功能说明 | 测试优先级 |
|----------|----------|----------|------------|
| `/admin` | LoginAdmin | 管理端登录页 (验证码登录) | ✅ 已覆盖 |
| `/login` | Login | 普通登录页 | ✅ 已覆盖 |
| `/sso-callback` | SsoCallback | SSO 单点登录回调 | ⬜ 未覆盖 |
| `/home` | HomeIndex | 门户首页 | ✅ 已覆盖 |
| `/` | LayoutHome | 布局根页面 → 重定向 `/home` | — |
| `/403` | 403 | 权限不足页面 | ⬜ 未覆盖 |

### 2.3 动态路由（业务菜单生成）

菜单通过后端接口 `GenerateRoutes` 动态加载，核心业务路由位于 `cleanEnergy` 模块下：

```
清洁能源 (顶部菜单)
└── 清洁取暖设备申报管理 (el-submenu)
    ├── 新增申报信息管理 (el-menu-item) ← add/index.vue
    ├── 申报审核管理 (el-menu-item) ← audit/index.vue  
    ├── 设备申报台账管理 (el-menu-item) ← ledger/index.vue
    ├── 历史台账查询 (el-menu-item) ← historicalLedger
    ├── 历史审核管理 (el-menu-item) ← historicalExamine
    ├── 历史数据查询 (el-menu-item) ← historicalQuery
    ├── 补贴配置管理 (el-menu-item) ← subsidyConfig
    ├── 代理人管理 (el-menu-item) ← agentManage
    ├── 厂家信息管理 (el-menu-item) ← manufactureInfoManage
    └── 抽查审核 (el-menu-item) ← spotCheckAudit
```

---

## 3. 核心业务页面 — UI 组件与表单字段映射

### 3.1 登录页 (`views/login/admin.vue`)

> [!IMPORTANT]
> 登录页是所有测试的入口，验证码需要 OCR 识别。

**表单结构：**

| 字段 | Element UI 组件 | 选择器 | v-model |
|------|----------------|--------|---------|
| 用户名 | `el-input` | `input[placeholder*='用户名']` | `form.phone` |
| 密码 | `el-input` (show-password) | `input[placeholder*='密码']` | `form.password` |
| 验证码 | `el-input` | `input[placeholder*='验证码']` | `form.code` |
| 验证码图片 | `<img>` | `img[src^='data:image']` (local) / `img[src*='captcha']` (test) | — |
| 登录按钮 | `el-button` | `.lgoinBtn` | — |
| SSO登录 | `el-button` | `button:has-text('统一认证登录')` | — |

**特殊行为：**
- 验证码图片点击可刷新 (`@click="getCode"`)
- 登录失败时恢复明文密码（`originalPassword` 机制）
- SSO 配置通过 `loadSsoConfig()` 异步加载

---

### 3.2 门户首页 (`views/home/index.vue`)

**关键元素：**
- 模块卡片：`text=设备更新(新增)补贴管理`
- 系统标题标志：`.cls-title`
- 顶部菜单：`.cls-header-menu`

---

### 3.3 新增申报页 (`views/cleanEnergy/heatingEquipment/add/index.vue`)

#### 3.3.1 添加弹窗入口

| 操作 | 选择器 |
|------|--------|
| 添加按钮 | `button:has-text('添加')` |
| 设备新增类型 | `.declaration-type-dialog .type-button:has-text('设备新增')` |
| 设备更新类型 | `.declaration-type-dialog .type-button:has-text('设备更新')` |
| 搜索按钮 | `button:has-text('搜索')` |
| 重置按钮 | `button:has-text('重置')` |

#### 3.3.2 设备新增表单 — 区块与字段映射

**区块 1: 户主信息 (`.section-title:has-text('户主信息')`)**

| 字段 | 类型 | 选择器 | 数据键 |
|------|------|--------|--------|
| 户主姓名 | input | `input[placeholder='请输入户主姓名']` | `household_name` |
| 身份证号 | input | `input[placeholder='请输入身份证号']` | `id_card` |
| 联系电话 | input | `input[placeholder='请输入联系电话']` | `phone` |
| 安装地址 | input | `input[placeholder='请输入安装地址']` | `address` |
| 门牌号 | input | `input[placeholder='请输入门牌号']` | `door_number` |
| 客户编号 | input | `input[placeholder='请输入客户编号']` | `customer_id` |

**区块 2: 申报人信息**

| 字段 | 类型 | 选择器 | 数据键 |
|------|------|--------|--------|
| 是否户主 | el-select | `input[placeholder='请选择是否户主']` | `is_household` |
| 申报人姓名 | input | `input[placeholder='请输入申报人姓名']` | `applicant_name` |
| 申报人身份证号 | input | `input[placeholder='请输入申报人身份证号']` | `applicant_id_card` |
| 申报人联系电话 | input | `input[placeholder='请输入申报人联系电话']` | `applicant_phone` |
| 户籍信息 | vue-treeselect | `.vue-treeselect` | 通过 `__vue__` 操作 |
| 采暖面积 | input | `input[placeholder*='采暖面积']` | `heating_area` |

**区块 3: 能源类型**

| 字段 | 类型 | 选择器 |
|------|------|--------|
| 能源类型 | el-select | `.el-form-item:has-text('能源类型') .el-input__inner` |

**区块 4: 基础信息**

| 字段 | 类型 | 选择器 | 数据键 |
|------|------|--------|--------|
| 用户编号 | input | `input[placeholder*='用户编号']` | `user_number` |
| 银行卡号 | input | `input[placeholder*='银行卡号']` | `bank_account` |
| 开户人姓名 | input | `input[placeholder*='开户人姓名']` | `account_holder_name` |

**附件上传：**
- 每个附件入口：`button:has-text('点击上传')` → `expect_file_chooser` + `set_files`

**保存操作：**
- 保存按钮：`button:has-text('保 存')`
- 保存并提交：`button:has-text('保存并提交')`
- 成功标志：`text=保存成功`
- 系统编号格式：`SB20xxxxxx`

---

### 3.4 设备更新弹窗 (`add/components/DeviceUpdateForm.vue`)

**查询区域：**

| 字段 | 类型 | 描述 |
|------|------|------|
| 所属区 | el-select | 区级下拉选择（已预填） |
| 所属镇 | el-select | 镇级下拉选择（已预填） |
| 所属村 | el-select | 村级下拉选择（已预填） |
| 查询类型 | el-select | 切换身份证号/姓名搜索 |
| 查询输入框 | input | `placeholder='请输入'` |
| 查询按钮 | button | `button:has-text('查询')` |

**表单字段** —— 查询成功后预填 + 需补填的空字段（与设备新增类似）

---

### 3.5 申报审核管理页 (`audit/index.vue` — 88KB)

> [!NOTE]
> 审核页功能复杂，文件体积大，包含多个弹窗和操作模式。

**搜索栏：**

| 字段 | 类型 | 选择器 |
|------|------|--------|
| 用户编号 | input | 通过 `fill_input_by_label("用户编号", ...)` |
| 申报状态 | el-select | `.el-form-item:has-text('申报状态')` |
| 搜索按钮 | button | `button:has-text('搜索')` |
| 重置按钮 | button | `button:has-text('重置')` |

**审核操作：**

| 操作 | 选择器 |
|------|--------|
| 审核按钮（行内） | `button:has-text('审核')` |
| 全部置为通过状态 | `button:has-text('全部置为通过状态')` |
| 保存并提交 | `button:has-text('保存并提交')` |
| 确定（二次确认） | `.el-message-box__btns button:has-text('确定')` |

---

### 3.6 台账管理页 (`ledger/index.vue` — 91KB)

**搜索栏：**

| 字段 | 类型 | 选择器 |
|------|------|--------|
| 用户编号 | input | 通过 `fill_input_by_label("用户编号", ...)` |
| 搜索/重置 | button | 标准 Element UI 按钮 |

**表格操作：**

| 操作 | 选择器 |
|------|--------|
| 查看详情 | `button:has-text('查看')` 或 `text=查看` |
| 补贴申报 | `text=补贴申报` 链接 或 `button:has-text('补贴申报')` |
| 导出台账 | `button:has-text('导出台账')` |

**补贴申报表单字段** (在弹窗内)：

| 字段 | 类型 | 选择器 |
|------|------|--------|
| 购置金额 | input | `fill_input_by_label("购置金额", ...)` |
| 设备厂家 | el-select (级联) | `.el-form-item:has-text('设备厂家')` |
| 设备类型 | el-select (级联) | `.el-form-item:has-text('设备类型')` |
| 设备型号 | el-select (级联) | `.el-form-item:has-text('设备型号')` |
| 能耗级别 | el-select | `.el-form-item:has-text('能耗级别')` |
| 质保日期 | el-date-picker | `.el-form-item:has-text('质保日期')` |
| 发票号码 | input | `fill_input_by_label("发票号码", ...)` |
| 安装日期 | el-date-picker | `.el-form-item:has-text('安装日期')` |
| 安装人员 | input | `fill_input_by_label("安装人员", ..., exact=True)` |
| 安装人员联系电话 | input | `fill_input_by_label("安装人员联系电话", ...)` |
| 是否申报特殊补贴 | el-radio | `label.el-radio:has-text('是/否')` |
| 特殊补贴申报类型 | el-select | （特殊补贴=是时出现） |
| 附件上传 | el-upload | `button:has-text('点击上传')` |

---

## 4. Element UI 组件选择器模式参考

> [!TIP]
> 编写自动化测试时，以下 Element UI DOM 选择器规律可大幅减少调试时间。

### 4.1 表单项定位
```
.el-form-item → 包裹整个表单项
  .el-form-item__label → 标签文字
  .el-form-item__content → 内容区
    .el-input__inner → 实际输入框
    .el-input__suffix → 下拉箭头区
```

### 4.2 el-select 下拉选择
```
打开: 点击 .el-input__inner 或 .el-input__suffix
面板: .el-select-dropdown__item >> visible=true
选项: .el-select-dropdown__item:has-text('目标文本')
关闭: 选中后自动关闭，或点击其他区域
```

### 4.3 el-date-picker 日期选择
```
打开: 点击 .el-input__inner
今天: td.available.today >> visible=true
可用日期: td.available:not(.disabled)
```

### 4.4 弹窗定位
```
外层: .el-dialog__wrapper (display:none 表示隐藏)
标题: .el-dialog__header / .el-dialog__title
内容: .el-dialog__body
底部: .el-dialog__footer / .dialog-footer
关闭: .el-dialog__headerbtn
```

### 4.5 消息提示
```
成功: .el-message--success
错误: .el-message--error
确认框: .el-message-box__btns button:has-text('确定')
```

### 4.6 表格
```
表格行: table.el-table__body tr
单元格: td
操作按钮: button:has-text('操作名')
```

### 4.7 vue-treeselect
```
根元素: .vue-treeselect
控制: .vue-treeselect__control
菜单: .vue-treeselect__menu
选项: .vue-treeselect__option
标签: .vue-treeselect__label
✅ 最可靠方式: 通过 __vue__ 实例直接设值
```

---

## 5. 表单组件清单（前端 `cleanEnergy/components/form/`）

| 组件文件 | 功能 | 大小 | 测试关注度 |
|----------|------|------|------------|
| `ApplicantInfo.vue` | 申报人信息（含 vue-treeselect 户籍） | 39KB | 🔴 高 |
| `HouseholdInfo.vue` | 户主信息 | 10KB | 🔴 高 |
| `DeclarationType.vue` | 申报类型选择 | 31KB | 🔴 高 |
| `DeclarationFiles.vue` | 申报材料/附件上传 | 35KB | 🔴 高 |
| `BasicInfoUpload.vue` | 基础信息 + 附件 | 69KB | 🔴 高 |
| `DeviceInfo.vue` | 设备信息 | 48KB | 🟡 中 |
| `InstallationInfo.vue` | 安装信息 | 7KB | 🟡 中 |
| `SpecialSubsidyInfo.vue` | 特殊补贴信息 | 59KB | 🟡 中 |
| `SupplementaryMaterials.vue` | 补充材料 | 28KB | 🟡 中 |
| `FundingSource.vue` | 资金来源 | 6KB | ⬜ 低 |
| `ArchiveInfo.vue` | 档案信息 | 15KB | ⬜ 低 |
| `ReporterInfo.vue` | 填报人信息 | 3KB | ⬜ 低 |

---

## 6. 已有自动化测试覆盖范围

### 6.1 测试框架

| 项目 | 说明 |
|------|------|
| 框架 | Pytest + Playwright (Python) |
| 设计模式 | Page Object Model (POM) |
| 报告 | pytest-html + allure |
| OCR | ddddocr (验证码识别) |
| 数据 | DataFactory 随机数据工厂 |

### 6.2 Page Object 覆盖

| 页面类 | 对应前端页面 | 方法数 |
|--------|-------------|--------|
| `LoginPage` | 登录页 | 5 (login, logout, 验证码刷新) |
| `HomePage` | 门户首页 | 1 (enter_equipment_update_module) |
| `DeclarationPage` | 新增申报管理 | 10+ (CRUD + 设备更新) |
| `AuditPage` | 审核管理 | 4 (navigate, search, click_audit, approve) |
| `LedgerPage` | 台账管理 | 7 (navigate, search, export, subsidy_declaration) |
| `BasePage` | 通用基类 | 8 (safe_fill, safe_select, fill_input_by_label 等) |

### 6.3 测试用例覆盖

| 测试文件 | 覆盖场景 | 参数化 |
|----------|----------|--------|
| `test_e2e_declaration_crud.py` | 申报 CRUD 闭环 (新增→查询→查看→修改→删除) | 是否户主 × 2 |
| `test_e2e_device_add_flow.py` | 设备**新增**全链路 (申报→审核→台账→补贴→审核) | 是否户主 × 特殊补贴 (2×2=4) |
| `test_e2e_device_update_flow.py` | 设备**更新**全链路 (前置新增→更新申报→审核→补贴→审核) | 是否户主 × 特殊补贴 (2×2=4) |

### 6.4 角色切换机制
- `RoleManager` 类实现村级/镇级角色无缝切换
- 支持角色: `admin`, `city`, `district`, `town`, `village`

---

## 7. 尚未覆盖的测试模块

> [!WARNING]
> 以下模块/功能尚无自动化测试覆盖，建议优先补充。

### 7.1 业务页面

| 未覆盖模块 | 前端路径 | 优先级 |
|------------|----------|--------|
| 历史台账查询 | `heatingEquipment/historicalLedger` | 🟡 中 |
| 历史审核管理 | `heatingEquipment/historicalExamine` | 🟡 中 |
| 历史数据查询 | `heatingEquipment/historicalQuery` | ⬜ 低 |
| 补贴配置管理 | `heatingEquipment/subsidyConfig` | 🟡 中 |
| 代理人管理 | `heatingEquipment/agentManage` | ⬜ 低 |
| 厂家信息管理 | `heatingEquipment/manufactureInfoManage` | ⬜ 低 |
| 抽查审核 | `heatingEquipment/spotCheckAudit` | 🟡 中 |
| 工单管理 | `cleanEnergy/workOrder` | ⬜ 低 |
| IOT 设备管理 | `views/iot/iotdevice` | ⬜ 低 |

### 7.2 系统管理模块

| 未覆盖模块 | 前端路径 |
|------------|----------|
| 用户管理 | `views/system/user` |
| 角色管理 | `views/system/role` |
| 菜单管理 | `views/system/menu` |
| 部门管理 | `views/system/dept` |
| 字典管理 | `views/system/dict` |
| 区域管理 | `views/system/area` |
| 租户管理 | `views/system/tenant` |
| 表单配置 | `views/system/formConfig` |
| 平台配置 | `views/system/platformConfig` |

### 7.3 尚未覆盖的测试场景

| 场景 | 描述 |
|------|------|
| 登录异常 | 错误密码、账号锁定、SSO 登录 |
| 权限校验 | 不同角色访问受限页面 |
| 审核驳回 | 镇级用户驳回申报 |
| 导出功能 | 台账导出下载验证 |
| 分页翻页 | 大量数据时翻页测试 |
| 表单校验 | 必填字段为空、格式错误时提示 |
| 附件上传失败 | 上传超大文件、不支持格式 |
| 并发操作 | 多用户同时操作同一条记录 |
| 搜索边界 | 特殊字符搜索、空搜索、模糊搜索 |

---

## 8. 接下来的建议

### 8.1 优先扩展的 Page Object

按业务覆盖优先级排序，建议新增以下 Page Object：

1. **`subsidy_config_page.py`** — 补贴配置管理（影响业务计算逻辑）
2. **`spot_check_page.py`** — 抽查审核（审核流程补充）
3. **`history_ledger_page.py`** — 历史台账查询（数据验证类）
4. **`user_management_page.py`** — 用户/角色管理（权限类）

### 8.2 建议新增的测试用例

1. **审核驳回 + 重新提交** 流程测试
2. **边界值表单校验** 测试（采暖面积=0、负数、超大值）
3. **多角色权限** 测试（city/district 级角色验证）
4. **SSO 登录** 流程测试
5. **导出台账** 下载与内容校验

### 8.3 选择器优化建议

> [!TIP]
> 当前测试脚本大量使用 `placeholder` 和 `has-text` 定位，建议前端增加 `data-testid` 属性提升稳定性。

优先在以下高频操作元素上添加 `data-testid`：
- 所有 `el-form-item` 的 `input` 元素
- 弹窗操作按钮（保存/提交/取消）
- 表格操作列的按钮组
- 侧边菜单项

---

## 9. API 接口参考

前端 API 文件位于 `src/api/system/`，与测试相关的关键接口：

| API 文件 | 功能 |
|----------|------|
| `login.js` | 登录/登出/验证码/SSO认证 |
| `formData.js` | 表单数据 CRUD（申报/审核/台账等核心接口） |
| `formConfig.js` | 表单配置（字段动态渲染） |
| `area.js` | 区域树数据（省/市/区/镇/村级联） |
| `dept.js` | 部门数据 |
| `manufacturer.js` | 设备厂家/型号/类型  |
| `subsidyRatio.js` | 补贴比例配置 |
| `fundingSource.js` | 资金来源 |
| `sampling.js` | 抽查采样 |
| `districtSampling.js` | 区级抽样 |
| `user.js` | 用户管理 |
| `role.js` | 角色管理 |

---

## 10. 环境与配置

### 10.1 测试环境切换

当前 `utils/config.py` 支持：

| 环境 | URL | 验证码位数 | 需要门户跳转 |
|------|-----|------------|-------------|
| `local` | `http://localhost:8888/` | 5位 | 是 |
| `test` | `https://rural.touchit.com.cn/agri/#/admin` | 4位 | 是 |

### 10.2 账号体系

| 角色 | local 用户名 | test 用户名 | 说明 |
|------|-------------|-------------|------|
| admin | qiang | 18800000060 | 管理员 |
| city | shiji1 | lishiyi | 市级 |
| district | quji1 | liquyi | 区级 |
| town | zhenji1 | lizhenyi2 | 镇级 |
| village | cunji1 | licunyi | 村级 |

### 10.3 前端环境变量

| 文件 | 说明 |
|------|------|
| `.env.development` | 本地开发 |
| `.env.test` | 测试环境 |
| `.env.production` | 生产环境 |
| `.env.no-auth` | 免认证模式（`VUE_APP_SKIP_AUTH=true`） |
