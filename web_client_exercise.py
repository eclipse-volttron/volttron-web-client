import logging

from volttron.web.client import Authentication, Platforms

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('urllib3.connectionpool').setLevel(level=logging.INFO)

a = Authentication(auth_url="http://localhost:8070/authenticate",
                   username="admin",
                   password="admin")

for p in Platforms().list():
    print(p)
    for a in p.agents:
        print(f"\t{a}")
        print(f"\t\t{a.configs}")
        print(f"\t\t\t{a.configs.enabled}")
        print(f"\t\t\t{a.configs.running}")
    print(p.status)
