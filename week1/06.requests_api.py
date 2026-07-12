import requests     # Python版的RestTemplate

# ================= ①最简单的GET请求 ==================
# 调用github的公开api 获取用户信息
url = "https://api.github.com/users/suyu7789-ux"
res = requests.get(url)      # 发送get请求并获取返回结果

# ================= ②http请求结果状态码 ==================
print("状态码：",res.status_code)

# ================= ③把返回结果的json转换成python的dict ==================
data = res.json()
print("返回数据:",data)

# ================= ④从dict里取字段 ==================
print("用户名：",data["login"])
print("头像：",data["avatar_url"])
print("用户id：",data["id"])
print("公开仓库数：",data["public_repos"])
print("注册时间：",data["created_at"])

# ================= ⑤带请求参数的get (URL拼 ?key=value) ==================
# 搜索github上跟python相关，star最多的仓库
search_url = "https://api.github.com/search/repositories"
param = {"q":"language:python","sort":"stars","per_page":3}
resp2 = requests.get(search_url, params=param)         #param自动拼成 ?q=...&sort=...&per_page=
print("\n== Python star 最多的三个仓库 ==")
for repo in resp2.json()["items"]:
    print(f" {repo['full_name']}  ⭐️{repo['stargazers_count']}")
