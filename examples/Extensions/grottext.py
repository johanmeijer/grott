def grottext(conf,data,jsonmsg) : 
    ### 
    ### Example to sent (http put) to a webserver. 
    ### 
    ### Updated: 2021-01-09
    ### Version 2.4.0
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

    try: 
        r = requests.post(url, json = jsonmsg)

    except Exception as e: 
        
        resultcode = e
        return resultcode 

    #print(r.text)  
    return resultcode

    