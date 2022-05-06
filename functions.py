import ldap3
import re
import os
import pickle
from sms_api import SmsApi

#----------- definitions -----------

ldapServer='##ldapServer##.ac-nantes.fr'
ldapMasterServer='##ldapMasterServer##.ac-nantes.fr'
ldapSearchBase='o=gouv,c=fr'
ldapUserDn='uid=##ldapUserDn##,ou=ac-nantes,ou=education,o=gouv,c=fr'
ldapUserPwd='##ldapUserPwd##'
sms='''Pour sécuriser l\'accès à votre compte académique, voici votre code de vérification :
##CODE'''
smtp = 'smtp.in.ac-nantes.fr'
mailnotif='''From: "Academie de Nantes" <ne-pas-repondre@ac-nantes.fr>
Organization: Rectorat de Nantes
MIME-Version: 1.0
To: ##TO
Subject: Notification de connexion avec un nouveau numero de mobile
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 8bit

<html>
 <head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <title>Notification de connexion avec un nouveau num&eacute;ro de mobile</title>
 </head>
 <body style="margin:0; padding: 0;">
  <table bgcolor="#f1f1f1" width="100%" height="100%" align="center" height="60" style="border-collapse: collapse"  border="0" cellspacing="0" cellpadding="0">
   <tr align="center">
    <td valign="top">
     <table bgcolor="#f1f1f1" height="75" style="border-collapse:collapse"  border="0" cellspacing="0" cellpadding="0">
      <tr valign="middle" height="40">
       <td style="width:5%"></td>
       <td style="width:30%" valign="middle">
        <img src="http://moncompte.ac-nantes.fr/images/academie-logo-3-vert-tr.png" border="0" alt="Acad&eacute;mie de Nantes" style="display:block;" height="70">&nbsp;
       </td>
       <td style="width:55%; font-size:13px; font-family:arial, sans-serif; color:#777777; text-align:right">##CN
       </td>
       <td style="width:7%">
        <img src="http://moncompte.ac-nantes.fr/images/icon-person.png" border="0" style="display:block;" height="70"> <!-- alt="oOo"  -->
       </td>
       <td style="width:3%"></td>
      </tr>
     </table>
     <table  width="90%"  border="1" bordercolor="#e5e5e5" cellspacing="0" cellpadding="0" bgcolor="#ffffff" style="text-align:left">
      <tr>
       <td style="height:15px; border-top:none; border-bottom:none; border-left:none; border-right:none;"></td>
      </tr>
      <tr>
       <td style="width:5%; border-top:none; border-bottom:none; border-left:none; border-right:none;"></td>
       <td valign="top" style="width:90%; font-size:83%; border-top:none; border-bottom:none; border-left:none; border-right:none; font-size:13px; font-family:arial, sans-serif; color:#222222; line-height:18px">
        Bonjour,<br /><br />
        Pour information, le num&eacute;ro de t&eacute;l&eacute;phone mobile ##MOBILE a &eacute;t&eacute; utilis&eacute; pour une connexion s&eacute;curis&eacute;e (&agrave; double facteur).<br /><br />
        <b>Si vous n'&ecirc;tes pas &agrave; l'initiative de cette connexion, nous vous recommandons de modifier au plus vite votre mot de passe.</b><br /><br />
        Cordialement,<br /><br />
        Acad&eacute;mie de Nantes<br /><br />
       </td>
       <td style="width:5%; border-top:none; border-bottom:none; border-left:none; border-right:none;"></td>
      </tr>
      <tr>
       <td style="border-top:none; border-bottom:none; border-left:none; border-right:none;"></td>
      </tr>
      <tr>
       <td style="width:5%; border-top:none; border-bottom:none; border-left:none; border-right:none;"></td>
       <td style="width:90%; font-size:11px; font-family:arial, sans-serif; color:#666666; border-top:none; border-bottom:none; border-left:none; border-right:none;">
        Cette notification vous a &eacute;t&eacute; envoy&eacute;e par e-mail afin de renforcer la s&eacute;curit&eacute; de votre compte acad&eacute;mique. Cette adresse e-mail n'accepte pas les r&eacute;ponses.<br /><br />
       </td>
       <td style="width:5%; border-top:none; border-bottom:none; border-left:none; border-right:none;"></td>
      </tr>
      <tr>
       <td style="border-top:none; border-bottom:none; border-left:none; border-right:none;"></td>
      </tr>
     </table>
     <table  bgcolor="#f1f1f1" height="50" style="text-align:left">
      <tr valign="middle">
       <td style="font-size:11px; font-family:arial, sans-serif; color:#777777;">
        <div  style="direction:ltr;">
         Rectorat de l'Acad&eacute;mie de Nantes 4, rue de la Houssiniere - BP 72616 - 44326 Nantes CEDEX 03
        </div>
       </td>
      </tr>
     </table>
    </td>
   </tr>
  </table>
 </body>
</html>
'''
mnethead='''From: "Academie de Nantes" <ne-pas-repondre@ac-nantes.fr>
Organization: Rectorat de Nantes
MIME-Version: 1.0
To: net@ac-nantes.fr
'''
mnetbody='''
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 8bit

<html>
 <head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <title>##CODE Code de connexion Academie de Nantes</title>
 </head>
 <body style="margin:0; padding: 0;">
 '''

