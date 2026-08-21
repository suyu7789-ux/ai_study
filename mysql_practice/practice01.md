# MySQL 高级查询语法学习笔记（Practice 01）

配套脚本：[practice01.sql](./practice01.sql)

本文把脚本中的高级查询按统一结构整理：

> 概念 → 语法 → 业务场景 → SQL → 结果 → 关键解析 → 易错点 → 练习

示例使用 MySQL 8.0.14+。其中窗口函数、递归 CTE、`JSON_TABLE` 等属于 MySQL 8.0 系列功能，`LATERAL` 派生表要求 MySQL 8.0.14 或更高版本。

## 0. 运行准备

### 0.1 运行脚本

先连接到一个测试数据库，再执行脚本。例如在命令行中：

```bash
mysql -u 用户名 -p 数据库名 < mysql_practice/practice01.sql
```

也可以先创建专用数据库，再在客户端中执行：

```sql
CREATE DATABASE IF NOT EXISTS mysql_advanced_practice
    DEFAULT CHARACTER SET utf8mb4;
USE mysql_advanced_practice;
```

脚本中的表统一使用 `p01_` 前缀。脚本开头的 `DROP TABLE IF EXISTS` 只会删除这些练习表，因此应在测试库中运行，不要直接对生产库执行。

### 0.2 示例表概览

| 表 | 用途 | 关键列 |
| --- | --- | --- |
| `p01_employee` | 部门员工薪资排名 | `department_id`、`salary` |
| `p01_monthly_sales` | 月度销售趋势 | `sales_month`、`amount` |
| `p01_category` | 多级商品类目 | `id`、`parent_id` |
| `p01_customer` / `p01_orders` | 客户与订单 | `customer_id`、`created_at` |
| `p01_sales` | 区域、门店销售 | `region`、`store`、`amount` |
| `p01_score_record` | 学生成绩纵表 | `student_name`、`subject`、`score` |
| `p01_json_orders` | JSON 商品数组 | `items_data` |
| `p01_order_log` | 宽字段日志分页 | `created_at`、`id`、`details` |

---

## 一、窗口函数（Window Functions）

### 1.1 解决什么问题

窗口函数在一组相关行上计算结果，但不会像 `GROUP BY` 那样把明细行合并掉。它适合：

- 每个部门、每个门店内部的排名；
- 取每组 Top N；
- 访问上一行或下一行，计算环比、同比；
- 计算累计值、移动平均；
- 在保留明细的同时附加分组统计值。

可以把窗口理解成“当前行能够看到的一组行”。`PARTITION BY` 决定分组边界，`ORDER BY` 决定组内顺序，窗口帧（`ROWS`/`RANGE`）决定具体参与计算的行范围。

### 1.2 通用语法

```sql
window_function([参数]) OVER (
    [PARTITION BY 分组列 [, 分组列 ...]]
    [ORDER BY 排序列 [ASC | DESC] [, 排序列 ...]]
    [ROWS | RANGE BETWEEN 起始边界 AND 结束边界]
)
```

常见窗口边界：

```sql
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW -- 从分组第一行到当前行
ROWS BETWEEN 2 PRECEDING AND CURRENT ROW         -- 当前行及前两行
ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING  -- 当前行到分组最后一行
```

`ROWS` 按物理行计数；`RANGE` 按排序值范围计算，并列排序值通常会被视为同一个范围。需要稳定的逐行累计时，优先明确写出 `ROWS`，并让排序列具有确定性。

窗口函数一般不能直接写在 `WHERE` 中，因为 `WHERE` 的执行阶段早于窗口计算。要筛选窗口结果，应先放入 CTE 或派生表，再在外层过滤。

### 1.3 三种排名函数

假设薪资降序为 `30000、28000、28000、26000`：

