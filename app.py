from asyncore import read
from crypt import methods
import ipaddress
from flask import Flask, request, abort, Response
import logging
from flasgger import Swagger
from functions import *

app = Flask(__name__)
swagger = Swagger(app)

logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'logging.conf'))
log_file_handler = logging.FileHandler(logging_conf_path)
log = logging.getLogger(__name__)
log.setLevel(level=logging.DEBUG)
log.addHandler(log_file_handler)
#----------------------------------------------------------------------------------------------------
# 1 : sendnotif
#----------------------------------------------------------------------------------------------------
@app.route('/sendnotif',methods=['POST'])
def sendnotif():
    """Envoi une notification de nouvelle connexion par mail sur mail et mails secondaires
    ---
    parameters:
      - name: body
        in: body
        type: string
        required: true
        schema:
          id : sendnotif
          required:
            - uid
          properties:
            uid:
              type: string
              description: user id
    responses:
      200:
        description: OK
    """
    json_data = request.json
    if 'uid' not in json_data:
        return('ERREUR : parametres manquants')

    uid = json_data['uid']

    # requete ldap
    res=ldapsadminapiinfra(f'uid={uid}',['mail','mailrecup','cn','mobilerecup'])

    # Test si on a bien qu'un resultat
    nbres=len(res)
    if nbres == 0:
        return('ERREUR : uid introuvable')
    elif nbres > 1:
        return('ERREUR : plus d\'un resultat avec ce filtre')
    else:
        print(res)
        infoldap=res[0]['attributes']
    
    
    # Recuperation des infos dans ldap
    cn=getattr(infoldap,'cn')
    listmail = []
    listmail.extend(infoldap['mailrecup']) #list
    listmail.append(infoldap['mail']) #ajout du mail
    mobilerecup=infoldap['mobilerecup']

    if mobilerecup == []:
        msg=f'/sendnotif/{uid} ERREUR : pas de mobilerecup sur la fiche de {uid}, on n envoie pas de notif'
        print(msg)
        return(msg)

    res=''
    for mailaddress in listmail:
        res+=envoinotif(mailaddress,cn,mobilerecup)+'\n'
    cleanres=res.replace('\n',', ')
    print(f'sendnotif {uid} - {cleanres}')
    return(res)

#----------------------------------------------------------------------------------------------------
# 2 : sendemail
#----------------------------------------------------------------------------------------------------
mail='''From: ##exp
Organization: Rectorat de Nantes
MIME-Version: 1.0
To: ##dest
##ccdestSubject: ##sujet
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 8bit

##corps'''

@app.route('/sendemail',methods=['POST'])
def sendemail():
    """Envoi d'un mail simple
    ---
    parameters:
      - name: body
        in: body
        type: string
        required: true
        schema:
          id : sendemail
          required:
            - from
            - to
            - subject
            - body
          properties:
            from:
              type: string
              description: from email
            to:
              type: array
              items: {'type': 'string'}
              minItems: 1
              description: to email(s)
            tocc:
              type: array
              items: {'type': 'string'}
              minItems: 1
              description: tocc email(s)
            subject:
              type: string
              description: email subject
            body:
              type: string
              description: email body
    responses:
      200:
        description: OK
    """
    json_data = request.json

    #recuperation des variables
    exp = json_data['from'] #str
    dest = json_data['to'] #list
    sujet = json_data['subject'] 
    corps = json_data['body']
    if 'tocc' in json_data:
        destcc2 = json_data['tocc'] #list
        destcc = 'Cc: ' + ', '.join(destcc2) + '\n'
    else:
        destcc = ''
        destcc2 = []

    #instanciation du mail
    mail2=mail.replace('##exp',exp)
    mail2=mail2.replace('##dest',', '.join(dest))
    mail2=mail2.replace('##ccdest',destcc)
    mail2=mail2.replace('##sujet',sujet)
    mail2=mail2.replace('##corps',corps)

    #envoi du mail
    listdest=list(set(dest+destcc2))
    res=SendMail(mail2,listdest,exp)
    if res == 0:
        return 'mail envoye a ' + ', '.join(listdest)
    else :
        return 'erreur envoi mail'

