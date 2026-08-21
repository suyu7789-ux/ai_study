/*
 MySQL 高级查询练习 01
 ================================================================
 详细知识讲解见同目录：practice01.md
 适用版本：MySQL 8.0.14+
 原因：本文件会使用窗口函数、递归 CTE、LATERAL、GROUPING、
       JSON_TABLE 等 MySQL 8.0 功能。

 使用方法：
 1. 先在测试环境中选中一个数据库（Schema）。
 2. 从上到下执行本文件。
 3. 所有演示表都使用 p01_ 前缀，避免和普通业务表重名。

 如需单独创建练习库，可手动取消下面两行的注释：
 CREATE DATABASE IF NOT EXISTS mysql_advanced_practice
   DEFAULT CHARACTER SET utf8mb4;
 USE mysql_advanced_practice;
*/

SET NAMES utf8mb4;


/*
 一、窗口函数（Window Functions）
 ================================================================

 【语法规则】

 窗口函数(...) OVER (
     PARTITION BY 分组列
     ORDER BY 排序列 [ASC | DESC]
     [ROWS | RANGE BETWEEN 起始边界 AND 结束边界]
 )

 与 GROUP BY 的区别：
 - GROUP BY 会把多行压缩成一行。
 - 窗口函数会保留明细行，并在每一行旁边附加排名、累计值、前后行等结果。

 常用函数：
 - ROW_NUMBER()：严格编号，不保留并列名次。
 - RANK()：并列后跳号，例如 1、2、2、4。
 - DENSE_RANK()：并列后不跳号，例如 1、2、2、3。
 - LAG()/LEAD()：获取上一行/下一行。
 - SUM() OVER：累计求和或移动求和。
*/

DROP TABLE IF EXISTS p01_employee;
CREATE TABLE p01_employee (
    id            BIGINT PRIMARY KEY,
    name          VARCHAR(30) NOT NULL,
    department_id INT NOT NULL,
    salary        DECIMAL(10, 2) NOT NULL,
    INDEX idx_employee_dept_salary (department_id, salary DESC)
) ENGINE = InnoDB;

INSERT INTO p01_employee (id, name, department_id, salary) VALUES
    (1, '张三', 1, 30000.00),
    (2, '李四', 1, 28000.00),
    (3, '王强', 1, 28000.00),
    (4, '周明', 1, 26000.00),
    (5, '赵六', 2, 25000.00),
    (6, '钱七', 2, 25000.00),
    (7, '孙八', 2, 22000.00);

/*
 【业务场景 A】查询每个部门薪资最高的前 2 个“薪资档位”，同薪同名次。

 注意：DENSE_RANK() 取的是前 2 个不同薪资档位，因此并列时一个部门
 可能返回超过 2 名员工。如果业务要求每部门必须恰好 2 人，应改用
 ROW_NUMBER()，并添加 id 等稳定的第二排序条件。
*/
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

/*
 预期结果摘要：
 - 部门 1：张三第 1；李四、王强并列第 2，因此返回 3 人。
 - 部门 2：赵六、钱七并列第 1；孙八第 2，因此返回 3 人。
*/

-- 扩展：每个部门严格只取 2 人；同薪时 id 小的排在前面。
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
WHERE row_num <= 2
ORDER BY department_id, row_num;


DROP TABLE IF EXISTS p01_monthly_sales;
CREATE TABLE p01_monthly_sales (
    sales_month DATE PRIMARY KEY,
    amount       DECIMAL(12, 2) NOT NULL
) ENGINE = InnoDB;

INSERT INTO p01_monthly_sales (sales_month, amount) VALUES
    ('2026-01-01', 100000.00),
    ('2026-02-01', 120000.00),
    ('2026-03-01',  90000.00),
    ('2026-04-01', 135000.00);

