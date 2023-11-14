def grottext(conf,data,jsonmsg) : 
    ### 
    ### Example to sent (http post) to a webserver. 
    ### 
    ### Updated: 2023-11-13
    ### Version 2.5.0
    ###
    ### see: https://www.w3schools.com/python/ref_requests_post.asp  for a clear explonation how to program a http post request: 
    ###
    import requests
    resultcode = 0
    if conf.verbose : 

        print("\t - " + "Grott extension module entered ") 
        ###
        ### uncomment this print statements if you want to see the information that is available.
        ###

        #print(jsonmsg)
        #print(data)
        #print(dir(conf))
        #print(conf.extvar)

    if "url" in conf.extvar:
        url = conf.extvar["url"]
    else:
        url = f"http://{conf.extvar['ip']}:{conf.extvar['port']}"

    headers = conf.extvar.get("headers", {})
    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
        
    try: 
        r = requests.post(url, headers = headers, data = jsonmsg)

    except Exception as e: 
        
        resultcode = e
        return resultcode 

    #print(r.text)  
    return resultcode