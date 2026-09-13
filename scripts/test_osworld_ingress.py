import io,json,unittest,tracemalloc,time
from osworld_ingress import project_messages

class IngressTests(unittest.TestCase):
    def test_run38_history_above_32mb_is_projected(self):
        history=[{'role':'system','content':'task'}]+[{'role':'user','content':[{'type':'text','text':str(i)},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+'A'*1_700_000}}]} for i in range(20)]
        raw=json.dumps({'messages':history}).encode();self.assertGreater(len(raw),32_000_000)
        tracemalloc.start();start=time.perf_counter()
        messages,metrics=project_messages(io.BytesIO(raw),len(raw))
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        self.assertEqual(len(messages),2);self.assertEqual(messages[-1]['content'][0]['text'],'19')
        self.assertLess(peak,15_000_000)
        print(json.dumps({'ingress_replay_bytes':len(raw),'retained_messages':len(messages),'peak_parser_bytes':peak,'seconds':round(time.perf_counter()-start,3)}))
    def test_corrupted_payload_rejected(self):
        for raw in (b'{bad',b'{"messages":[]}',b'{"messages":[null]}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):project_messages(io.BytesIO(raw),len(raw))
    def test_unicode_and_unrelated_fields(self):
        raw=json.dumps({'model':'x','messages':[{'role':'system','content':'task'},{'role':'assistant','content':'old'},{'role':'user','content':'雪'}],'temperature':0}).encode()
        messages,_=project_messages(io.BytesIO(raw),len(raw));self.assertEqual(messages[-1]['content'],'雪')
    def test_declared_length_bounds_and_truncation(self):
        for length in (-1,0,300_000_000):
            with self.assertRaises(ValueError):project_messages(io.BytesIO(b'{}'),length)
        raw=b'{"messages":[{"role":"user","content":"x"}]}'
        with self.assertRaises(ValueError):project_messages(io.BytesIO(raw),len(raw)+10)

    def test_official_osworld_system_text_parts_are_normalized(self):
        payload={'messages':[{'role':'system','content':[{'type':'text','text':'policy\nYou are asked to complete the following task: demo'}]},{'role':'user','content':[{'type':'text','text':'obs'}]}]}
        raw=json.dumps(payload).encode();messages,_=project_messages(io.BytesIO(raw),len(raw))
        self.assertIsInstance(messages[0]['content'],str);self.assertIn('following task: demo',messages[0]['content'])
    def test_system_multimodal_content_is_rejected(self):
        payload={'messages':[{'role':'system','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,AA'}}]},{'role':'user','content':'obs'}]}
        raw=json.dumps(payload).encode()
        with self.assertRaisesRegex(ValueError,'INVALID_SYSTEM_MESSAGE'):project_messages(io.BytesIO(raw),len(raw))

if __name__=='__main__':unittest.main()