#----------------------------------------------------------------------------------------------------
# 3 : smartaddattr
#----------------------------------------------------------------------------------------------------
@app.route('/smartaddattr',methods=['POST'])
def smartaddattr():
    """ajoute un attribut ldap ou le remplace s'il existe deja
    ---
    parameters:
      - name: body
        in: body
        type: string
        required: true
        schema:
          id : smartaddattr
          required:
            - bind_dn
            - bind_pwd
            - uid
            - attr
            - value
          properties:
            bind_dn:
              type: string
              description: bind DN account used to addattr
            bind_pwd:
              type: string
            uid:
              type: string
              description: user id
            attr:
              type: string
              description: ldap attr name
            value:
              type: string
              description: ldap attr value
    responses:
      200:
        description: OK
    """
    json_data = request.json
    dn = json_data['bind_dn']
    pwd = json_data['bind_pwd']
    uid = json_data['uid']
    attr = json_data['attr']
    value = json_data['value']
    res=ldapaddattr(dn,pwd,uid,attr,value)
    #Essaie de récupérer le code retour ldap
    try:
        result=res['result']
    except:
        result=1000
    
    msg=f'/smartaddattr/ {uid} '
    if result==0: #La réponse est bonne
        msg+=f'OK : l\'attribut {attr}={value} a ete ajoute'
        print(msg)
        return(msg)
    elif result==20: #La réponse est considérée bonne  (le code 20 signifie que l'attribut existe déjà ce qu'on ne considère pas comme une erreur)
        msg+=f'OK : mais l\'attribut {attr}={value} existait deja'
        print(msg)
        return(msg)
    elif result==65: #L'attribut existe mais a une autre valeur
        #On essaie de remplacer l'attribut
        res=ldapreplaceattr(dn,pwd,uid,attr,value)
        #Essaie de récupérer le code retour ldap
        try:
            result=res['result']
        except:
            result=1000
        if result==0: #La réponse est bonne
            msg+=f'OK : l\'attribut {attr}={value} a ete modifie'
            return(msg)
    #Dans les autres cas, il y a une erreur :
    #Essaie de récupérer le code retour ldap
    try:
        msg+=res['description']+':'+res['message']
    except:
        msg+="erreur inconnue"
    print(msg)
    abort(400, msg)