| 函数 | 结果 | 适用含义 |
| --- | --- | --- |
| `ROW_NUMBER()` | `1、2、3、4` | 必须严格取前 N 人 |
| `RANK()` | `1、2、2、4` | 并列会占位，后续名次跳号 |
| `DENSE_RANK()` | `1、2、2、3` | 按前 N 个不同名次/薪资档位取值 |

### 1.4 场景 A：每个部门薪资最高的前 2 个薪资档位

业务表：`p01_employee(id, name, department_id, salary)`。

业务要求：每个部门取薪资最高的前 2 个档位，同薪员工并列保留。

```sql
WITH ranked_employee AS (
    SELECT
        id,
        name,
        department_id,
        salary,
        DENSE_RANK() OVER (
            PARTITION BY department_id
            ORDER BY salary DESC
        ) AS salary_rank
    FROM p01_employee
)
SELECT id, name, department_id, salary, salary_rank
FROM ranked_employee
WHERE salary_rank <= 2
ORDER BY department_id, salary_rank, id;
```

结果摘要：

| 部门 | 员工 | 薪资 | 名次 |
| --- | --- | ---: | ---: |
| 1 | 张三 | 30000 | 1 |
| 1 | 李四 | 28000 | 2 |
| 1 | 王强 | 28000 | 2 |
| 2 | 赵六 | 25000 | 1 |
| 2 | 钱七 | 25000 | 1 |
| 2 | 孙八 | 22000 | 2 |

因为 `DENSE_RANK()` 取的是两个薪资档位，所以每个部门可能超过两个人。若业务要求“每个部门严格 2 人”，使用 `ROW_NUMBER()`，并加入唯一列作为第二排序条件：

```sql
WITH numbered_employee AS (
    SELECT
        id,
        name,
        department_id,
        salary,
        ROW_NUMBER() OVER (
            PARTITION BY department_id
            ORDER BY salary DESC, id ASC
        ) AS row_num
    FROM p01_employee
)
SELECT id, name, department_id, salary, row_num
FROM numbered_employee
WHERE row_num <= 2;
```

### 1.5 场景 B：计算月度销售环比

业务表：`p01_monthly_sales(sales_month, amount)`。

环比公式：

```text
(本月销售额 - 上月销售额) / 上月销售额 × 100%
```

使用 `LAG(amount, 1)` 取得上一行：

```sql
WITH sales_with_previous AS (
    SELECT
        sales_month,
        amount,
        LAG(amount, 1) OVER (ORDER BY sales_month) AS previous_amount
    FROM p01_monthly_sales
)
SELECT
    sales_month,
    amount AS current_amount,
    previous_amount,
    ROUND(
        (amount - previous_amount) / NULLIF(previous_amount, 0) * 100,
        2
    ) AS mom_growth_percent
FROM sales_with_previous
ORDER BY sales_month;
```

预期环比为：第一月 `NULL`、第二月 `20.00%`、第三月 `-25.00%`、第四月 `50.00%`。

这里有两个防护：

1. 第一月不存在上一月，`LAG()` 返回 `NULL`，不应随意伪造成 `0%`；
2. `NULLIF(previous_amount, 0)` 把分母为 0 转为 `NULL`，避免除零错误。

### 1.6 场景 C：累计销售额

```sql
SELECT
    sales_month,
    amount,
    SUM(amount) OVER (
        ORDER BY sales_month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS year_to_date_amount
FROM p01_monthly_sales
ORDER BY sales_month;
```

累计结果是 `100000、220000、310000、445000`。如果要“每个门店各自累计”，加入 `PARTITION BY store_id`；如果要移动 3 个月平均，可以使用 `AVG(amount) OVER (ORDER BY sales_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)`。

### 1.7 常见错误

- 只写 `ORDER BY salary`，没有 `PARTITION BY department_id`，结果会变成全公司排名；
- 直接在 `WHERE` 中写 `ROW_NUMBER() <= 2`；应使用 CTE/派生表；
- 需要严格人数却使用 `RANK()` 或 `DENSE_RANK()`；
- 环比没有处理第一行和分母为 0；
- 排序列有重复值却没有补充 `id`，分页或编号可能不稳定。

