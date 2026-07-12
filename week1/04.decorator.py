import time

# ============== 装饰器 等于Java中的AOP 可以对原有的方法做增强处理 ==============
def log_and_timer(func):      # func为接收的原函数
  def wrapper(*args,**kwargs):    #里面定义一个增强方法 接收原有函数的所有参数
    start = time.time()
    print(f"方法{func.__name__}开始执行，开始执行时间为：{start}s")  # 方法执行前 记录日志及开始时间
    result = func(*args,**kwargs)                              # 方法执行 并拦截结果
    end = time.time()
    print(f"方法{func.__name__}执行完成，结束时间为：{end}s")       # 方法执行完成 记录日志及执行结束时间
    print(f"方法{func.__name__}执行耗时为：{end-start}s，执行结果：{result}")
    return result                                              # 将执行结果返回
  return wrapper

@log_and_timer
def slow_add(num1,num2):
  time.sleep(0.5)
  return num1+num2

print(slow_add(1,2))


