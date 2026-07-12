# ================ 基本类型注释：参数：类型  返回值使用 -> 类型 =================
from unicodedata import name


def add(num1 : int,num2 : int) -> int:
  return num1 + num2

def greet(name : str) -> str:
  return f"Hello, {name}"

print(add(10,1))
print(greet("suyu"))

# ================ 基本类型注释：参数：类型  返回值使用 -> 类型 (复杂类型)=================
def total(nums : list[int]) -> int:         # 参数是int值的列表
  return sum(nums)

def get_user() -> dict[str,str]:
  return {"name":"suyu","age":"21","job":"Java后端"}

print(total([1,3,43]))
print(get_user())

print(total([2,4,5]))

print(add("Java", "Python"))   # add 标着要 int，我偏传字符串