---

## 二、通用表表达式与递归 CTE

### 2.1 普通 CTE

CTE（Common Table Expression，通用表表达式）是当前 SQL 语句范围内的临时命名结果集。它可以把复杂查询拆成多个有名字的阶段，提高可读性。

```sql
WITH cte_name AS (
    SELECT ...
)
SELECT ...
FROM cte_name;
```

同一条语句可以定义多个 CTE：

```sql
WITH first_step AS (...),
     second_step AS (... FROM first_step)
SELECT ... FROM second_step;
```

CTE 不是永久表，也不保证一定物化；具体执行方式由优化器决定。

### 2.2 递归 CTE 结构

```sql
WITH RECURSIVE cte_name AS (
    -- 锚点（anchor）：递归起点
    SELECT ...
    WHERE 起点条件

    UNION ALL

    -- 递归成员（recursive member）：根据上一层产生下一层
    SELECT ...
    FROM 源表
    JOIN cte_name ON 关联条件
)
SELECT * FROM cte_name;
```

递归 CTE 每轮包含两部分：

1. 锚点查询先产生第 1 层；
2. 递归查询引用上一轮结果，产生下一层；当某轮没有新行时结束。

`UNION ALL` 通常比 `UNION` 更适合递归，因为 `UNION` 会额外去重；但如果业务需要防止重复，必须设计明确的去重或路径判重策略。

### 2.3 场景：遍历多级商品类目

表结构：

```text
p01_category(id, name, parent_id)
```

例如：电子产品 → 手机数码 → 智能手机。

```sql
WITH RECURSIVE category_path AS (
    SELECT
        id,
        name,
        parent_id,
        1 AS category_level,
        CAST(name AS CHAR(500)) AS full_path
    FROM p01_category
    WHERE id = 1

    UNION ALL

    SELECT
        child.id,
        child.name,
        child.parent_id,
        parent.category_level + 1,
        CONCAT(parent.full_path, ' > ', child.name)
    FROM p01_category AS child
    INNER JOIN category_path AS parent
        ON child.parent_id = parent.id
)
SELECT id, name, parent_id, category_level, full_path
FROM category_path
ORDER BY full_path;
```

结果示例：

| id | name | 层级 | full_path |
| ---: | --- | ---: | --- |
| 1 | 电子产品 | 1 | 电子产品 |
| 2 | 手机数码 | 2 | 电子产品 > 手机数码 |
| 3 | 智能手机 | 3 | 电子产品 > 手机数码 > 智能手机 |
| 4 | 电脑办公 | 2 | 电子产品 > 电脑办公 |
| 5 | 笔记本电脑 | 3 | 电子产品 > 电脑办公 > 笔记本电脑 |

### 2.4 为什么要 `CAST(name AS CHAR(500))`

递归 CTE 的列类型通常根据锚点查询推断。如果锚点中的 `full_path` 只是一个短字符串，递归阶段不断 `CONCAT()` 后可能出现 `Data too long`。预先把路径列声明为足够长的字符类型，可以避免这个问题。

### 2.5 反向查询祖先节点

向下遍历时连接条件是 `child.parent_id = parent.id`。如果要从“智能手机”向上找祖先，方向相反：

```sql
WITH RECURSIVE ancestors AS (
    SELECT id, name, parent_id, 1 AS distance
    FROM p01_category
    WHERE id = 3

    UNION ALL

    SELECT parent.id, parent.name, parent.parent_id, child.distance + 1
    FROM p01_category AS parent
    JOIN ancestors AS child
        ON parent.id = child.parent_id
)
SELECT * FROM ancestors;
```

### 2.6 常见错误与生产注意事项

