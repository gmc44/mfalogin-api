#!/usr/bin/python3

import json
import requests

class SmsApi:
    def __init__(self):
        self.s = requests.session()
        self.baseurl='https://prosvc.netsize.com'
        tokenendpoint='/ants/api/v2/oauth/token'
        conf={'username':'##netsizeusername##','password':'##netsiezpwd##'}
        headers = {'content-type': 'application/json'}
        proxies = {'https': 'http://##httpsproxy##:3128'}

        r = self.s.post(self.baseurl+tokenendpoint,data=json.dumps(conf),headers=headers,proxies=proxies)

        if r.status_code == 200:
            try:
                self.token=eval(r.content)['access_token']
            except:
                print("Erreur de connexion : aucun token renvoye")
                print(r.read())
        else:
            print(f'Erreur de connexion : {r.status_code}')

    def send(self,num,msg):
        validityminutes=15
        url=self.baseurl+"/ants/api/v2/sms"
        hdr = {'Authorization': f'Bearer {self.token}', 'content-type': 'application/json'}
        payload={
                    "userIds": [num],
                    "message": msg,
                    "senderAddress": "AcaNantes",
                }
        r = self.s.post(url,data=json.dumps(payload), headers=hdr)
        # print(r.text)
        # {"result":[{"id":1859693434,"userId":"33631822673","status":0,"statusDetail":"Pending","type":"SMS"}]}
        if r.status_code==201:
            return(True)
        else:
            return(False)