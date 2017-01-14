
这是一个使用django跟django-rest-framework的示例项目, 有几点参考意义:

- User使用的是扩展至django的AbstractUser类. 管理控制台关于user也自定义了Form
具体可参考 [models.py关于UserInfo的定义](tg/models.py)

- 用户登陆那块使用的是django的扩展机制.
具体可参考 [authbackends.py](tg/authbackends.py)

- django-rest-framework使用的是jwt及修改基于浏览器的session认证api调用时,去掉csrf的检查.
具体可参考 [authentication.py](tg/authentication.py)

