from pathlib import Path

source = Path(__file__).resolve().parents[1] / 'catalogue.py'
s = source.read_text(encoding='utf-8')
start = s.index('    def check_updates(self,silent=False):')
end = s.index('    def task(self,enable):', start)
replacement = '''    def check_updates(self,silent=False):
        repo=self.store.setting('github_repo').strip().strip('/') or 'VeyrStudio/DesktopAppUpdates'
        if repo.count('/')!=1:
            if not silent:messagebox.showerror('Updates','Invalid GitHub repository setting.')
            return
        def worker():
            try:
                url=f'https://raw.githubusercontent.com/{repo}/main/catalogue/latest.json'
                req=urllib.request.Request(url,headers={'User-Agent':'Catalogue-Updater/2.0'})
                with urllib.request.urlopen(req,timeout=15) as response:
                    manifest=json.load(response)
                new=str(manifest['version'])
                def nums(version):
                    return tuple(int(x) for x in version.strip().lstrip('vV').split('.')[:3])
                newer=nums(new)>nums(APP_VERSION)
                installer_url=manifest['url']
                checksum=manifest['sha256'].lower()
                if not installer_url.startswith('https://github.com/'+repo+'/releases/download/catalogue-') or not installer_url.endswith('.exe'):
                    raise ValueError('The update feed does not contain a valid Catalogue installer URL.')
                if len(checksum)!=64 or any(c not in '0123456789abcdef' for c in checksum):
                    raise ValueError('The update feed has an invalid checksum.')
                def show():
                    if newer:
                        if messagebox.askyesno('Catalogue Update',f'Catalogue {new} is available. Download and run its Windows installer now?\\n\\nYour saved subscriptions and pictures will be retained.'):
                            self.download_release(installer_url,checksum,new)
                    elif not silent:
                        messagebox.showinfo('Updates',f'Catalogue is up to date (v{APP_VERSION}).')
                self.after(0,show)
            except Exception as exc:
                error=str(exc)
                if not silent:self.after(0,lambda:messagebox.showerror('Update check failed',error))
        threading.Thread(target=worker,daemon=True).start()
    def download_release(self,url,checksum,version):
        def worker():
            try:
                import hashlib
                import subprocess
                target=DATA_DIR/'updates'
                target.mkdir(parents=True,exist_ok=True)
                dst=target/('Catalogue-Setup-'+version+'.exe')
                request=urllib.request.Request(url,headers={'User-Agent':'Catalogue-Updater/2.0'})
                digest=hashlib.sha256()
                with urllib.request.urlopen(request,timeout=60) as response, open(dst,'wb') as output:
                    while True:
                        block=response.read(1024*1024)
                        if not block:break
                        output.write(block)
                        digest.update(block)
                if digest.hexdigest().lower()!=checksum:
                    dst.unlink(missing_ok=True)
                    raise ValueError('Update verification failed: downloaded installer checksum does not match GitHub.')
                def install():
                    if sys.platform!='win32':
                        messagebox.showinfo('Installer downloaded',str(dst))
                        return
                    try:
                        subprocess.Popen([str(dst)],close_fds=True)
                        self.destroy()
                    except Exception as exc:
                        messagebox.showerror('Installer failed to start',str(exc))
                self.after(0,install)
            except Exception as exc:
                error=str(exc)
                self.after(0,lambda:messagebox.showerror('Update download failed',error))
        threading.Thread(target=worker,daemon=True).start()
'''
s=s[:start]+replacement+s[end:]
# Ensure all fresh installations already have a default repository, including upgrades of old installations.
s=s.replace("self.set_default('notify_trial','1');self.set_default('notify_price','1');self.set_default('github_repo','')",
            "self.set_default('notify_trial','1');self.set_default('notify_price','1');self.set_default('github_repo','VeyrStudio/DesktopAppUpdates')")
s=s.replace("        if self.store.setting('github_repo'): self.check_updates(silent=True)", "        self.check_updates(silent=True)")
source.write_text(s,encoding='utf-8')
print('Catalogue update installer workflow patched successfully')
