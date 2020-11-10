import requests
import xmltodict
import urllib2
from urllib2 import Request, urlopen, URLError, HTTPError
from mw1_backend.configs import CUDBIP,CUDB_SERVER_URL , CUDBUserName , CUDBPass , CUDBLOGPATH , CUDBDEBUG
from cudbParser import *
from cudbXML import login,logout,AddUser,UpdateUser,ADDOptionPack,ADDOptionPack2,DeleteOptionPack,viewOptionPack,addRadiusReplyItem,AddNPID,addpassword,GetUser,GetDSLDetails
import time
import logging
logger = logging.getLogger(__name__)
import time
import datetime
from lxml import etree
import string
import random
import crypt
from .models import LDAPStatus

#################################################################################################################################################################Section 1 : functions used in all webservices ################################################################################################################################################################################################################################
def checkconnection():
   req = urllib2.Request(CUDB_SERVER_URL)
   try:
     urllib2.urlopen(req,timeout=2)
     return {'action_result': True, 'action_error_message': ""}
   except URLError, e:
     return {'action_result': False, 'action_error_message': str(e.reason)}

def errorCodeMapping(argument): 
    switcher = { 
		1001:"Invalid SessionId",
                1002:"Session Timeout",
                1003:"SessionId Syntax Error",
                1006:"Mandatory Parameter is missing",
        1101:"Invalid SequenceId",
        1201:"Invalid TransactionId",
        1301:"Invalid Context",
        2001:"Invalid Managed Object Type",
        2002:"Invalid Managed Object Id",
        2003:"Unsupported Data Type",
        2999:"Other Request Error",
        3001:"Operation Not Allowed",
        3002:"Object Does Not Exist",
        3003:"Object Already Exists",
        3004:"Invalid User ID",
        3005:"Invalid Password",
        3006:"Invalid SessionId",
        3007:"Invalid Filter",
        3008:"Invalid Subscription ID",
        3009:"Invalid Managed Object ID",
        3010:"Invalid MO Attribute",
        3011:"Insufficient MO Attributes",
        3012:"Insufficient Parameter",
        3013:"Invalid Parameter",
        3014:"Login Failure",
        3015:"Wrong UserName or password",
        3999:"Other Client Error",
        4001:"Operation Not Supported.",
        4002:"Object Not Supported.",
        4003:"Filter Not Supported",
        4004:"Function Busy",
        4005:"Internal Fatal Error",
        4006:"External Error",
        4007:"CAI3G Version Not Supported",
        4008:"MO Version Not Supported",
        4009:"Reached the limitation",
        4010:"Reached the limitation",
        4999:"Other Server Error",
        3:"Time limit exceeded",
        11:"Administrative limit exceeded",
        51:"Busy or Overload or congestion",
        52:"CUDB node is unavailable to process requests",
        53:"Unwilling to perform",
        80:"A problem in an internal in cudb component or resource that prevents CUDB from successfully processing the request",
    } 
    return switcher.get(argument, "error code not exist")

def logcudb(request,response):
  if CUDBDEBUG:
   timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H:%M:%S')
   log=str(timestamp)+"  \n"+request+"\n"+convertToPrerryXML(str(response.text))+"\n"
   today=time.strftime("%Y-%m-%d")
   f = open(CUDBLOGPATH+"cudb."+today+".log", "a")
   f.write(log+"\n")

def crypt_password(user_password):
        char_set = string.ascii_uppercase + string.digits
        salt = ''.join(random.sample(char_set, 8))
        salt = '$1$' + salt + '$'
        pwd = "{CRYPT}" + crypt.crypt(str(user_password), salt)
        return pwd


def convertToPrerryXML(xml_str):
    root = etree.fromstring(xml_str)
    return etree.tostring(root, pretty_print=True)