#---------------------------------- Fonctions diverses
def txthtml(json):
    from flask import make_response
    rep = make_response(str(json))
    rep.headers['content-type'] = 'text/html'
    return(rep)

#---------------------------------- Fonctions ldap
def ldaps(searchFilter,retrieveAttributes):
    conn = ldap3.Connection(ldapServer, auto_bind=True)
    if conn.search(ldapSearchBase,'(&('+searchFilter+'))',attributes=retrieveAttributes):
        return eval(conn.response_to_json())['entries']
    else:
        return 0

# ldaps avec bind utilisateur
def ldapsbind(searchFilter,retrieveAttributes,user_dn,user_pwd):
    conn = ldap3.Connection(ldapServer, user=user_dn, password=user_pwd, auto_bind=True)
    if conn.search(ldapSearchBase,'(&('+searchFilter+'))',attributes=retrieveAttributes):
        return eval(conn.response_to_json())['entries']
    else:
        return 0

# ldaps avec uid=admin-apiinfra
def ldapsadminapiinfra(searchFilter,retrieveAttributes):
    return(ldapsbind(searchFilter,retrieveAttributes,ldapUserDn,ldapUserPwd))

def getattr(ldapinfo,attr,index=0):
    try:
        return(ldapinfo[attr][index])
    except:
        return('')

def ldapmodify(bind_dn,bind_pwd,uid,dn,values):
    c = ldap3.Connection(ldap3.Server(ldapMasterServer), user=bind_dn, password=bind_pwd)
    c.bind()
    c.modify(dn,values)
    return(c.result)

def ldapgetdn(uid):
    res=ldaps("uid=%s" % uid,ldap3.NO_ATTRIBUTES)
    try:
        return(str(res[0]['dn']))
    except:
        return("")

def ldapaddattr(bind_dn,bind_pwd,uid,attr,value):
    return(ldapmodify(bind_dn,bind_pwd,uid,ldapgetdn(uid),{attr: [(ldap3.MODIFY_ADD, [value])]}))

def ldapreplaceattr(bind_dn,bind_pwd,uid,attr,value):
    return(ldapmodify(bind_dn,bind_pwd,uid,ldapgetdn(uid),{attr: [(ldap3.MODIFY_REPLACE, [value])]}))

#---------------------------------- Fonctions Email

#SendMail : envoi un mail à une liste de destinataires
def SendMail(mail,dest,exp):
    import smtplib
    try:
        s = smtplib.SMTP(smtp)
        s.sendmail(exp, dest, mail.encode('utf-8'))
        s.quit()
        return 0
    except:
        print("Erreur d'envoi du mail")
        return 1

