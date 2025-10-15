#!/usr/bin/env python3
import os, sys, json, subprocess

TOP = int(sys.argv[1]) if len(sys.argv) > 1 else 30
PODS_DIR = "/var/lib/kubelet/pods"
POD_LOGS_DIR = "/var/log/pods"
CONTAINERS_LOG = "/var/log/containers"
RUNC_ROOT = "/run/containerd/io.containerd.runtime.v2.task/k8s.io"
MOUNTINFO = "/proc/self/mountinfo"
CD_BASE = "/var/lib/containerd"
SNAP_BASE = "/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots"
CONTENT_BASE = "/var/lib/containerd/io.containerd.content.v1.content"

def run(cmd): return subprocess.check_output(cmd, text=True).strip()
def du_bytes(path):
    try: return int(subprocess.check_output(["du","-sb",path], text=True, stderr=subprocess.DEVNULL).split()[0])
    except: 
        try: return int(subprocess.check_output(["du","-s",path], text=True, stderr=subprocess.DEVNULL).split()[0])*1024
        except: return 0
def human(b):
    u=["B","KB","MB","GB","TB","PB"]; i=0; x=float(b)
    while x>=1024 and i<len(u)-1: x/=1024; i+=1
    return f"{x:.1f} {u[i]}"

def upperdir_map():
    m={}
    try:
        with open(MOUNTINFO) as f:
            for line in f:
                p=line.strip().split()
                if len(p)>=10 and p[-3]=="overlay":
                    mp=p[4]; opts=p[-1]
                    for kv in opts.split(","):
                        if kv.startswith("upperdir="): m[mp]=kv.split("=",1)[1]; break
    except: pass
    return m

def image_size_maps():
    by_id, by_name = {}, {}
    try:
        imgs=json.loads(run(["crictl","images","-o","json"])).get("images",[])
        for im in imgs:
            sz=int(im.get("size",0))
            iid=im.get("id","")
            if iid: by_id[iid]=sz
            for n in im.get("repoTags",[])+im.get("repoDigests",[]): by_name[n]=sz
    except: pass
    return by_id, by_name

u_map = upperdir_map()
img_by_id, img_by_name = image_size_maps()
ps=json.loads(run(["crictl","ps","-a","-o","json"]))

pods_name, writable, pod_images = {}, {}, {}
for c in ps.get("containers",[]):
    lbl=c.get("labels",{})
    uid=lbl.get("io.kubernetes.pod.uid")
    if not uid: continue
    pods_name.setdefault(uid, f'{lbl.get("io.kubernetes.pod.namespace","")}/{lbl.get("io.kubernetes.pod.name","")}')
    pod_images.setdefault(uid,set())
    img_ref=c.get("imageRef") or ""
    img=c.get("image"); img_name=img.get("image") if isinstance(img,dict) else img
    if img_ref: pod_images[uid].add(("id",img_ref))
    if img_name: pod_images[uid].add(("name",img_name))
    root=f"{RUNC_ROOT}/{c['id']}/rootfs"
    upper=u_map.get(root,"")
    if upper and os.path.isdir(upper): writable[uid]=writable.get(uid,0)+du_bytes(upper)

emptydir={}
if os.path.isdir(PODS_DIR):
    for uid in os.listdir(PODS_DIR):
        base=os.path.join(PODS_DIR,uid,"volumes","kubernetes.io~empty-dir")
        if os.path.isdir(base): emptydir[uid]=du_bytes(base)

logs={}
if os.path.isdir(CONTAINERS_LOG):
    seen=set()
    for fn in os.listdir(CONTAINERS_LOG):
        if not fn.endswith(".log"): continue
        link=os.path.join(CONTAINERS_LOG,fn)
        try:
            real=os.path.realpath(link)
            parts=real.split(os.sep)
            if "pods" not in parts: continue
            idx=parts.index("pods")
            pod_dir_name=parts[idx+1] if idx+1<len(parts) else ""
            uid=pod_dir_name.split("_")[-1]
            pod_dir=os.path.join("/",*parts[:idx+2])
            if not os.path.isdir(pod_dir): continue
            key=(uid,pod_dir)
            if key in seen: continue
            logs[uid]=logs.get(uid,0)+du_bytes(pod_dir)
            seen.add(key)
        except: pass
elif os.path.isdir(POD_LOGS_DIR):
    for name in os.listdir(POD_LOGS_DIR):
        p=os.path.join(POD_LOGS_DIR,name)
        if not os.path.isdir(p): continue
        uid=name.split("_")[-1]
        if len(uid)<30: continue
        logs[uid]=du_bytes(p)

images={}
for uid,keys in pod_images.items():
    s=0; seen=set()
    for kind,val in keys:
        if val in seen: continue
        sz=img_by_id.get(val) if kind=="id" else img_by_name.get(val)
        if sz is not None: s+=sz; seen.add(val)
    images[uid]=s

rows=[]
for uid,name in pods_name.items():
    w=writable.get(uid,0); e=emptydir.get(uid,0); l=logs.get(uid,0); im=images.get(uid,0)
    t=w+e+l
    if t>0 or im>0: rows.append((t,w,e,l,im,name,uid))
rows.sort(key=lambda r:r[0], reverse=True)

print("=== container ===")
print(f"{'Total':>9}  {'Writable':>9}  {'emptyDir':>9}  {'Logs':>9}  {'Image':>9}  Pod")
for t,w,e,l,im,name,uid in rows[:TOP]:
    print(f"{human(t):>9}  {human(w):>9}  {human(e):>9}  {human(l):>9}  {human(im):>9}  {name} ({uid})")

print("\n=== containerd ===")
def du_h(p):
    try: return subprocess.check_output(["du","-sh",p], text=True, stderr=subprocess.DEVNULL).split()[0]
    except: return "0"
print("containerd:", du_h(CD_BASE))
print("snapshots: ", du_h(SNAP_BASE))
print("content:   ", du_h(CONTENT_BASE))
snaps=[]
if os.path.isdir(SNAP_BASE):
    for sid in os.listdir(SNAP_BASE):
        fs=os.path.join(SNAP_BASE,sid,"fs")
        if os.path.isdir(fs): snaps.append((du_bytes(fs),sid))
snaps.sort(key=lambda x:x[0], reverse=True)
if snaps:
    print("\nTop snapshots:")
    for sz,sid in snaps[:20]:
        print(f"{human(sz):>9}  {sid}")

print("\n=== node disk ===")
try: print(run(["df","-h","/"]))
except: pass