- 忘记写 `WITH RECURSIVE`；
- 锚点与递归成员的列数量、顺序、类型不一致；
- `parent_id` 数据形成环，导致重复递归；
- 层级过深，超过 `cte_max_recursion_depth`；
- 路径过长或字符集不一致；
- 没有给 `parent_id` 建索引，导致每一层都进行低效扫描。

组织架构、权限菜单、评论回复、商品类目、文件目录都适合使用递归 CTE。

---

## 三、LATERAL 横向派生表

### 3.1 核心概念

普通派生表是一个独立的子查询；`LATERAL` 允许派生表引用它左侧表当前行的列。因此，它可以理解为“对左表每一行执行一次的相关派生表”。

### 3.2 语法

```sql
SELECT ...
FROM 主表 AS a
LEFT JOIN LATERAL (
    SELECT ...
    FROM 明细表 AS b
    WHERE b.foreign_key = a.primary_key
    ORDER BY 排序列 DESC
    LIMIT n
) AS detail_top_n ON TRUE;
```

`LEFT JOIN LATERAL` 会保留没有明细的主表行；若只需要有明细的主表，可以使用 `JOIN LATERAL`。`ON TRUE` 表示相关条件已经写在子查询的 `WHERE` 中。

### 3.3 场景：每个客户最近 2 笔订单

表结构：

```text
p01_customer(id, name)
p01_orders(id, customer_id, amount, created_at)
```

```sql
SELECT
    customer.id AS customer_id,
    customer.name AS customer_name,
    latest_orders.order_id,
    latest_orders.amount,
    latest_orders.created_at
FROM p01_customer AS customer
LEFT JOIN LATERAL (
    SELECT
        orders.id AS order_id,
        orders.amount,
        orders.created_at
    FROM p01_orders AS orders
    WHERE orders.customer_id = customer.id
    ORDER BY orders.created_at DESC, orders.id DESC
    LIMIT 2
) AS latest_orders ON TRUE
ORDER BY customer.id, latest_orders.created_at DESC;
```

结果特点：

- 晨光科技有 3 笔订单，但只返回最新 2 笔；
- 远山贸易有 1 笔，返回 1 笔；
- 蓝海工作室没有订单，但客户行仍保留，订单列为 `NULL`。

### 3.4 为什么普通 `JOIN ... LIMIT 2` 不行

下面的 `LIMIT 2` 限制的是整个结果集，而不是每个客户：

```sql
-- 不是“每个客户 2 笔”，而是全局只返回 2 行
SELECT c.id, o.id, o.created_at
FROM p01_customer AS c
JOIN p01_orders AS o ON o.customer_id = c.id
ORDER BY o.created_at DESC
LIMIT 2;
```

如果不使用 `LATERAL`，也可以先对全部订单使用 `ROW_NUMBER() OVER (PARTITION BY customer_id ...)`，再在外层筛选；`LATERAL` 的表达方式更贴近“每个客户单独取 Top N”。

### 3.5 索引与性能

推荐索引：

```sql
CREATE INDEX idx_orders_customer_created
ON p01_orders (customer_id, created_at DESC, id DESC);
```

索引先匹配关联条件 `customer_id`，再匹配排序列 `created_at`、`id`。实际效果仍取决于客户数量、每个客户的订单数量和数据分布，应使用 `EXPLAIN` 或 `EXPLAIN ANALYZE` 验证。

### 3.6 常见错误

- MySQL 版本低于 8.0.14；
- 忘记给 LATERAL 子查询起别名；
- 没有稳定的第二排序条件，导致同一时间订单顺序不确定；
- 误以为它一定比窗口函数快，实际上要结合数据规模和执行计划判断。

---

## 四、`WITH ROLLUP` 与 `GROUPING`

### 4.1 解决什么问题

普通 `GROUP BY region, store` 只能得到门店级别数据。报表通常还需要：