###################################################################################################################################
################################section 2 : services for login and logout##########################################################
###################################################################################################################################
def Logins():
  requestLogin = login%(CUDBUserName,CUDBPass)
  try:
   response = requests.post(CUDB_SERVER_URL, data=requestLogin)
  except Exception as e:
    return {'action_result': True, 'action_error_message': "error to send login request"+str(e)}
  try:
   StatusMessage=getStatusMessage(response,'Login')
   StatusCode=getStatusCode(response,'Login')
   if StatusMessage =="Success":
      SessionId=getSessionId(response)
      return {'action_result': True, 'action_error_message': "",'SessionId':SessionId}
   else:
     errorCodemap=errorCodeMapping(int(StatusCode))
     error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
     logcudb(requestLogin,response)
     return {'action_result': False, 'action_error_message':error_message }
  except Exception as e:
    return {'action_result': False, 'action_error_message':str(e) }


def Logouts(SessionId):
    requestLogout = logout%(SessionId)
    try:
      response = requests.post(CUDB_SERVER_URL, data=requestLogout)
    except Exception as e:
      logger.error(str(e))
    try:
     StatusMessage=getStatusMessage(response,'Logout')
     StatusCode=getStatusCode(response,'Logout')
     if StatusMessage !="Success":
        errorCodemap=errorCodeMapping(int(StatusCode))
        error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
        logger.error("can't logout session"+str(SessionId)+" due to "+ error_message)
        logcudb(requestLogout,response)
    except Exception as e:
      if response: logcudb(requestLogout,response) 

###################################################################################################################################
################################### section 3 : services for production MW For Provisionin ########################################
###################################################################################################################################

def UpdateUsers(SessionId,username,servicename):
    request = UpdateUser%(SessionId,username,servicename)
    try:
      response = requests.post(CUDB_SERVER_URL, data=request)
    except Exception as e:
      logger.error(str(e))
      return ("cant send UpdateService request with error"+str(e))
    try:
     StatusMessage=getStatusMessage(response,'updateUser')
     StatusCode=getStatusCode(response,'updateUser')
     if StatusMessage =="Success":
        return "Done"
     else:
        logcudb(request,response)
        return "can't update User service with error with error code : "+StatusCode
    except Exception as e:
	    if response: logcudb(request,response)
            return "error happened during update service profile : "+str(e)


def create_or_change_service_cudb(username,service_name):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request=AddUser%(SessionId,username,service_name)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'AddUser')
              StatusCode=getStatusCode(response,'AddUser')
              if StatusMessage =="Success":
                 Logouts(SessionId)
                 return {'action_result': True, 'action_error_message': "done created"}
              else:
                 if StatusCode == "104102":
                    UpdateUserProfile=UpdateUsers(SessionId,username,service_name)
		    if UpdateUserProfile == "Done":
                         Logouts(SessionId)
                         try:
                          logging = LDAPStatus.objects.using('daily_usage_db').create(username =username , status = False , service_name = service_name )
                         except:
                             pass
			 return {'action_result': True, 'action_error_message': "updated"}
	            else:
                         Logouts(SessionId)
			 return {'action_result': False, 'action_error_message': "can't update service user "+UpdateUserProfile}     
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 logcudb(request,response)
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
      return  {'action_result': False, 'action_error_message': "connection error with cudb" }


def suspendSubscriber(username):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = GetUser%(SessionId,username)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               Logouts(SessionId)
               logger.error("Error to send request to CUDB"+str(e))
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'GetUser')
              StatusCode=getStatusCode(response,'GetUser')
              if StatusMessage =="Success":
                 service=getGetUserService(response,'GetUser')
	         if "SUSPENDED_SERVICE" in service:
                    Logouts(SessionId)
	            return {'action_result': False, 'action_error_message':"User "+username+" is already suspended"}
	         Addsuspend=service+";SUSPENDED_SERVICE"
                 return create_or_change_service_cudb(username,Addsuspend)
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
                 logcudb(request,response)
             except Exception as e:
                Logouts(SessionId)
                logger.error('cant parse cudb response due to'+str(e))
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
      return  {'action_result': False, 'action_error_message': "connection error with cudb" }


