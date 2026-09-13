"""Incrementally project OpenAI history to task + latest observation.

History is consumed once, but old screenshots are never retained together.
Permanent input errors become a terminal agent result, not retried HTTP 500s.
"""
import hashlib
import ijson

MAX_WIRE_BYTES=256_000_000
MAX_MESSAGE_CHARS=28_000_000

class SizedReader:
    def __init__(self,stream,length):
        self.stream=stream;self.remaining=length;self.digest=hashlib.sha256()
    def read(self,size=-1):
        n=self.remaining if size<0 else min(size,self.remaining)
        data=self.stream.read(n) if n else b''
        self.remaining-=len(data);self.digest.update(data)
        return data

def project_messages(stream,length):
    if not 0<length<=MAX_WIRE_BYTES:raise ValueError('INVALID_WIRE_LENGTH')
    reader=SizedReader(stream,length)
    systems=[];latest=None;count=0;retained=0
    try:
        for msg in ijson.items(reader,'messages.item'):
            count+=1
            if count>200 or not isinstance(msg,dict):raise ValueError('INVALID_MESSAGE_SEQUENCE')
            content=msg.get('content','')
            if isinstance(content,str):size=len(content)
            elif isinstance(content,list):
                size=sum(len(str(item.get('text','')))+len(str(item.get('image_url',{}))) for item in content if isinstance(item,dict))
            else:raise ValueError('INVALID_MESSAGE_CONTENT')
            if size>MAX_MESSAGE_CHARS:raise ValueError('SINGLE_MESSAGE_TOO_LARGE')
            if msg.get('role')=='system':
                if isinstance(content,str): system_text=content
                elif isinstance(content,list):
                    texts=[]
                    for item in content:
                        if not isinstance(item,dict) or item.get('type')!='text' or not isinstance(item.get('text',''),str):raise ValueError('INVALID_SYSTEM_MESSAGE')
                        texts.append(item.get('text',''))
                    if not texts:raise ValueError('INVALID_SYSTEM_MESSAGE')
                    system_text='\n'.join(texts)
                else:raise ValueError('INVALID_SYSTEM_MESSAGE')
                if len(system_text)>100_000 or len(systems)>=4:raise ValueError('INVALID_SYSTEM_MESSAGE')
                systems.append({**msg,'content':system_text})
            elif msg.get('role')=='user':latest=msg;retained=size
    except ijson.JSONError as exc:
        raise ValueError('INVALID_REQUEST_JSON') from exc
    if reader.remaining or latest is None:raise ValueError('INCOMPLETE_REQUEST')
    return systems+[latest],{'wire_bytes':length,'messages_received':count,'messages_retained':len(systems)+1,
                            'latest_content_chars':retained,'request_sha256':reader.digest.hexdigest()}