- 每个大区的小计；
- 全部大区的总计；
- 在同一结果集中标识哪些行是明细、哪些行是汇总。

`WITH ROLLUP` 自动生成这些层级，避免手写多条 `UNION ALL`。

### 4.2 语法

```sql
SELECT
    col1,
    col2,
    SUM(amount),
    GROUPING(col1),
    GROUPING(col2)
FROM table_name
GROUP BY col1, col2 WITH ROLLUP;
```

对于 `GROUP BY region, store WITH ROLLUP`，结果大致按以下层级产生：

```text
region + store       明细
region + NULL        region 小计
NULL   + NULL        总计
```

这里的 `NULL` 可能是 ROLLUP 生成的，也可能是原始数据真实存储的 `NULL`，所以不能只通过 `col IS NULL` 判断汇总行。`GROUPING(col)` 返回 `1` 才表示该列在当前行被汇总。

### 4.3 场景：门店小计、大区小计和全国总计

```sql
SELECT
    CASE
        WHEN GROUPING(region) = 1 THEN '全国总计'
        ELSE region
    END AS region_name,
    CASE
        WHEN GROUPING(region) = 1 THEN '全部门店'
        WHEN GROUPING(store) = 1 THEN '大区小计'
        ELSE store
    END AS store_name,
    SUM(amount) AS total_sales,
    GROUPING(region) AS is_region_summary,
    GROUPING(store) AS is_store_summary
FROM p01_sales
GROUP BY region, store WITH ROLLUP;
```

预期汇总：华东小计 `130000`，华南小计 `70000`，全国总计 `200000`。

### 4.4 `GROUPING` 标记解读

| `GROUPING(region)` | `GROUPING(store)` | 含义 |
| ---: | ---: | --- |
| 0 | 0 | 门店明细 |
| 0 | 1 | 当前大区小计 |
| 1 | 1 | 全国总计 |

在展示层，通常用 `CASE`/`IF` 把汇总行的 `NULL` 改成“合计”“全国总计”等文字；保留 `is_*_summary` 标记则方便前端设置加粗、排序或导出格式。

### 4.5 注意事项

- `ROLLUP` 的汇总顺序由 `GROUP BY` 列顺序决定；
- MySQL 主要使用 `ROLLUP` 生成层级汇总；如果需要完全自定义多个汇总组合，通常使用多条查询配合 `UNION ALL`，不要直接照搬其他数据库的 `GROUPING SETS` 语法；
- 不能把汇总行当成普通明细直接参与后续再次求和，否则可能重复计算；
- 汇总查询常常需要显式 `ORDER BY`，否则结果顺序不应依赖执行计划。

---

## 五、条件聚合与行列转换（静态 Pivot）

### 5.1 核心思路

MySQL 没有 SQL Server/Oracle 那种独立的 `PIVOT` 关键字。常用做法是：

1. 用 `CASE WHEN` 判断当前行属于哪一类；
2. 对满足条件的值使用 `SUM`、`MAX` 或 `COUNT`；
3. 以主维度 `GROUP BY`，把多行压成一行多列。

### 5.2 通用语法

```sql
SELECT
    main_dimension,
    MAX(CASE WHEN category_col = '分类 A' THEN value_col END) AS col_a,
    MAX(CASE WHEN category_col = '分类 B' THEN value_col END) AS col_b,
    SUM(CASE WHEN category_col = '分类 A' THEN value_col ELSE 0 END) AS sum_a
FROM table_name
GROUP BY main_dimension;
```

函数选择：

- 每个维度和分类只有一条记录：常用 `MAX` 取出该值；
- 同一分类有多条记录且需要相加：使用 `SUM`；
- 只需要计数：使用 `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` 或 `COUNT` 配合 `CASE`。

### 5.3 场景：学生成绩纵表转横表

原始纵表：

| student_name | subject | score |
| --- | --- | ---: |
| 小明 | Chinese | 85 |
| 小明 | Math | 92 |
| 小明 | English | 78 |

