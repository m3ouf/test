##every request sent to EDA need sessionid value,so we use the below request to get sessionid value
login="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:LoginRequest>
         <userId>%s</userId>
         <pwd>%s</pwd>
      </aaa:LoginRequest>
   </soapenv:Body>
</soapenv:Envelope>"""
#every sessionid value you used need to be sent to release it from EDA system
logout="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:LogoutRequest>
         <SessionId>%s</SessionId>
      </aaa:LogoutRequest>
   </soapenv:Body>
</soapenv:Envelope>"""
#to add new user 
AddUser="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:AddUserRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <AddUser>
            <username>%s</username>
            <Service>%s</Service>
         </AddUser>
      </aaa:AddUserRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

##to get user service name
GetUser="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:GetUserRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <GetUser>
            <username>%s</username>
         </GetUser>
      </aaa:GetUserRequest>
   </soapenv:Body>
</soapenv:Envelope>"""


UpdateUser="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:updateUserRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <updateUser>
            <username>%s</username>
            <Service>%s</Service>
         </updateUser>
      </aaa:updateUserRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

#We use the below service for NST and for lab To get all user info
GetDSLDetails="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:GetDSLDetailsRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <GetDSLDetails>
            <username>%s</username>
         </GetDSLDetails>
      </aaa:GetDSLDetailsRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

#we use the below service for lab only to add nasportID
AddNPID="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:AddNPIDRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <AddNPID>
            <username>%s</username>
            <NPID>%s</NPID>
         </AddNPID>
      </aaa:AddNPIDRequest>
   </soapenv:Body>
</soapenv:Envelope>"""
#we use the below service for lab only to reset user password
addpassword="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:ResetUserPasswordRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <ResetUserPassword>
            <username>%s</username>
            <userPassword>%s</userPassword>
            <password>%s</password>
         </ResetUserPassword>
      </aaa:ResetUserPasswordRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

#we use the below for adding optionPack attributes
ADDOptionPack="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:ADDOptionPackRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <ADDOptionPack>
            <username>%s</username>
            <WanIp>%s</WanIp>
            <WanMask>%s</WanMask>
            <route>%s</route>
            <lanip>%s</lanip>
            <zone>%s</zone>
         </ADDOptionPack>
      </aaa:ADDOptionPackRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

ADDOptionPack2="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:ADDOptionPackRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <ADDOptionPack>
            <username>%s</username>
            <WanIp>%s</WanIp>
            <WanMask>%s</WanMask>
            <route>%s</route>
            <lanip>%s</lanip>
            <zone>%s</zone>
            <zone>%s</zone>
         </ADDOptionPack>
      </aaa:ADDOptionPackRequest>
   </soapenv:Body>
</soapenv:Envelope>"""


#we use the below for editing optionPack attributes
EditOptionPack="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:EditOptionPackRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <EditOptionPack>
            <username>%s</username>
            <WanIp>%s</WanIp>
            <WanMask>%s</WanMask>
            <route>%s</route>
            <lanip>%s</lanip>
            <zone>%s</zone>
         </EditOptionPack>
      </aaa:EditOptionPackRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

#we use the below to view OptionPack info
viewOptionPack="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:viewOptionPackRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <viewOptionPack>
            <username>%s</username>
         </viewOptionPack>
      </aaa:viewOptionPackRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

#we use the below to remove optionPack attributes from any user
DeleteOptionPack="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:DeleteOptionPackRequest>
      <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <DeleteOptionPack>
            <username>%s</username>
         </DeleteOptionPack>
      </aaa:DeleteOptionPackRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

#we use the below service to add defalut value for optionPack(tedata-pool) after remove optionPack attributes and in lab
addRadiusReplyItem="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:ADSLModifyRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <ADSLModify>
            <username>%s</username>
            <type>%s</type>
         </ADSLModify>
      </aaa:ADSLModifyRequest>
   </soapenv:Body>
</soapenv:Envelope>"""
#we use the below delete NASPORTID value (for lab)
DeleteNPID="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:DeleteNPIDRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <DeleteNPID>
            <username>%s</username>
         </DeleteNPID>
      </aaa:DeleteNPIDRequest>
   </soapenv:Body>
</soapenv:Envelope>"""
#we use the below to update nasportid (for lab)
UpdateNPID="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aaa="http://com/te/ema/aaa/">
   <soapenv:Header/>
   <soapenv:Body>
      <aaa:UpdateNPIDRequest>
         <RequestHeader>
            <SessionId>%s</SessionId>
         </RequestHeader>
         <UpdateNPID>
            <username>%s</username>
            <NPID>%s</NPID>
         </UpdateNPID>
      </aaa:UpdateNPIDRequest>
   </soapenv:Body>
</soapenv:Envelope>"""
