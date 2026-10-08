import hashlib, http.client, json, tempfile, threading, unittest
from pathlib import Path
import app

class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old_dest=app.DEST
        app.DEST=Path(self.tmp.name)
        self.server=app.ThreadingHTTPServer(("127.0.0.1",0),app.Receiver)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        app.DEST=self.old_dest
        self.tmp.cleanup()
    def request(self,method,path,body=None):
        con=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=10)
        con.request(method,path,body=body,headers={"Content-Type":"application/octet-stream"})
        resp=con.getresponse()
        result=(resp.status,resp.read().decode())
        con.close()
        return result
    def test_website_requires_secret_and_serves_upload(self):
        self.assertEqual(self.request("GET","/")[0],403)
        code,html=self.request("GET","/?key="+app.KEY)
        self.assertEqual(code,200)
        self.assertIn("Send to computer",html)
        self.assertIn('type="file"',html)
    def test_upload_and_duplicate(self):
        payload=b"PhotoBridge end-to-end upload test bytes"
        path="/upload?key="+app.KEY+"&name=test.jpg"
        self.assertEqual(self.request("POST",path,payload)[0],200)
        self.assertEqual((app.DEST/"test.jpg").read_bytes(),payload)
        self.assertEqual(self.request("POST",path,payload),(200,"Duplicate"))
        self.assertEqual(len(list(app.DEST.glob("*.jpg"))),1)
        index=json.loads((app.DEST/".photobridge-index.json").read_text())
        self.assertEqual(index[hashlib.sha256(payload).hexdigest()],"test.jpg")
    def test_bad_secret_rejected(self):
        self.assertEqual(self.request("POST","/upload?key=wrong&name=test.jpg",b"abc")[0],403)
        self.assertEqual(list(app.DEST.iterdir()),[])

if __name__=="__main__":
    unittest.main()