目标横表：每名学生一行，语文、数学、英语各一列。

```sql
SELECT
    student_name,
    MAX(CASE WHEN subject = 'Chinese' THEN score END) AS chinese_score,
    MAX(CASE WHEN subject = 'Math'    THEN score END) AS math_score,
    MAX(CASE WHEN subject = 'English' THEN score END) AS english_score,
    SUM(CASE
            WHEN subject IN ('Chinese', 'Math', 'English') THEN score
            ELSE 0
        END) AS total_score
FROM p01_score_record
GROUP BY student_name
ORDER BY student_name;
```

结果：小明总分 `255`，小红总分 `279`。

### 5.4 `NULL` 与 `0` 的业务含义

```sql
MAX(CASE WHEN subject = 'Math' THEN score END)
```

没有数学记录时返回 `NULL`，表示“没有成绩”。如果改成：

```sql
MAX(CASE WHEN subject = 'Math' THEN score ELSE 0 END)
```

没有记录时会显示 `0`，这只能在业务明确把缺失视为 0 分时使用。缺失、缺考、未录入和真实 0 分通常应该区分。

### 5.5 动态 Pivot

上述写法是静态 Pivot，科目变化时必须改 SQL。动态列通常需要：

- 应用程序读取分类列表后拼接 SQL；或
- 使用 MySQL 预处理语句 `PREPARE`/`EXECUTE`；或
- 不做物理转列，在应用层或报表工具中透视。

动态 SQL 必须对列名和分类值做白名单校验，不能把未经验证的用户输入直接拼接进 SQL。

---

## 六、`JSON_TABLE`：把 JSON 数组关系化

### 6.1 为什么需要它

有些数据来自外部 API、消息队列或历史系统，商品明细暂时以 JSON 数组存储。`JSON_TABLE` 可以在查询时把数组元素展开成临时的行列结构，然后继续使用普通 SQL：

- `JOIN` 商品表补充商品名称；
- `WHERE` 过滤某类商品；
- `GROUP BY` 统计 SKU；
- `SUM` 计算数量和金额。

### 6.2 基本语法

```sql
SELECT ...
FROM main_table AS t
JOIN JSON_TABLE(
    t.json_column,
    '$[*]' COLUMNS (
        output_col data_type PATH '$.json_key'
    )
) AS jt ON TRUE;
```

关键部分：

- `'$[*]'`：遍历 JSON 数组的每个元素；
- `COLUMNS`：定义输出列；
- `PATH '$.sku_id'`：从当前数组元素读取字段；
- `ON TRUE`：表示 JSON_TABLE 与主表的关联已经由第一个参数 `t.json_column` 表达。

### 6.3 场景：统计全平台 SKU 销量和销售额

示例 `items_data`：

```json
[
  {"sku_id": 101, "price": 50.00, "qty": 2},
  {"sku_id": 102, "price": 30.00, "qty": 1}
]
```

查询：

```sql
SELECT
    item.sku_id,
    SUM(item.qty) AS total_sold_qty,
    SUM(item.price * item.qty) AS total_revenue
FROM p01_json_orders AS orders
JOIN JSON_TABLE(
    orders.items_data,
    '$[*]' COLUMNS (
        sku_id INT            PATH '$.sku_id',
        price  DECIMAL(10, 2) PATH '$.price',
        qty    INT            PATH '$.qty'
    )
) AS item ON TRUE
GROUP BY item.sku_id
ORDER BY item.sku_id;
```

结果：

| sku_id | total_sold_qty | total_revenue |
| ---: | ---: | ---: |
| 101 | 5 | 250.00 |
| 102 | 1 | 30.00 |
| 103 | 1 | 80.00 |

### 6.4 展开为明细行

如果不想汇总，而是查看每个订单的每个商品：

