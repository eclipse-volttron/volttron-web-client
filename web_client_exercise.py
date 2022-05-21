import logging

from volttron.web.client import Authentication, Platforms

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('urllib3.connectionpool').setLevel(level=logging.INFO)

a = Authentication(auth_url="http://localhost:8070/authenticate",
                   username="admin",
                   password="admin")

volttron1 = Platforms().get_platform("volttron1")
historian = volttron1.get_agent('platform.historian')
print(historian.status)
print(historian.rpc.execute('get_topic_list').data)

# for p in Platforms().list():
#     #print(p)
#     for a in p.agents:
#         print("Before set")
#         print(a.configs.enabled)
#         a.configs.set_priority(50)
#         print("After set")
#         print(a.configs.enabled)
#
#         print("Remove priority")
#         a.configs.set_enabled(False)
#         print(a.configs.enabled)
#
#     print(p.status)