def activateSubscriber(username):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = GetUser%(SessionId,username)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'GetUser')
              StatusCode=getStatusCode(response,'GetUser')
              if StatusMessage =="Success":
                 service=getGetUserService(response,'GetUser')
                 if "SUSPENDED_SERVICE" not in service:
                    Logouts(SessionId)    
                    return {'action_result': False, 'action_error_message':"User "+username+"is already active"}
                 removesuspend=service.replace(";SUSPENDED_SERVICE",'')
                 return create_or_change_service_cudb(username,removesuspend)
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
                 logcudb(request,response)
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
       logger.error("connection error with cudb due to"+str(connection['action_error_message']))
       return  {'action_result': False, 'action_error_message': "connection error with cudb" }

def getSubscriberStatus(username):
   connection=checkconnection()
   if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = GetUser%(SessionId,username)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'GetUser')
              StatusCode=getStatusCode(response,'GetUser')
              if StatusMessage =="Success":
                 service=getGetUserService(response,'GetUser')
                 if "SUSPENDED_SERVICE" not in service:
                    Logouts(SessionId)
                    return {'action_result': True, 'action_error_message':"active"}
	         else:
                    Logouts(SessionId)   
	            return {'action_result': True, 'action_error_message':"inactive"}
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
		 logcudb(request,response)
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
 
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
   else:
       logger.error("connection error with cudb due to"+str(connection['action_error_message']))
       return  {'action_result': False, 'action_error_message': "connection error with cudb" }

def listAAAServices(username):
   connection=checkconnection()
   if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = GetUser%(SessionId,username)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'GetUser')
              StatusCode=getStatusCode(response,'GetUser')
              if StatusMessage =="Success":
                 service=getGetUserService(response,'GetUser')
                 service=service.split(';')
                 Logouts(SessionId)
                 return {'action_result': True, 'services':service}
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 logcudb(request,response)
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }

             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
   else:
       logger.error("connection error with cudb due to"+str(connection['action_error_message']))
       return  {'action_result': False, 'action_error_message': "connection error with cudb" }

#################################################################################################################################
############################section 4:  services for OptionPack #################################################################
#################################################################################################################################

def create_or_change_optionpackcudb(user_name,WanIp,WanMask,route,lanip,zone,zone2):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             if zone2 =="Not exist":
                request = ADDOptionPack%(SessionId,user_name,WanIp,WanMask,route,lanip,zone)
             else:
              request = ADDOptionPack2%(SessionId,user_name,WanIp,WanMask,route,lanip,zone,zone2)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send ADDOptionPack request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'ADDOptionPack')
              StatusCode=getStatusCode(response,'ADDOptionPack')
              if StatusMessage =="Success":
                 Logouts(SessionId)
                 return {'action_result': True, 'action_error_message': ""}
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%user_name}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
                 logcudb(request,response)
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
      return  {'action_result': False, 'action_error_message': "connection error with cudb" }



def showOptionPack(username):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = viewOptionPack%(SessionId,username)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'viewOptionPack')
              StatusCode=getStatusCode(response,'viewOptionPack')
              if StatusMessage =="Success":
			 zone=getzone(response)
                         WanIp=getWanIp(response)
                         WanMask=getWanMask(response)
                         route=getroute(response)
                         lanip=getlanip(response)
	                 result = {'action_result': True, 'action_error_message': ""}
                         op = {}
                         if zone: op['zone']=zone
                         if WanIp: op['WanIp']=WanIp
                         if WanMask: op['WanMask']=WanMask
                         if route: op['route']=route
                         if lanip: op['lanip']=lanip
			 result.update(op)
                         Logouts(SessionId)
                         return result
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
                 logcudb(request,response)
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
      return  {'action_result': False, 'action_error_message': "connection error with cudb" }

def addRadiusReplyItems(sessionID,user_name):
    defaultPool='cisco-avpair = \"ip:addr-pool=TEDATA\"'
    request = addRadiusReplyItem%(sessionID,user_name,defaultPool)
    try:
      response = requests.post(CUDB_SERVER_URL, data=request)
    except Exception as e:
      logger.error(str(e))
      return (str(e))
    try:
     StatusMessage=getStatusMessage(response,'ADSLModify')
     StatusCode=getStatusCode(response,'ADSLModify')
     if StatusMessage =="Success":
        return "Done"
     else:
        return "can't add RadiusReplyItem with error "
        logcudb(request,response)
    except Exception as e:
        return str(e)
		