```sql
SELECT
    orders.order_no,
    item.sku_id,
    item.price,
    item.qty,
    item.price * item.qty AS line_amount
FROM p01_json_orders AS orders
JOIN JSON_TABLE(
    orders.items_data,
    '$[*]' COLUMNS (
        sku_id INT            PATH '$.sku_id',
        price  DECIMAL(10, 2) PATH '$.price',
        qty    INT            PATH '$.qty'
    )
) AS item ON TRUE
ORDER BY orders.order_no, item.sku_id;
```

### 6.5 `NESTED PATH` 与缺失字段

复杂 JSON 可以在 `COLUMNS` 内使用 `NESTED PATH` 展开嵌套数组。字段可能缺失时，可以指定默认值或错误处理策略，例如：

```sql
COLUMNS (
    qty INT PATH '$.qty' DEFAULT '0' ON EMPTY NULL ON ERROR
)
```

实际项目中应根据数据质量决定是把异常转为 `NULL`、默认值，还是直接报错，避免静默吞掉脏数据。

### 6.6 JSON 还是正规化表

适合保留 JSON 的情况：外部载荷结构不稳定、低频分析、历史兼容、迁移过渡。

适合拆成明细表的情况：高频过滤/关联、需要唯一约束、需要外键、需要单条更新、需要高性能索引。`JSON_TABLE` 是查询时展开，不会自动替代正规化设计。

---

## 七、深度分页：延迟关联与游标分页

### 7.1 `LIMIT offset, page_size` 的问题

```sql
SELECT *
FROM p01_order_log
ORDER BY created_at DESC, id DESC
LIMIT 5000000, 10;
```

数据库通常需要先找到并跳过前 `5000000` 行，再返回 10 行。若表包含 `TEXT`、`JSON` 等宽字段，直接 `SELECT *` 还可能让大量无须返回的行发生回表和 I/O。

### 7.2 延迟关联（Deferred Join）

通用写法：

```sql
SELECT full_row.*
FROM large_table AS full_row
JOIN (
    SELECT id
    FROM large_table
    WHERE filtering_condition
    ORDER BY indexed_col DESC, id DESC
    LIMIT offset, page_size
) AS page_ids
    ON page_ids.id = full_row.id
ORDER BY full_row.indexed_col DESC, full_row.id DESC;
```

内层只取主键（或覆盖索引中的窄列），定位到本页 ID 后，外层只回表读取本页完整字段。

脚本中的演示：

```sql
SELECT log_row.id, log_row.created_at, log_row.status, log_row.details
FROM p01_order_log AS log_row
INNER JOIN (
    SELECT id
    FROM p01_order_log FORCE INDEX (idx_order_log_page)
    ORDER BY created_at DESC, id DESC
    LIMIT 5, 3
) AS page_ids ON page_ids.id = log_row.id
ORDER BY log_row.created_at DESC, log_row.id DESC;
```

这条语句返回 `id = 7、6、5`。`FORCE INDEX` 只是让练习更直观；生产中应先使用 `EXPLAIN`/`EXPLAIN ANALYZE`，不要习惯性强制索引。

### 7.3 延迟关联的边界

延迟关联减少了宽行回表的次数，但内层仍要扫描和跳过 `offset` 行，因此页码特别深时，耗时仍可能增长。它是对传统 Offset 分页的优化，不是把 Offset 变成常数复杂度。

### 7.4 游标分页（Keyset/Cursor Pagination）

当页面只需要“下一页”，游标分页通常更适合：

```sql
SELECT id, created_at, status, details
FROM p01_order_log
WHERE created_at < :last_created_at
   OR (created_at = :last_created_at AND id < :last_id)
ORDER BY created_at DESC, id DESC
LIMIT :page_size;
```

假设上一页最后一行是 `created_at = '2026-08-20 12:08:00'`、`id = 8`，查询下一页：