/*
 【业务场景 B】计算月度销售额环比。

 先在 CTE 中计算一次 LAG，再在外层使用，避免重复书写窗口函数。
 NULLIF(previous_amount, 0) 能防止上月金额为 0 时发生除零错误。
 第一月没有上月数据，因此环比为 NULL，这比伪造 0% 更符合业务语义。
*/
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

/*
 预期环比：NULL、20.00、-25.00、50.00。
*/

-- 扩展：计算从年初到当前月的累计销售额。
SELECT
    sales_month,
    amount,
    SUM(amount) OVER (
        ORDER BY sales_month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS year_to_date_amount
FROM p01_monthly_sales
ORDER BY sales_month;


/*
 二、通用表表达式与递归 CTE（Recursive CTE）
 ================================================================

 【普通 CTE 语法】

 WITH cte_name AS (
     SELECT ...
 )
 SELECT ... FROM cte_name;

 【递归 CTE 语法】

 WITH RECURSIVE cte_name AS (
     -- 锚点查询：确定递归起点
     SELECT ...

     UNION ALL

     -- 递归查询：引用 cte_name，逐层产生下一批数据
     SELECT ...
     FROM source_table
     JOIN cte_name ON 关联条件
 )
 SELECT * FROM cte_name;

 递归会在某一轮查询不再产生新行时终止。
*/

DROP TABLE IF EXISTS p01_category;
CREATE TABLE p01_category (
    id        BIGINT PRIMARY KEY,
    name      VARCHAR(50) NOT NULL,
    parent_id BIGINT NULL,
    INDEX idx_category_parent (parent_id)
) ENGINE = InnoDB;

INSERT INTO p01_category (id, name, parent_id) VALUES
    (1, '电子产品', NULL),
    (2, '手机数码', 1),
    (3, '智能手机', 2),
    (4, '电脑办公', 1),
    (5, '笔记本电脑', 4),
    (6, '家用电器', NULL);

/*
 【业务场景】从“电子产品”(id = 1) 开始，向下查出全部后代类目，
 同时展示层级和完整路径。

 CAST 很重要：递归 CTE 的字符串列类型由锚点推断。如果锚点只返回
 较短的 name，后续拼接出的长路径可能报 Data too long。
*/
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

/*
 预期路径示例：电子产品 > 手机数码 > 智能手机。

 生产提示：脏数据中的环可能导致递归不断重复。生产系统应通过数据约束、
 路径判重或合理的递归深度限制防止循环。
*/


/*
 三、横向派生表（LATERAL Derived Table）
 ================================================================

 【语法规则】

 SELECT ...
 FROM main_table AS a
 LEFT JOIN LATERAL (
     SELECT ...
     FROM detail_table AS b
     WHERE b.foreign_key = a.primary_key  -- 可引用左表 a
     ORDER BY ...
     LIMIT n
 ) AS derived_table ON TRUE;

 普通派生表通常不能引用同级 FROM 中左侧表的列；LATERAL 允许这种引用。
 MySQL 从 8.0.14 开始支持 LATERAL 派生表。
*/

DROP TABLE IF EXISTS p01_orders;
DROP TABLE IF EXISTS p01_customer;

CREATE TABLE p01_customer (
    id   BIGINT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
) ENGINE = InnoDB;

CREATE TABLE p01_orders (
    id          BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    amount      DECIMAL(12, 2) NOT NULL,
    created_at  DATETIME NOT NULL,
    INDEX idx_orders_customer_created (customer_id, created_at DESC, id DESC)
) ENGINE = InnoDB;

INSERT INTO p01_customer (id, name) VALUES
    (1, '晨光科技'),
    (2, '远山贸易'),
    (3, '蓝海工作室');

INSERT INTO p01_orders (id, customer_id, amount, created_at) VALUES
    (101, 1,  8000.00, '2026-08-01 10:00:00'),
    (102, 1, 12000.00, '2026-08-10 14:00:00'),
    (103, 1,  9500.00, '2026-08-18 09:00:00'),
    (104, 2, 20000.00, '2026-08-15 16:30:00');

/*
 【业务场景】列出每个客户最近的 2 笔订单；没有订单的客户也要保留。

 LIMIT 2 会对左表中的“每一个客户”分别执行，而不是限制整个结果集。
 复合索引 (customer_id, created_at DESC, id DESC) 与过滤、排序顺序匹配。
*/
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

/*
 预期结果：晨光科技 2 行，远山贸易 1 行，蓝海工作室 1 行且订单列为 NULL。
*/


/*
 四、多维聚合与汇总（WITH ROLLUP + GROUPING）
 ================================================================

 【语法规则】

 SELECT
     group_col_1,
     group_col_2,
     GROUPING(group_col_1),
     GROUPING(group_col_2),
     SUM(value_col)
 FROM table_name
 GROUP BY group_col_1, group_col_2 WITH ROLLUP;

 ROLLUP 按分组列从右向左生成逐级小计，最后生成总计。
 GROUPING(col) = 1 表示该列的 NULL 是汇总产生的，不是真实数据里的 NULL。
*/

DROP TABLE IF EXISTS p01_sales;
CREATE TABLE p01_sales (
    id     BIGINT PRIMARY KEY,
    region VARCHAR(30) NOT NULL,
    store  VARCHAR(50) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL
) ENGINE = InnoDB;

INSERT INTO p01_sales (id, region, store, amount) VALUES
    (1, '华东', '杭州店', 30000.00),
    (2, '华东', '杭州店', 20000.00),
    (3, '华东', '上海店', 80000.00),
    (4, '华南', '深圳店', 70000.00);

/*
 【业务场景】一次查询同时输出门店销售额、大区小计和全国总计。
*/
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

/*
 预期汇总：华东 130000、华南 70000、全国 200000。
*/


/*
 五、条件聚合与行列转换（静态 Pivot）
 ================================================================

 【语法规则】

 SELECT
     main_dimension,
     aggregate_function(
         CASE WHEN category_col = '分类值' THEN value_col ELSE NULL END
     ) AS result_col
 FROM table_name
 GROUP BY main_dimension;

 MySQL 没有独立的 PIVOT 关键字，通常用 CASE + 聚合函数完成静态透视。
*/

DROP TABLE IF EXISTS p01_score_record;
CREATE TABLE p01_score_record (
    id           BIGINT PRIMARY KEY,
    student_name VARCHAR(30) NOT NULL,
    subject      VARCHAR(30) NOT NULL,
    score        DECIMAL(5, 2) NOT NULL,
    UNIQUE KEY uk_student_subject (student_name, subject)
) ENGINE = InnoDB;

INSERT INTO p01_score_record (id, student_name, subject, score) VALUES
    (1, '小明', 'Chinese', 85.00),
    (2, '小明', 'Math',    92.00),
    (3, '小明', 'English', 78.00),
    (4, '小红', 'Chinese', 90.00),
    (5, '小红', 'Math',    95.00),
    (6, '小红', 'English', 94.00);

/*
 【业务场景】将每名学生的科目成绩从纵向多行转换为横向多列。

 ELSE NULL 能让“缺考/无记录”保持为 NULL；如果写 ELSE 0，会混淆
 “没有成绩”和“真实考了 0 分”。MAX 在每名学生每科只有一条记录时取值。
*/
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

/*
 预期总分：小明 255，小红 279。

 限制：科目必须预先写在 SQL 中。如果科目数量动态变化，需要在应用层生成
 SQL，或使用预处理语句构造动态列。
*/


/*
 六、JSON 关系化展开（JSON_TABLE）
 ================================================================

 【语法规则】

 SELECT ...
 FROM main_table AS t
JOIN JSON_TABLE(
     t.json_column,
     'JSON 数组路径' COLUMNS (
         output_col data_type PATH '元素内的相对路径'
     )
 ) AS json_rows ON TRUE;

 JSON_TABLE 将 JSON 文档映射成临时关系表，之后可正常 JOIN、GROUP BY、SUM。
*/

DROP TABLE IF EXISTS p01_json_orders;
CREATE TABLE p01_json_orders (
    id         BIGINT PRIMARY KEY,
    order_no   VARCHAR(30) NOT NULL UNIQUE,
    items_data JSON NOT NULL
) ENGINE = InnoDB;

INSERT INTO p01_json_orders (id, order_no, items_data) VALUES
    (1, 'SO20260820001', JSON_ARRAY(
        JSON_OBJECT('sku_id', 101, 'price', 50.00, 'qty', 2),
        JSON_OBJECT('sku_id', 102, 'price', 30.00, 'qty', 1)
    )),
    (2, 'SO20260820002', JSON_ARRAY(
        JSON_OBJECT('sku_id', 101, 'price', 50.00, 'qty', 3),
        JSON_OBJECT('sku_id', 103, 'price', 80.00, 'qty', 1)
    ));

/*
 【业务场景】把订单中的商品数组拆成明细行，并按 SKU 统计销量和销售额。
*/
SELECT
    item.sku_id,
    SUM(item.qty) AS total_sold_qty,
    SUM(item.price * item.qty) AS total_revenue
FROM p01_json_orders AS orders
JOIN JSON_TABLE(
    orders.items_data,
    '$[*]' COLUMNS (
        sku_id INT           PATH '$.sku_id',
        price  DECIMAL(10, 2) PATH '$.price',
        qty    INT           PATH '$.qty'
    )
) AS item ON TRUE
GROUP BY item.sku_id
ORDER BY item.sku_id;

/*
 预期结果：
 - SKU 101：销量 5，销售额 250。
 - SKU 102：销量 1，销售额 30。
 - SKU 103：销量 1，销售额 80。

 设计提示：高频查询、关联或需要强约束的数据，优先正规化到商品明细表；
 JSON_TABLE 更适合兼容外部载荷、低频分析或逐步迁移 JSON 数据。
*/


/*
 七、深度分页：延迟关联与游标分页
 ================================================================

 【延迟关联语法】

 SELECT full_row.*
 FROM large_table AS full_row
INNER JOIN (
     SELECT id
     FROM large_table
     WHERE filtering_condition
     ORDER BY indexed_col, id
     LIMIT offset, page_size
 ) AS page_ids ON page_ids.id = full_row.id
 ORDER BY full_row.indexed_col, full_row.id;

 思路：先利用较窄的覆盖索引跳过 offset 并取得当前页主键，再只对当前页回表。
*/

DROP TABLE IF EXISTS p01_order_log;
CREATE TABLE p01_order_log (
    id         BIGINT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    status     VARCHAR(20) NOT NULL,
    details    TEXT NOT NULL,
    INDEX idx_order_log_page (created_at DESC, id DESC)
) ENGINE = InnoDB;

INSERT INTO p01_order_log (id, created_at, status, details) VALUES
    (1,  '2026-08-20 12:01:00', 'SUCCESS', REPEAT('日志内容-1 ',  50)),
    (2,  '2026-08-20 12:02:00', 'SUCCESS', REPEAT('日志内容-2 ',  50)),
    (3,  '2026-08-20 12:03:00', 'FAILED',  REPEAT('日志内容-3 ',  50)),
    (4,  '2026-08-20 12:04:00', 'SUCCESS', REPEAT('日志内容-4 ',  50)),
    (5,  '2026-08-20 12:05:00', 'SUCCESS', REPEAT('日志内容-5 ',  50)),
    (6,  '2026-08-20 12:06:00', 'FAILED',  REPEAT('日志内容-6 ',  50)),
    (7,  '2026-08-20 12:07:00', 'SUCCESS', REPEAT('日志内容-7 ',  50)),
    (8,  '2026-08-20 12:08:00', 'SUCCESS', REPEAT('日志内容-8 ',  50)),
    (9,  '2026-08-20 12:09:00', 'FAILED',  REPEAT('日志内容-9 ',  50)),
    (10, '2026-08-20 12:10:00', 'SUCCESS', REPEAT('日志内容-10 ', 50)),
    (11, '2026-08-20 12:11:00', 'SUCCESS', REPEAT('日志内容-11 ', 50)),
    (12, '2026-08-20 12:12:00', 'FAILED',  REPEAT('日志内容-12 ', 50));

-- 传统 OFFSET 分页：为了演示，只跳过 5 行并取 3 行。
SELECT id, created_at, status, details
FROM p01_order_log
ORDER BY created_at DESC, id DESC
LIMIT 5, 3;

/*
 【业务场景 A】延迟关联。

 子查询只读取 (created_at, id) 覆盖索引，得到 id 后再读取 3 行完整 details。
 FORCE INDEX 仅用于让练习时的执行计划更直观；生产中应先用 EXPLAIN ANALYZE
 验证优化器计划，不要习惯性强制索引。
*/
SELECT log_row.id, log_row.created_at, log_row.status, log_row.details
FROM p01_order_log AS log_row
INNER JOIN (
    SELECT id
    FROM p01_order_log FORCE INDEX (idx_order_log_page)
    ORDER BY created_at DESC, id DESC
    LIMIT 5, 3
) AS page_ids ON page_ids.id = log_row.id
ORDER BY log_row.created_at DESC, log_row.id DESC;

/*
 这里两种写法都应返回 id 7、6、5。

 重要限制：延迟关联只是减少读取宽字段和回表的开销，数据库仍要扫描并跳过
 offset 行，所以复杂度仍随页码加深而增长。它不会保证固定的耗时数字。
*/

/*
 【游标分页语法】

 SELECT ...
 FROM large_table
 WHERE indexed_col < 上一页最后值
    OR (indexed_col = 上一页最后值 AND id < 上一页最后id)
 ORDER BY indexed_col DESC, id DESC
 LIMIT page_size;

 【业务场景 B】已知上一页最后一行为：
 created_at = '2026-08-20 12:08:00'，id = 8，继续读取下一页 3 条。

 游标分页直接从索引位置向后读取，更适合信息流和“下一页”；代价是不能方便地
 任意跳到第 N 页。created_at 和 id 共同构成稳定、唯一的翻页游标。
*/
SELECT id, created_at, status, details
FROM p01_order_log
WHERE created_at < '2026-08-20 12:08:00'
   OR (created_at = '2026-08-20 12:08:00' AND id < 8)
ORDER BY created_at DESC, id DESC
LIMIT 3;


/*
 八、学习总结与自测
 ================================================================

 1. 窗口函数
    痛点：组内排名、环比、累计值，同时保留明细行。
    自测：统计每位客户的订单累计金额和订单序号。

 2. 递归 CTE
    痛点：组织架构、类目、权限菜单等树形结构遍历。
    自测：从“智能手机”反向查询到根类目。

 3. LATERAL
    痛点：针对左表的每一行，单独查询相关 Top N 明细。
    自测：取每位客户金额最高的 1 笔订单。

 4. ROLLUP + GROUPING
    痛点：一条 SQL 同时输出明细分组、小计和总计。
    自测：增加“销售日期”维度，观察汇总层级变化。

 5. 条件聚合
    痛点：纵表转横表、多状态指标在一行对比。
    自测：统计每位客户 SUCCESS/FAILED 订单数。

 6. JSON_TABLE
    痛点：把 JSON 数组临时映射为关系行后参与聚合和关联。
    自测：列出每个订单展开后的商品明细，而不是按 SKU 汇总。

 7. 延迟关联 / 游标分页
    痛点：降低深分页宽行读取成本，或避免 offset 扫描。
    自测：用 EXPLAIN ANALYZE 对比三种分页方式的实际执行计划。
*/
