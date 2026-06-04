import urllib.request, json
req = urllib.request.Request('https://huggingface.co/api/spaces/Kaushik-17/CTI_RAG_chatbot/logs')
for line in urllib.request.urlopen(req).readlines():
    if line.startswith(b'data:'):
        try:
            print(json.loads(line.decode('utf-8').replace('data:', ''))['msg'])
        except:
            pass
