import subprocess as sb_p
import tkinter as tk
import register_with_eye as regV
import admFunc as adFunc
from tkinter import *
from register_with_eye import *
from admFunc import *
from tkinter import messagebox


def AdminHome(root,frame1,frame3):
    root.title("Admin")
    for widget in frame1.winfo_children():
        widget.destroy()

    Button(frame3, text="Admin", command = lambda: AdminHome(root, frame1, frame3)).grid(row = 1, column = 0)
    frame3.pack(side=TOP)

    Label(frame1, text="Admin", font=('Helvetica', 25, 'bold')).grid(row = 0, column = 1)
    Label(frame1, text="").grid(row = 1,column = 0)

    # Admin Login
    runServer = Button(frame1, text="Run Server", width=15, command = lambda: sb_p.call('start python Server.py', shell=True))

    # Voter Login
    registerVoter = Button(frame1, text="Register Voter", width=15, command = lambda: regV.Register(root, frame1))

    # Show Votes
    showVotes = Button(frame1, text="Show Votes", width=15, command = lambda: adFunc.showVotes(root, frame1))

    # Tally & Reset Votes (new)
    tallyReset = Button(frame1, text="Tally & Reset Votes", width=15, command = lambda: tally_and_reset(root, frame1))

    # Reset Data
    reset = Button(frame1, text="Reset All", width=15, command = lambda: adFunc.resetAll(root, frame1))

    Label(frame1, text="").grid(row = 2,column = 0)
    Label(frame1, text="").grid(row = 4,column = 0)
    Label(frame1, text="").grid(row = 6,column = 0)
    Label(frame1, text="").grid(row = 8,column = 0)
    runServer.grid(row = 3, column = 1, columnspan = 2)
    registerVoter.grid(row = 5, column = 1, columnspan = 2)
    showVotes.grid(row = 7, column = 1, columnspan = 2)
    tallyReset.grid(row = 9, column = 1, columnspan = 2)
    # reset.grid(row = 9, column = 1, columnspan = 2)

    frame1.pack()
    root.mainloop()


def tally_and_reset(root, frame1):
    """Tally votes by calling adFunc.showVotes then optionally reset all votes.

    This function will:
      1. Call adFunc.showVotes(root, frame1) to display/tally current votes (keeps existing behavior).
      2. Ask the admin to confirm whether to reset all votes.
      3. If confirmed, call adFunc.resetAll(root, frame1) to clear the votes and show a confirmation message.

    Note: This implementation assumes adFunc.showVotes and adFunc.resetAll exist and perform the
    expected operations. If your tallying logic requires reading files or databases directly, move
    that logic into admFunc.tallyVotes and call it here instead.
    """
    try:
        # Step 1: show/tally votes (reuse existing UI function)
        adFunc.showVotes(root, frame1)

        # Step 2: ask for confirmation before resetting
        proceed = messagebox.askyesno("Confirm Reset", "Do you want to reset all votes after tallying?")
        if not proceed:
            messagebox.showinfo("Tally Complete", "Votes have been tallied. No reset was performed.")
            return

        # Step 3: perform reset
        adFunc.resetAll(root, frame1)
        messagebox.showinfo("Reset Complete", "All votes have been reset. Voting is now null.")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while tallying/resetting votes:\n{e}")


def log_admin(root,frame1,admin_ID,password):

    if(admin_ID=="Admin" and password=="admin"):
        frame3 = root.winfo_children()[1]
        AdminHome(root, frame1, frame3)
    else:
        msg = Message(frame1, text="Either ID or Password is Incorrect", width=500)
        msg.grid(row = 6, column = 0, columnspan = 5)


def AdmLogin(root,frame1):

    root.title("Admin Login")
    for widget in frame1.winfo_children():
        widget.destroy()

    Label(frame1, text="Admin Login", font=('Helvetica', 18, 'bold')).grid(row = 0, column = 2, rowspan=1)
    Label(frame1, text="").grid(row = 1,column = 0)
    Label(frame1, text="Admin ID:      ", anchor="e", justify=LEFT).grid(row = 2,column = 0)
    Label(frame1, text="Password:       ", anchor="e", justify=LEFT).grid(row = 3,column = 0)

    admin_ID = tk.StringVar()
    password = tk.StringVar()

    e1 = Entry(frame1, textvariable = admin_ID)
    e1.grid(row = 2,column = 2)
    e2 = Entry(frame1, textvariable = password, show = '*')
    e2.grid(row = 3,column = 2)

    sub = Button(frame1, text="Login", width=10, command = lambda: log_admin(root, frame1, admin_ID.get(), password.get()))
    Label(frame1, text="").grid(row = 4,column = 0)
    sub.grid(row = 5, column = 3, columnspan = 2)

    frame1.pack()
    root.mainloop()


# if __name__ == "__main__":
#         root = Tk()
#         root.geometry('500x500')
#         frame1 = Frame(root)
#         frame3 = Frame(root)
#         AdminHome(root,frame1,frame3)
