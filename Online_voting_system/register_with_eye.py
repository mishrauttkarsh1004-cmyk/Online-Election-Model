# register_with_eye.py (camera index selection; email option removed)
import tkinter as tk
from tkinter import ttk, Label, Entry, Button, Frame, Message, LEFT, Spinbox
import numpy as np
import cv2
import dframe as df    # updated dframe.py (must provide save_eye_template, list_voters, load_eye_template, taking_data_voter)
import re

# ORB + capture logic; descriptors will be saved via df.save_eye_template()
ORB_N_FEATURES = 500
MATCH_THRESHOLD = 10

def capture_eye_image(camera_index=0, window_name="Capture Eye - press 'c' to capture, 'q' to cancel"):
    """Capture ROI from the specified camera_index and return grayscale ROI or None."""
    try:
        cam_index = int(camera_index)
    except Exception:
        cam_index = 0

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"Camera {cam_index} not available.")
        return None
    captured = None
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (int(w*0.25), int(h*0.2)), (int(w*0.75), int(h*0.8)), (255,255,255), 2)
        cv2.putText(frame, f"Cam {cam_index} - Place eye in box. Press 'c' to capture, 'q' to cancel.", (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        cv2.imshow(window_name, frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('c'):
            roi = frame[int(h*0.2):int(h*0.8), int(w*0.25):int(w*0.75)]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            captured = gray
            break
        elif k == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    return captured

def make_descriptors(img_gray):
    if img_gray is None:
        return None
    orb = cv2.ORB_create(ORB_N_FEATURES)
    kps, des = orb.detectAndCompute(img_gray, None)
    return des

from cv2 import BFMatcher

def match_templates(des1, des2):
    if des1 is None or des2 is None:
        return 0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    try:
        matches = bf.knnMatch(des1, des2, k=2)
    except cv2.error:
        return 0
    good = []
    for m_n in matches:
        if len(m_n) < 2:
            continue
        m, n = m_n
        if m.distance < 0.75 * n.distance:
            good.append(m)
    return len(good)


def reg_server(root, frame1, name, gender, zone, city, passw, age, descriptors, raw_image):
    # Basic checks
    if passw.strip() == "":
        msg = Message(frame1, text="Error: Missing password", width=500)
        msg.grid(row = 13, column = 0, columnspan = 5)
        return -1
    # password complexity check
    if not re.search(r'[A-Z]', passw) or not re.search(r'[a-z]', passw) or not re.search(r'\d', passw):
        msg = Message(frame1, text="Password must contain at least one uppercase letter, one lowercase letter and one number.", width=500)
        msg.grid(row = 13, column = 0, columnspan = 5)
        return -1

    # descriptor must exist
    if descriptors is None:
        msg = Message(frame1, text="No eye template captured. Capture eye before registering.", width=500)
        msg.grid(row = 13, column = 0, columnspan = 5)
        return -1

    # check for duplicates: same password AND matching eye template
    try:
        voters_df = df.list_voters()
        candidates = voters_df[voters_df['passw'].astype(str) == str(passw)]
        for _, r in candidates.iterrows():
            vid = r['voter_id']
            stored = df.load_eye_template(vid)
            if stored is None:
                continue
            score = match_templates(descriptors, stored)
            if score >= MATCH_THRESHOLD:
                msg = Message(frame1, text=f"A voter with the same password and eye template already exists (Voter ID: {vid}).", width=500)
                msg.grid(row = 13, column = 0, columnspan = 5)
                return -1
    except Exception as e:
        print("Duplicate check failed (continuing):", e)

    # create voter entry (supports age)
    try:
        vid = df.taking_data_voter(name, gender, zone, city, passw, age)
    except TypeError:
        # fallback if signature differs
        vid = df.taking_data_voter(name, gender, zone, city, passw)

    if vid is None:
        msg = Message(frame1, text="Registration failed (no voter id assigned)", width=500)
        msg.grid(row = 13, column = 0, columnspan = 5)
        return -1

    # save encrypted template via dframe helper (handles encryption/key)
    ok = df.save_eye_template(vid, descriptors, raw_image=raw_image)

    if not ok:
        # still show the id, but inform admin about template save failure
        for widget in frame1.winfo_children():
            widget.destroy()
        txt = f"Registered Voter with VOTER I.D. = {vid}\n\nBut failed to save eye template."
        Label(frame1, text=txt, font=('Helvetica', 14, 'bold')).grid(row = 2, column = 1, columnspan=2)
        return vid

    # success
    for widget in frame1.winfo_children():
        widget.destroy()
    txt = "Registered Voter with\n\n VOTER I.D. = " + str(vid)
    Label(frame1, text=txt, font=('Helvetica', 18, 'bold')).grid(row = 2, column = 1, columnspan=2)
    return vid


def Register(root, frame1):
    root.title("Register Voter (with Eye Capture)")
    for widget in frame1.winfo_children():
        widget.destroy()

    Label(frame1, text="Register Voter", font=('Helvetica', 18, 'bold')).grid(row = 0, column = 2, rowspan=1)
    Label(frame1, text="").grid(row = 1,column = 0)
    Label(frame1, text="Name:").grid(row = 3, column = 0)
    Label(frame1, text="Gender:").grid(row = 4, column = 0)
    Label(frame1, text="Age:").grid(row = 5, column = 0)
    Label(frame1, text="Zone:").grid(row = 6, column = 0)
    Label(frame1, text="City:").grid(row = 7, column = 0)
    Label(frame1, text="Password:").grid(row = 9, column = 0)
    Label(frame1, text="Eye Capture:").grid(row = 10, column = 0)
    Label(frame1, text="Camera Index:").grid(row = 2, column = 0)

    name = tk.StringVar()
    gender = tk.StringVar()
    zone = tk.StringVar()
    city = tk.StringVar()
    password = tk.StringVar()
    age_var = tk.IntVar(value=18)
    camera_var = tk.IntVar(value=0)

    Entry(frame1, textvariable = name).grid(row = 3, column = 2)
    Entry(frame1, textvariable = zone).grid(row = 6, column = 2)
    Entry(frame1, textvariable = city).grid(row = 7, column = 2)
    Entry(frame1, textvariable = password, show='*').grid(row = 9, column = 2)
    Entry(frame1, textvariable = age_var).grid(row = 5, column = 2)

    e4 = ttk.Combobox(frame1, textvariable = gender, width=17)
    e4['values'] = ("Male","Female","Transgender")
    e4.grid(row = 4, column = 2)
    try:
        e4.current()
    except Exception:
        pass

    # camera spinbox (0..10)
    Spinbox(frame1, from_=0, to=10, textvariable=camera_var, width=5).grid(row=2, column=2, sticky='w')

    captured = {"img": None, "des": None}

    def on_capture():
        cam_idx = camera_var.get()
        img = capture_eye_image(cam_idx)
        if img is None:
            Message(frame1, text=f"Capture cancelled or camera {cam_idx} not available.", width=500).grid(row = 12, column = 0, columnspan = 5)
            return
        des = make_descriptors(img)
        if des is None:
            Message(frame1, text="No keypoints found. Try recapturing with better lighting.", width=500).grid(row = 12, column = 0, columnspan = 5)
            return
        captured['img'] = img
        captured['des'] = des
        Message(frame1, text=f"Eye captured successfully from camera {cam_idx}. Now press Register.", width=500).grid(row = 12, column = 0, columnspan = 5)

    reg_btn = Button(frame1, text="Capture Eye", command=on_capture, width=12)
    reg_btn.grid(row = 10, column = 2)

    reg = Button(frame1, text="Register", command = lambda: reg_server(
        root, frame1,
        name.get(), gender.get(), zone.get(), city.get(),
        password.get(), age_var.get(),
        captured['des'], captured['img']
    ), width=10)
    Label(frame1, text="").grid(row = 11,column = 0)
    reg.grid(row = 11, column = 3, columnspan = 2)

    frame1.pack()
    root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry('700x600')
    frame1 = Frame(root)
    Register(root, frame1)