#----------------------------------------------------------------------------------------------------
# 4 : sendotp
#----------------------------------------------------------------------------------------------------
@app.route('/sendotp',methods=['POST'])
def sendotp():
    """envoi le code otp
    ---
    parameters:
      - name: body
        in: body
        type: string
        required: true
        schema:
          id : sendotp
          required:
            - uid
            - code
          properties:
            uid:
              type: string
              description: user ID
            code:
              type: string
              description: OTP code
            num:
              type: string
              description: mobile number
    responses:
      200:
        description: OK
    """
    json_data = request.json
    if 'uid' not in json_data or 'code' not in json_data:
        return('ERREUR : parametres manquants')

    uid = json_data['uid']
    code = json_data['code']
    if 'num' in json_data:
        num = json_data['num']
    else:
        num = ''

    # requete ldap
    res=ldapsadminapiinfra(f'uid={uid}',['mailrecup','cn','mobilerecup','employeeType'])

    # Test si on a bien qu'un resultat
    try:
        nbres=len(res)
    except:
        nbres=0
    if nbres == 0:
        return('ERREUR : uid introuvable')
    elif nbres > 1:
        return('ERREUR : plus d\'un resultat avec ce filtre')
    else:
        infoldap=res[0]['attributes']
    
    # Recuperation des infos dans ldap
    mailrecup1=getattr(infoldap,'mailrecup')
    cn=getattr(infoldap,'cn')
    employeetype=infoldap['employeeType']
    mobilerecup=infoldap['mobilerecup']
    if mobilerecup == []:
        mobilerecup = ''

    msgvalidation=''
    #traitement du num dans le post, on le prend en compte s'il est valide (meme si il y a un mobilerecup)
    if num != '' and testmobileFR(num):
        mobilerecup=num
        if mobilerecup == '':
            msgvalidation='pour validation du mobile'
        else:
            msgvalidation='pour validation remplacement du mobile'

    #conversion d'un 06 en +336
    if len(mobilerecup) >= 9:
        mobilerecup=f'+33{mobilerecup[-9:]}'

    #on envoie un mail ou un SMS ?
    send='none'
    msgerreur=[]

    #on regarde si attribut mfamail => envoi par mail
    if 'mfamail' in employeetype:
        if mailrecup1 != '' and testemail(mailrecup1): #non vide et valide
            send='email'
        else:
            msgerreur.append('mail non valide')
    else:
        if mobilerecup != '' and testmobile(mobilerecup): #non vide et valide
            send='sms'
        else: #si pas email valide on envoie en sms
            msgerreur.append(f'numero {mobilerecup} non valide')
    
    #c'est parti, on envoie !
    if send == 'email':
        res=envoiemail(mailrecup1,code,cn)
        print(f'{uid} - MAIL envoye a {mailrecup1}- {res}')
    elif send == 'sms':
        res=envoisms(mobilerecup,code,uid)
        print(f'{uid} - SMS envoye a {mobilerecup} {msgvalidation}- {res}')
    else:
        # res=f'connexion impossible {", ".join(msgerreur)}, veuillez renseigner un deuxieme facteur d\'authentification sur moncompte.ac-nantes.fr'
        res=f'connexion impossible {", ".join(msgerreur)}'
        print(f'{uid} - {res}')
    return(txthtml(res))

#----------------------------------------------------------------------------------------------------
# 5 : checkip
#----------------------------------------------------------------------------------------------------
@app.route('/checkip',methods=['POST'])
def checkip():
    """check ip address
    ---
    parameters:
      - name: body
        in: body
        type: string
        required: true
        schema:
          id : checkip
          required:
            - ip
          properties:
            ip:
              type: string
              description: IP Address
    responses:
      200:
        description: OK
      401:
        description: KO
    """
    json_data = request.json
    if 'ip' not in json_data:
        return('ERREUR : parametres manquants')

    ip = json_data['ip']
    
    blacklist=['1.2.3.4','4.6.7.8']

    if ip in blacklist:
      return Response(response="Unauthorized", status=401)
    else:
      return('OK')
#----------------------------------------------------------------------------------------------------
# 6 : checkuseragent
#----------------------------------------------------------------------------------------------------
@app.route('/checkuseragent',methods=['POST'])
def checkuseragent():
    """check user agent
    ---
    parameters:
      - name: body
        in: body
        type: string
        required: true
        schema:
          id : checkuseragent
          required:
            - user-agent
          properties:
            user-agent:
              type: string
              description: Browser User Agent
    responses:
      200:
        description: OK
      401:
        description: KO
    """
    json_data = request.json
    if 'user-agent' not in json_data:
        return('ERREUR : parametres manquants')

    useragent = json_data['user-agent']
    
    blacklist=['torbrowser','MSIE']

    for bl in blacklist:
      if bl in useragent:
        return Response(response="Unauthorized", status=401)

    return('OK')

#----------------------------------------------------------------------------------------------------
# 6 : checkuseragent
#----------------------------------------------------------------------------------------------------
def nbip2cidr(nbip): #convert nb ip to cidr
  import math
  return(32-int(math.log(int(nbip),2)))

class geoipfrance():
  def get(self):
    """geoipfrance : renvoie la liste json des reseaux france a partir de ripe.net"""		
    ripedburl='ftp://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-extended-latest'
    ripedb=getviaproxy(ripedburl).splitlines()
    france=[]
    #rfc1918
    france.append({'net':'10.0.0.0','cidr':8})
    france.append({'net':'172.16.0.0','cidr':12})
    france.append({'net':'192.168.0.0','cidr':16})
    for l in ripedb:
      tl=l.split('|')
      country=tl[1]
      if country == 'FR':
        iptype=tl[2]
        if iptype == 'ipv4':
          net=tl[3]
          cidr=nbip2cidr(tl[4])
          france.append({'net':net,'cidr':cidr})
    return(france)

