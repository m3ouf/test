import requests
import xmltodict
import urllib2
from urllib2 import Request, urlopen, URLError, HTTPError

###this file responsible for parsing XML responces return from EDA 

def getStatusMessage(response,service):
    try: return xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:'+service+'Response']['ResponseHeader']['MessageStatus']['StatusMessage']
    except: return (None)    

def getStatusCode(response,service):
    try: return xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:'+service+'Response']['ResponseHeader']['MessageStatus']['StatusCode']
    except: return (None)

def getSessionId(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:LoginResponse']['ResponseHeader']['SessionId']
    except: return (None)

def getGetUserService(response,service):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:'+service+'Response']['Result']['Service']
    except: return (None)

def getRadiusReplayItem(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:GetDSLDetailsResponse']['Result']['type']
    except: return (None)

def getpassword(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:GetDSLDetailsResponse']['Result']['password']
    except: return (None)

def getNPID(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:GetDSLDetailsResponse']['Result']['NPID']
    except: return (None)

def getErrorDetails(response,service):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:'+service+'Response']['ResponseHeader']['MessageStatus']['ErrorDetails']['ErrorMessage']
    except: return (None)

def getzone(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:viewOptionPackResponse']['Result']['zone']
    except: return (None)

def getWanIp(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:viewOptionPackResponse']['Result']['WanIp']
    except: return (None)

def getWanMask(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:viewOptionPackResponse']['Result']['WanMask']
    except: return (None)

def getroute(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:viewOptionPackResponse']['Result']['route']
    except: return (None)

def getlanip(response):
    try: return  xmltodict.parse(response.content)['S:Envelope']['S:Body']['ns2:viewOptionPackResponse']['Result']['lanip']
    except: return (None)
