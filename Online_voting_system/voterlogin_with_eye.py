# voterlogin_with_eye.py (camera index selection)
# Changes:
# - Camera index selection (Spinbox) and capture uses chosen webcam index
# - All capture calls pass the chosen camera index

import tkinter as tk
from tkinter import Label, Entry, Button, Frame, LEFT, messagebox, Spinbox
import socket
import cv2
import numpy as np
import dframe as df   # must provide verify(), load_eye_template(), isEligible(), get_voter_row()
from VotingPage import votingPg   # existing voting page callback

ORB_N_FEATURES = 500
MATCH_THRESHOLD = 10  # ~8-15 depending on camera/lighting

def establish_connection():
    try:
        host = socket.gethostname()
        port = 4001
        client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        client_socket.connect((host, port))
        message = client_socket.recv(1024)
        if message.decode() == "Connection Established":
            return client_socket
        else:
            return 'Failed'
    except Exception as e:
        print("Connection Failed:", e)
        return 'Failed'

def failed_return(root,frame1,client_socket,message):
    for widget in frame1.winfo_children():
        widget.destroy()
    message = message + "... \nTry again..."
    Label(frame1, text=message, font=('Helvetica', 12, 'bold')).grid(row = 1, column = 1)
    try:
        client_socket.close()
    except:
        pass

def capture_eye_image(camera_index=0, window_name="Verify Eye - press 'c' to capture, 'q' to cancel"):
    """Capture ROI from specified camera index and return grayscale ROI or None."""
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

def perform_eye_verification_for_id(voter_id, frame1, camera_index=0, threshold=MATCH_THRESHOLD):
    """
    Load stored descriptors for voter_id and compare with live capture using chosen camera_index.
    Returns tuple (ok: bool, score: float)
    """
    stored = df.load_eye_template(voter_id)
    if stored is None:
        Label(frame1, text="No eye template found for this voter. Use normal login.", font=('Helvetica', 12, 'bold')).grid(row=6, column=1)
        return False, 0.0
    live = capture_eye_image(camera_index)
    if live is None:
        Label(frame1, text=f"Live capture failed or cancelled (camera {camera_index}).", font=('Helvetica', 12, 'bold')).grid(row=6, column=1)
        return False, 0.0
    live_des = make_descriptors(live)
    if live_des is None:
        Label(frame1, text="No descriptors in live capture. Try again with better lighting.", font=('Helvetica', 12, 'bold')).grid(row=6, column=1)
        return False, 0.0
    m1 = match_templates(live_des, stored)
    m2 = match_templates(stored, live_des)
    avg = (m1 + m2) / 2.0
    print("Match count avg:", avg)
    return (avg >= threshold), avg

def log_server(root, frame1, client_socket, voter_ID, password, camera_index=0):
    """
    Original server auth flow: server authenticates, then client performs eye verification using camera_index.
    After a successful eye check, show confirmation dialog with voter name before proceeding.
    """
    if not (voter_ID and password):
        voter_ID = "0"
        password = "x"
    message = voter_ID + " " + password
    try:
        client_socket.send(message.encode())
    except Exception as e:
        failed_return(root, frame1, client_socket, "Connection lost")
        return
    message = client_socket.recv(1024)
    message = message.decode()

    if message == "Authenticate":
        ok, score = perform_eye_verification_for_id(voter_ID, frame1, camera_index=camera_index)
        if ok:
            # show visual confirmation with voter name
            row = df.get_voter_row(voter_ID)
            name = row.get('name', '') if row else ''
            confirm = messagebox.askyesno("Confirm Identity", f"Matched Voter:\n\nID: {voter_ID}\nName: {name}\n\nProceed to voting?")
            if confirm:
                votingPg(root, frame1, client_socket)
            else:
                # user cancelled
                failed_return(root, frame1, client_socket, "User cancelled after identity confirmation")
        else:
            failed_return(root, frame1, client_socket, "Eye verification failed")
    elif message == "VoteCasted":
        failed_return(root, frame1, client_socket, "Vote has Already been Cast")
    elif message == "InvalidVoter":
        failed_return(root, frame1, client_socket, "Invalid Voter")
    else:
        failed_return(root, frame1, client_socket, "Server Error")