def envoinotif(mailaddress,cn,mobile):
    mail2=mailnotif.replace('##TO',mailaddress)
    mail2=mail2.replace('##CN',cn)
    mail2=mail2.replace('##MOBILE',mobile)
    SendMail(mail2,mailaddress,'ne-pas-repondre@ac-nantes.fr')
    return(f'notif envoye a {mailaddress}')

def testemail(mail):
    try:
        regex = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$' #valide une adresse email
        return(re.match(regex,mail))
    except:
        return(False)

def hideemail(mail):
    dom=mail.split('@')[1]
    paddinglen=len(mail)-len(dom)-3
    padding=''.join('*'*paddinglen)
    return(f'{mail[0:2]}{padding}@{dom}')

def envoiemail(mailrecup1,code,cn):
    mail2=mail.replace('##TO',mailrecup1)
    mail2=mail2.replace('##CODE',code)
    mail2=mail2.replace('##CN',cn)
    SendMail(mail2,mailrecup1,'ne-pas-repondre@ac-nantes.fr')
    return(f'email à l\'adresse {hideemail(mailrecup1)}')

#---------------------------------- Fonctions Mobile

def hidemobile(numero):
    return(f'+{numero[1:5]}*****{numero[-2:]}')

def testmobileFR(numero):
    try:
        regex=r'^0[6-7][0-9]{8}$' #valide un numero de portable francais en 06 ou 07
        return(re.match(regex,numero))
    except:
        return(False)

def testmobile(numero):
    try:
        regex=r'^[+]33[6-7][0-9]{8}$' #valide un numero de portable francais en +336 ou +337
        return(re.match(regex,numero))
    except:
        return(False)

def envoisms(numero,code,uid):
    # if numero in getmobileblacklist().keys():
    blacklist=['+33631823683','+33757181240']
    if numero in blacklist:
        SendMail(f'{mnethead}Subject: [mobileblacklist] {uid} a essaye de se connecter avec le {numero}{mnetbody}Attention : le compte {uid} a essaye de se connecter avec le {numero} qui est blackliste','net@ac-nantes.fr','ne-pas-repondre@ac-nantes.fr')
        return(f'.. numero bloqué')
        
    msg=sms.replace('##CODE',code)
    
    # ---------------- OVH --------------------
    # param = {'account':'sms-xxxxxx-1',
    #          'login':'apisms',
    #          'password':'xxxxxx',
    #          'from':'AcaNantes',
    #          'to':f'0033{numero[3:]}',
    #          'message':f'{msg}',
    #          'noStop':'1',
    #          }
    # from urllib.parse import urlencode, quote_plus
    # paramencode = urlencode(param, quote_via=quote_plus)
    # url=f'https://www.ovh.com/cgi-bin/sms/http2sms.cgi?{paramencode}'
    # res=getviaproxy(url)

    # ---------------- NetSize --------------------
    smsapi=SmsApi()
    if smsapi.send(numero,msg):
        return(f'SMS au numero {hidemobile(numero)}')
    else:
        log.warning(f"erreur d'envoi au numero {numero}")
        return(".. erreur d'envoi du SMS")

def getviaproxy(url):
    proto=url.split(':')[0]
    proxy_host='proxy.ac-nantes.fr:3128'
    if proto[:4] == 'http': #valide pour http ou https
        import urllib3
        proxy = urllib3.ProxyManager(f'http://{proxy_host}/')
        rep = proxy.request('GET', url)
        res = rep.data.decode('utf-8')
    elif proto == 'ftp':
        import urllib.request
        req=urllib.request.Request(url)
        req.set_proxy(proxy_host, 'http')
        res=urllib.request.urlopen(req).read().decode('utf-8')
    else:
        res='protocole invalide http,https,ftp'
    return(res)

def checkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

#Utilisation de base pickle
def DBL(fic):		return pickle.load(open(fic, "rb")) #DB Load
def DBS(fic,dic):	return pickle.dump(dic, open(fic, "wb")) #DB Save