# ===========list（列表）≈ Java的ArrayList =============
langs  = ["Java","Python","GO"]
langs.append("C++")  # ≈ list.add()
print("列表：", langs)
print("第一个：",langs[0])
print("最后一个",langs[-1])
print("切片，前两个：",langs[0:2])
print("长度：",len(langs))

# ===========dict（字典）≈ HashMap =============
user = {"name":"suyu","age":21,"job":"Java后端"}
print("\n字典：",user)
print("取值：",user["name"])         # 根据键取值 map.get(key)
user["city"] =  "上海"               # 加/改键值对 map.put()
print("判断字段是否存在字典：","city" in user)     # 用in判断 map.contains(key)

print()

# ===========遍历字典（最常用写法） =============
for key,value in user.items():          # ≈ Java的entrySet()
  print(f" {key}={value} ")

print()

# =========== set(集合) ≈ Java中HashSet：去重、无序 =============
tags = {"ai","Java","ai","Python","java"}    # 重复的自动去除
print("集合，重复的自动去除：",tags)
tags.add("agent")
print("agent是否在tags中：","agent" in tags)