def eye_verify_and_login(root, frame1, voter_ID, password, camera_index=0):
    """
    Combined flow:
    1) Locally check credentials (df.verify)
    2) If OK, perform local eye verification against stored template for voter_ID using camera_index
    3) If user confirms identity, establish connection to server and send credentials;
       if server returns Authenticate -> votingPg
    """
    # local credential check first (fast)
    if not (voter_ID and password):
        Label(frame1, text="Enter Voter ID and Password before Eye Verify + Login.", font=('Helvetica', 12, 'bold')).grid(row=6, column=1)
        return

    if not df.verify(voter_ID, password):
        Label(frame1, text="ID/Password do not match local records. Check and try.", font=('Helvetica', 12, 'bold')).grid(row=6, column=1)
        return

    # check eligibility before heavy steps (optional)
    if not df.isEligible(voter_ID):
        Label(frame1, text="Voter already voted or not eligible.", font=('Helvetica', 12, 'bold')).grid(row=6, column=1)
        return

    # perform eye verification (uses stored template)
    Label(frame1, text=f"Starting eye capture for verification (camera {camera_index})...", font=('Helvetica', 12, 'bold')).grid(row=6, column=1)
    root.update()
    ok, score = perform_eye_verification_for_id(voter_ID, frame1, camera_index=camera_index)
    if not ok:
        Label(frame1, text="Eye verification failed. Try again or use normal login.", font=('Helvetica', 12, 'bold')).grid(row=7, column=1)
        return

    # eye verified locally — show name confirmation before contacting server
    row = df.get_voter_row(voter_ID)
    name = row.get('name', '') if row else ''
    confirm = messagebox.askyesno("Confirm Identity", f"Matched Voter:\n\nID: {voter_ID}\nName: {name}\n\nProceed to authenticate with server and vote?")
    if not confirm:
        Label(frame1, text="User cancelled after identity confirmation.", font=('Helvetica', 12, 'bold')).grid(row=7, column=1)
        return

    # proceed to server auth
    client_socket = establish_connection()
    if client_socket == 'Failed':
        failed_return(root, frame1, client_socket, "Connection failed")
        return

    # send credentials to server and handle response (same as log_server)
    try:
        client_socket.send((voter_ID + " " + password).encode())
    except Exception as e:
        failed_return(root, frame1, client_socket, "Connection lost")
        return

    try:
        message = client_socket.recv(1024).decode()
    except Exception as e:
        failed_return(root, frame1, client_socket, "No response from server")
        return

    if message == "Authenticate":
        votingPg(root, frame1, client_socket)
    elif message == "VoteCasted":
        failed_return(root, frame1, client_socket, "Vote has Already been Cast")
    elif message == "InvalidVoter":
        failed_return(root, frame1, client_socket, "Invalid Voter")
    else:
        failed_return(root, frame1, client_socket, "Server Error")

def voterLogin(root,frame1):
    client_socket = establish_connection()
    # keep the UI even if connection failed; functions will handle it
    if client_socket == 'Failed':
        print("Warning: server connection failed at start. Login buttons will still attempt local flows.")

    root.title("Voter Login (with Eye Verification)")
    for widget in frame1.winfo_children():
        widget.destroy()

    Label(frame1, text="Voter Login", font=('Helvetica', 18, 'bold')).grid(row = 0, column = 2, rowspan=1)
    Label(frame1, text="").grid(row = 1,column = 0)
    Label(frame1, text="Voter ID:      ", anchor="e", justify=LEFT).grid(row = 2,column = 0)
    Label(frame1, text="Password:   ", anchor="e", justify=LEFT).grid(row = 3,column = 0)
    Label(frame1, text="Camera Index:").grid(row = 4, column = 0)

    voter_ID = tk.StringVar()
    password = tk.StringVar()
    camera_var = tk.IntVar(value=0)

    e1 = Entry(frame1, textvariable = voter_ID)
    e1.grid(row = 2,column = 2)
    e3 = Entry(frame1, textvariable = password, show='*')
    e3.grid(row = 3,column = 2)

    # camera selection spinbox
    Spinbox(frame1, from_=0, to=10, textvariable=camera_var, width=5).grid(row=4, column=2, sticky='w')

    # Original Login (server auth then eye verification)
    sub = Button(frame1, text="Login", width=12, command = lambda: log_server(root, frame1, client_socket, voter_ID.get(), password.get(), camera_index=camera_var.get()))
    sub.grid(row = 6, column = 2, padx=5, pady=8)

    # New combined Eye Verify + Login (ID+pass + eye)
    eye_login_btn = Button(frame1, text="Eye Verify + Login", width=16, command = lambda: eye_verify_and_login(root, frame1, voter_ID.get(), password.get(), camera_index=camera_var.get()))
    eye_login_btn.grid(row = 6, column = 3, padx=5, pady=8)

    Label(frame1, text="").grid(row = 5,column = 0)

    frame1.pack()
    root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry('600x450')
    frame1 = Frame(root)
    voterLogin(root, frame1)