```sql
SELECT id, created_at, status, details
FROM p01_order_log
WHERE created_at < '2026-08-20 12:08:00'
   OR (created_at = '2026-08-20 12:08:00' AND id < 8)
ORDER BY created_at DESC, id DESC
LIMIT 3;
```

游标分页通过索引直接从上次位置继续读取，适合信息流、订单列表、“加载更多”等场景；代价是不能方便地跳转到任意第 N 页。

### 7.5 为什么需要两个排序列

仅使用 `created_at < 上次时间`，可能漏掉与上一页最后一行时间相同的记录。增加唯一的 `id` 作为 tie-breaker 后，条件变为：

```text
created_at 更早
或 created_at 相同且 id 更小
```

这样每一行都有稳定的位置。排序方向、索引顺序和游标比较符号必须保持一致。

### 7.6 三种分页方式对比

| 方式 | 优点 | 局限 | 适用场景 |
| --- | --- | --- | --- |
| 普通 Offset | 写法简单，可跳页 | 深页扫描大量行 | 小表、后台简单列表 |
| 延迟关联 | 减少宽字段回表 | 仍需跳过 offset | 宽表、必须支持跳页 |
| 游标分页 | 深页性能稳定，适合索引 | 不方便任意跳页 | 信息流、下一页、加载更多 |

---

## 八、综合对照表

| 技术 | 核心痛点 | 典型业务 |
| --- | --- | --- |
| 窗口函数 | 组内排名、前后行、累计值，同时保留明细 | 部门 Top N、环比、累计消费 |
| 普通/递归 CTE | 拆分复杂查询、遍历层级树 | 组织架构、类目、权限菜单 |
| LATERAL | 左表每一行单独取相关 Top N | 每客户最新订单、商品最新评论 |
| `ROLLUP` | 同时生成明细、小计、总计 | 区域-门店销售报表 |
| 条件聚合 | 纵表转横表、条件指标并列 | 成绩单、状态金额统计 |
| `JSON_TABLE` | JSON 数组无法直接参与关系聚合 | 订单商品拆解、标签统计 |
| 延迟关联 | 宽表深分页回表开销大 | 日志、订单后台列表 |
| 游标分页 | 避免深 Offset 扫描 | 信息流、加载更多 |

---

## 九、建议的学习顺序

1. 先掌握 `ROW_NUMBER`、`RANK`、`DENSE_RANK`，理解 `PARTITION BY` 和 `ORDER BY`；
2. 再学习 `LAG`、`LEAD` 和带窗口帧的累计计算；
3. 使用普通 CTE 拆分查询，再学习递归 CTE；
4. 学习条件聚合，把纵表转换成报表需要的横表；
5. 学习 `ROLLUP`，理解汇总层级和 `GROUPING` 标记；
6. 最后学习 LATERAL、JSON_TABLE 及分页执行计划，它们更依赖版本、索引和真实数据规模。

---

## 十、自测题

以下题目可以直接基于 `practice01.sql` 创建的表练习：

1. 使用窗口函数统计每位客户的订单序号和累计订单金额。
2. 从 `p01_category` 的“智能手机”反向查询到根类目，并输出路径。
3. 使用 `LATERAL` 取每位客户金额最高的 1 笔订单；金额相同时按订单 ID 降序。
4. 给 `p01_sales` 增加销售日期，观察 `GROUP BY region, store WITH ROLLUP` 的汇总层级。
5. 使用条件聚合统计每位客户 `SUCCESS` 和 `FAILED` 订单数。
6. 使用 `JSON_TABLE` 展开每个订单的商品明细，不做 SKU 汇总。
7. 对普通 Offset、延迟关联、游标分页分别执行 `EXPLAIN ANALYZE`，比较扫描行数、回表和耗时。

完成自测时，先写出“结果应该按什么维度分组、按什么字段排序、缺失值代表什么”，再写 SQL。高级查询的正确性通常取决于这些业务语义，而不只是语法是否能执行。
