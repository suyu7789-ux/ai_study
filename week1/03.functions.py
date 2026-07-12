# =============== 基本函数：def 定义 (≈ Java方法 但是不需要定义在类内) ================
def greet(name):
  return f"Hello {name}"

print(greet("suyu"))

print()

def greet2(name,greeting = "你好"):
  return f"{greeting},{name}"     # greeting有默认值


print(greet2("suyu"))                        # 使用greeting定默认值
print(greet2("suyu","早上好"))  # 覆盖greeting的默认值

print()

# =============== 关键字参数 ================
print(greet2(name="苏语",greeting="Good night"))

print()

# =============== *args 接收任意多个“位置参数”，打包成tuple ================
def total(*nums):               # nums是一个元组
  print("接收到的参数：",nums)
  return sum(nums)

print("求和：",total(1,2,3,4,5,6))

print()

# =============== **kwargs 接收任意多个“关键字参数”，打包成dict ================
def build_user(**kwargs):
  print("收到的键值：",kwargs)
  return kwargs

build_user(name = "suyu",age = 21,job = "Java后端")