def removeOptionPack(user_name):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = DeleteOptionPack%(SessionId,user_name)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send removeOptionPack request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'DeleteOptionPack')
              StatusCode=getStatusCode(response,'DeleteOptionPack')
              if StatusMessage =="Success":
                 defaultpool=addRadiusReplyItems(SessionId,user_name)
                 if defaultpool=='Done':
                    Logouts(SessionId)
                    return {'action_result': True, 'action_error_message': ""}
                 else:
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "removed by can't add default pool "+defaultpool}
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%user_name}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
                 logcudb(request,response)
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
########################################################################################################################################
##########################section 5 :services for (Ldap Manager )add password / nspid ( Lab only ) #####################################
########################################################################################################################################

def create_or_change_NPIDcudb(username,NPID):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']             
             request = AddNPID%(SessionId,username,NPID)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'AddNPID')
              StatusCode=getStatusCode(response,'AddNPID')
              if StatusMessage =="Success":
                 Logouts(SessionId)
                 return {'action_result': True, 'action_error_message': ""}
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
                 logcudb(request,response)
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }  
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
      return  {'action_result': False, 'action_error_message': "connection error with cudb" } 

def add_or_edit_passwordcudb(username,password): 
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = addpassword%(SessionId,username,password,crypt_password(password))
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'ResetUserPassword')
              StatusCode=getStatusCode(response,'ResetUserPassword')
              if StatusMessage =="Success":
                 Logouts(SessionId)
                 return {'action_result': True, 'action_error_message': ""}
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
                 logcudb(request,response)
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                Logouts(SessionId)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
      return  {'action_result': False, 'action_error_message': "connection error with cudb" }

def get_option_pack(SessionId,username):
    request = viewOptionPack%(SessionId,username)
    try:
      response = requests.post(CUDB_SERVER_URL, data=request)
    except Exception as e:
      logger.error(str(e))
      return None
    try:
     StatusMessage=getStatusMessage(response,'viewOptionPack')
     StatusCode=getStatusCode(response,'viewOptionPack')
     if StatusMessage =="Success":
        zone=getzone(response)
        WanIp=getWanIp(response)
        WanMask=getWanMask(response)
        route=getroute(response)
        lanip=getlanip(response)
        op = {}
        if zone: op['zone']=zone
        if WanIp: op['WanIp']=WanIp
        if WanMask: op['WanMask']=WanMask
        if route: op['route']=route
        if lanip: op['lanip']=lanip
        return op
    except:
       logger.error("can't parse viewoptionPack")
       return None

def get_cudb_profilecudb(username):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = GetUser%(SessionId,username)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'GetUser')
              StatusCode=getStatusCode(response,'GetUser')
              if StatusMessage =="Success":
                 service=getGetUserService(response,'GetUser')
                 Profile= {'action_result': True, 'action_error_message': "",'service':service}
                 try:
                  request=GetDSLDetails%(SessionId,username)
                 except:
                   Logouts(SessionId)
                   return {'action_result': False, 'action_error_message': "error set request",'service':service}
                 try:
                   response = requests.post(CUDB_SERVER_URL, data=request)
                   logger.error(convertToPrerryXML(str(response.text)))
                 except Exception as e:
                   logger.error("Error to send request to CUDB"+str(e))
                   Logouts(SessionId)   
                   return {'action_result': False, 'action_error_message': "error to get ADSL profile"}
                 try:
                    StatusMessage=getStatusMessage(response,'GetDSLDetails')
                    StatusCode=getStatusCode(response,'GetDSLDetails')
                    logger.error(StatusMessage)
                    if StatusMessage =="Success":
                       radiusReplyItem=getRadiusReplayItem(response)
                       password=getpassword(response)
                       NPID=getNPID(response)
                       if radiusReplyItem: Profile['radiusReplyItem']=radiusReplyItem
                       if password: Profile['password']=password
                       if NPID: Profile['NPID']=NPID
                       if get_option_pack(SessionId,username):Profile.update(get_option_pack(SessionId,username))
                       Logouts(SessionId)
                       return Profile
                    else:
                      errorCodemap=errorCodeMapping(int(StatusCode))
                      error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                      Logouts(SessionId)
                      return  {'action_result': False, 'action_error_message':error_message , 'service':service } 
                 except Exception as e:
                    logger.error('cant parse cudb response due to'+str(e))
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "error to get ADSL profile"}
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 logcudb(request,response)
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                logcudb(request,response)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
      return  {'action_result': False, 'action_error_message': "connection error with cudb" }

