# =============== f-String 模版字符串 ================
name = "suyu"
age = 21
print(f"我的名字是{name},今年{age}岁啦～")
# {}里面可以放变量，表达式和计算式
print(f"23 + 1 = {23+1}")
# :.2f控制输出格式
price = 9.9
print(f"单价：{price:.2f}")

print()
# =============== 列表推导式 ================
# 需求：生成1～5的平方
# Java写法需要循环 list.add(result)
squares = [x * x for x in range(1,6)]     # range(1,6)  => 1,2,3,4,5 包含开头不包含结尾
print("平方：",squares)

# 带条件：只要偶数的平方
even_squares = [ x * x for x in range(1,11) if x % 2 == 0 ]
print("偶数的平方：",even_squares)

# 加工字符串列表，全部转大写
langs = ["java","ai","python"]
upper_langs = [s.upper() for s in langs]
print("大写：",upper_langs)

# 字典推导式
names = ["Mike","Jerry","Tom"]
names_len = {name:len(name) for name in names}
print("名字长度：",names_len)