# ip france en memoire
def initcache():
  global franceSubnets
  listip=set()
  for net in geoipfrance().get():
    ipnet=ipaddress.ip_network(f'{net["net"]}/{net["cidr"]}',False)
    listip.add(ipnet)
  franceSubnets=list(listip)

checkdir('tmp')
ipfrance_cache_file="tmp/ipfrance.db"
try:
  franceSubnets=DBL(ipfrance_cache_file)
except:
    #initialisation puis sauvegarde
    franceSubnets={}
    initcache()
    DBS(ipfrance_cache_file,franceSubnets)

def noMfaNeeded(reason=''):
  log.info('noMfaNeeded : '+reason)
  return "No Mfa Needed"
def mfaNeeded(reason=''):
  log.info('mfaNeeded : '+reason)
  return Response(response="Mfa Needed", status=401)

#test
franceSubnets = [ipaddress.ip_network('1.2.3.0/24'),ipaddress.ip_network('3.4.2.0/24')]

def IpIsSecure(ip):
  global franceSubnets
  try:
    ipaddr = ipaddress.ip_address(ip)
    for net in franceSubnets:
      if ipaddr in net:
        return True
  except:
    log.error(f"impossible d'evaluer l'ip : {ip}")
  return False

def IsAnOtpConnection(authtype):
  #cleartrust authtype = 8 or 9 means rsa otp connection
  if authtype in ('8','9'):
    return True
  return False

def IsABadUserAgent(useragent):
  #user-agent
  uablacklist=['torbrowser','MSIE']
  for useragentstring in uablacklist:
    if useragentstring in useragent:
      return True
  return False

def IsInWorkHours():
  """from monday to friday, from 7AM to 7PM"""
  from datetime import datetime, time, date
  start = time(7, 0, 0)
  end = time(19, 0, 0)
  current = datetime.now().time()
  return start <= current <= end and 0 <= date.today().weekday() <= 4

@app.route('/smartcheckmfaneeded',methods=['POST'])
def smartcheckmfaneeded():
    """smart check if mfa needed
    ---
    parameters:
      - name: body
        in: body
        type: string
        required: true
        schema:
          id : smartcheck
          required:
            - useragent
            - ip
            - authtype
          properties:
            useragent:
              type: string
              description: Browser User Agent
            ip:
              type: string
              description: User IP Address
            authtype:
              type: string
              description: Cleartrust CT-AUTH-TYPE
    responses:
      200:
        description: MFA needed
      401:
        description: no MFA needed
    """
    json_data = request.json

    if 'useragent' not in json_data or 'ip' not in json_data or 'authtype' not in json_data:
        return('ERREUR : parametres manquants')

    #ip


    useragent = json_data['useragent']
    ip =        json_data['ip']
    authtype =  json_data['authtype']


    log.info(f'Call : {json_data}')

    # Si User Agent in BlackList => MFA
    if IsABadUserAgent(useragent):
      return mfaNeeded('Bad user agent')
    
    # Sinon si connexion Otp => pas de MFA
    elif IsAnOtpConnection(authtype):
      return noMfaNeeded('Otp connection')
    
    # Sinon si ip secure et heures de travail
    elif IpIsSecure(ip) and IsInWorkHours():
      return noMfaNeeded('ip is secure and workhours')

    # Sinon MFA
    else:
      return mfaNeeded('else')

@app.route('/reloadfrancesubnets')
def reloadCheckIP():
    """reloadfrancesubnets
    ---
    responses:
      200:
        description: OK
      401:
        description: KO
    """
    global franceSubnets
    franceSubnets={}
    initcache()
    DBS(ipfrance_cache_file,franceSubnets)
    return("liste rechargee")

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