def get_full_cudb_profilecudb(username):
    connection=checkconnection()
    if connection['action_result'] == True:
          sessionIDlogin=Logins()
          if sessionIDlogin['action_result'] == True:
             SessionId=sessionIDlogin['SessionId']
             request = GetUser%(SessionId,username)
             try:
                response = requests.post(CUDB_SERVER_URL, data=request)
             except Exception as e:
               logger.error("Error to send request to CUDB"+str(e))
               Logouts(SessionId)
               return  {'action_result': False, 'action_error_message':"ERROR in CUDB sending request" }
             try:
              StatusMessage=getStatusMessage(response,'GetUser')
              StatusCode=getStatusCode(response,'GetUser')
              if StatusMessage =="Success":
                 service=getGetUserService(response,'GetUser')
                 Profile= {'action_result': True, 'action_error_message': "",'service':service}
                 try:
                  request=GetDSLDetails%(SessionId,username)
                 except:
                   Logouts(SessionId)
                   return {'action_result': False, 'action_error_message': "error set request",'service':service}
                 try:
                   response = requests.post(CUDB_SERVER_URL, data=request)
                   logger.error(convertToPrerryXML(str(response.text)))
                 except Exception as e:
                   logger.error("Error to send request to CUDB"+str(e))
                   Logouts(SessionId)   
                   return {'action_result': False, 'action_error_message': "error to get ADSL profile"}
                 try:
                    StatusMessage=getStatusMessage(response,'GetDSLDetails')
                    StatusCode=getStatusCode(response,'GetDSLDetails')
                    logger.error(StatusMessage)
                    if StatusMessage =="Success":
                       radiusReplyItem=getRadiusReplayItem(response)
                       password=getpassword(response)
                       NPID=getNPID(response)
                       if radiusReplyItem: Profile['radiusReplyItem']=radiusReplyItem
                       if password: Profile['password']=password
                       if NPID: Profile['NPID']=NPID
                       if get_option_pack(SessionId,username):Profile.update(get_option_pack(SessionId,username))
                       Logouts(SessionId)
                       return Profile
                    else:
                      errorCodemap=errorCodeMapping(int(StatusCode))
                      error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                      Logouts(SessionId)
                      return  {'action_result': False, 'action_error_message':error_message , 'service':service } 
                 except Exception as e:
                    logger.error('cant parse cudb response due to'+str(e))
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "error to get ADSL profile"}
              else:
                 if StatusCode == "104102":
                    logcudb(request,response)
                    Logouts(SessionId)
                    return {'action_result': False, 'action_error_message': "User (%s) has no profile on AAA"%username}
                 errorCodemap=errorCodeMapping(int(StatusCode))
                 error_message=StatusMessage+" with error code: "+StatusCode+" due to : "+errorCodemap
                 logcudb(request,response)
                 Logouts(SessionId)
                 return  {'action_result': False, 'action_error_message':error_message }
             except Exception as e:
                logger.error('cant parse cudb response due to'+str(e))
                logcudb(request,response)
                return  {'action_result': False, 'action_error_message':'cant parse response from cudb' }
          else:
             logger.error("can't get sessionID from repsonse due to : "+str(sessionIDlogin['action_error_message']))
             return {'action_result': False, 'action_error_message':"can't get sessionID" }
    else:
      logger.error("connection error with cudb due to"+str(connection['action_error_message']))
      return  {'action_result': False, 'action_error_message': "connection error with cudb" }
