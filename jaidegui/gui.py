#!/usr/bin/env python
""" The GUI wrapper for the jaide CLI utility.

This python file is used to spawn the GUI that wraps around jaide,
providing ease of use for those that don't want to use the command line.

This Class is part of the jaidegui project.
It is free software for use in manipulating junos devices. More information
can be found at the github page found here:

    https://github.com/NetworkAutomation/jaidegui


For more information on the underlying jaide utility, visit:

    https://github.com/NetworkAutomation/jaide
"""
# Standard Imports
import Queue
# In terms of JGUI, we use multiprocessing to enable freeze_support.
import multiprocessing as mp
import webbrowser as webb
import re
import os
import sys
import base64
import time
# Tkinter related imports.
import Tkinter as tk  # Tkinter is the underlying gui framework.
import tkFileDialog
import tkMessageBox
import ttk  # Used for separators between frames of the UI.
# Intra-jaidegui imports
from jgui_widgets import JaideEntry, JaideCheckbox
from jgui_widgets import AutoScrollbar, JaideRadiobutton
from worker_thread import WorkerThread
from module_locator import module_path
# The rest are Non-standard imports
from jaide import wrap
from jaide.utils import clean_lines
# Pmw is the extended menuwidget option giving us the ability
# to call a function when a option is chosen from the menu.
from Pmw import OptionMenu as OM


# TODO: make Script output non-editable, but still selectable for copying.  - Doesn't seem feasible without completely re-writing textArea widget.
# TODO: add headers to the sections of the GUI / add coloring or styling.  - Attempted, couldn't get menuoption to work, or checkboxes on mac.
# TODO: make entry fields fill their given space on the x-axis to give more space for filepaths?
# TODO: check and make sure writing to multiple files works on windows and compiled versions.
class JaideGUI(tk.Tk):

    """ The GUI wrapper for the jaide CLI tool.

    The JaideGUI class inherits the properties of the Tkinter.Tk class. This
    class encapsulates the entire methodology for creating the visual
    representation seen by the user. Some functionality is enhanced with the
    use of other classes that are imported and used, including WorkerThread
    (for running the jaide CLI tool and handling output gathering) and
    AutoScrollbar (for putting scrollbars on the output_area text entry widget)
    """

    def __init__(self, parent):
        """ Purpose: Initializes and shows the GUI. """
        tk.Tk.__init__(self, parent)
        self.parent = parent

        self.grid()
        self.wm_title("Jaide GUI")
        self.focus_force()
        self.defaults_file = os.path.join(module_path(), "defaults.ini")

        # ## Argument and option lists for user input
        # arguments that require extra input
        self.yes_options = ["Operational Command(s)", "Set Command(s)",
                            "Shell Command(s)", "SCP Files", "Diff Config",
                            "Show | Compare"]
        # arguments that don't require extra input
        self.no_options = ["Interface Errors", "Health Check", "Device Info"]
        # List of argument options
        self.options_list = ["Diff Config", "Operational Command(s)",
                             "SCP Files", "Set Command(s)", "Shell Command(s)",
                             "Show | Compare", "------", "Device Info",
                             "Health Check", "Interface Errors"]

        # Maps optionMenu choice to jaide_cli function.
        self.option_conversion = {
            "Diff Config": wrap.diff_config,
            "Device Info": wrap.device_info,
            "Health Check": wrap.health_check,
            "Interface Errors": wrap.interface_errors,
            "Operational Command(s)": wrap.command,
            "SCP Files": wrap.push,
            "Set Command(s)": wrap.commit,
            "Shell Command(s)": wrap.shell,
            "Show | Compare": wrap.compare
        }
        # Maps optionMenu choice to help text.
        self.help_conversion = {
            "Show | Compare": "Quick Help: Run a 'show | compare' in Junos against a given list of set commands. " +
                              "The command(s) can be a single command, a comma separated list, or a filepath of many commands.",
            "Device Info": "Quick Help: Device Info pulls some baseline information from the device(s), including " +
                           "Hostname, Model, Junos Version, and Chassis Serial Number.",
            "Diff Config": "Quick Help: Compare the configuration between two devices. Specify the second IP/hostname," +
                           " and choose whether to do set mode or stanza mode. If you are not familiar with the format of the output,"
                           " take a look at 'git diff output' on google.",
            "Health Check": "Quick Help: Health Check runs multiple commands to get routing-engine CPU/memory info, " +
                            "busy processes, temperatures, and alarms. The output will likely show the mgd process using " +
                            "high CPU, this is normal due to the execution of the script logging in and running the commands.",
            "Interface Errors": "Quick Help: Interface Errors will tell you of any input or output errors on all interfaces.",
            "Operational Command(s)": "Quick Help: Run one or more operational command(s) against the device(s). This can " +
                                      "be any non-interactive command(s) that can be run from operational mode. This includes show, " +
                                      "request, traceroute, op scripts, etc.",
            "SCP Files": "Quick Help: SCP file(s) or folder(s) to or from one or more devices. Specify a source and destination " +
                         "file or folder. If Pulling, the source is the remote file/folder, and the destination is the local " +
                         "folder you are putting them. If Pushing, the source is the local file/folder, and the destination would" +
                         " the folder to put them on the remote device. Note, the '~' home directory link can not be used!",
            "Set Command(s)": "Quick Help: A single or multiple set commands that will be sent and committed to the device(s). " +
                              "There are additional optional commit modifiers, which can be used to do several different things. " +
                              "Much more information can be found in the help files.",
            "Shell Command(s)": "Quick Help: Send one or more shell commands to the device(s). Be wary when sending shell " +
                                "commands, you can make instant changes or potentially harm the networking device. Care should be taken."
        }

        # stdout_queue is where the WorkerThread class will dump output to.
        self.stdout_queue = Queue.Queue()
        # thread will be the WorkerThread instantiation.
        self.thread = ""
        # boolean for tracking if the upper options of the GUI are shown.
        self.frames_shown = True

        # ## CREATE THE TOP MENUBAR OPTIONS
        self.menubar = tk.Menu(self)
        # tearoff=0 prohibits windows users from pulling out the menus.
        self.menu_file = tk.Menu(self.menubar, tearoff=0)
        self.menu_help = tk.Menu(self.menubar, tearoff=0)

        self.menubar.add_cascade(menu=self.menu_file, label="File")
        # Added space after Help to prevent OSX from putting spotlight in.
        self.menubar.add_cascade(menu=self.menu_help, label="Help ")

        # Create the File menu and appropriate keyboard shortcuts.
        self.menu_file.add_command(label="Save Template", accelerator='Ctrl-S',
                                   command=lambda: self.ask_template_save(None))
        self.bind_all("<Control-s>", self.ask_template_save)
        self.menu_file.add_command(label="Open Template", accelerator='Ctrl-O',
                                   command=lambda: self.ask_template_open(None))
        self.bind_all("<Control-o>", self.ask_template_open)
        self.menu_file.add_command(label="Set as Defaults",
                                   command=lambda: self.save_template(
                                   self.defaults_file, "defaults"))
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Clear Fields", accelerator='Ctrl-F',
                                   command=lambda: self.clear_fields(None))
        self.bind_all("<Control-f>", self.clear_fields)
        self.menu_file.add_command(label="Clear Output", accelerator='Ctrl-W',
                                   command=lambda: self.clear_output(None))
        self.bind_all("<Control-w>", self.clear_output)
        self.menu_file.add_command(label="Run Script", accelerator='Ctrl-R',
                                   command=lambda: self.go(None))
        self.bind_all("<Control-r>", self.go)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Quit", accelerator='Ctrl-Q',
                                   command=lambda: self.quit(None))
        self.bind_all("<Control-q>", self.quit)

        # Create the Help menu
        self.menu_help.add_command(label="About", command=self.show_about)
        self.menu_help.add_command(label="Go to Docs", command=self.show_help)

        # Add the menubar in.
        self.config(menu=self.menubar)

        ############################################
        # GUI frames, and all user entry widgets   #
        ############################################

        # ## FRAME INITIALIZATION
        # outer frame to hold the ip and creds frames
        self.ip_cred_frame = tk.Frame(self)

        self.ip_frame = tk.Frame(self.ip_cred_frame)
        self.creds_frame = tk.Frame(self.ip_cred_frame)
        # write to file frame
        self.wtf_frame = tk.Frame(self)
        self.options_frame = tk.Frame(self)
        # Set Commands frames for the additional commit options
        self.set_frame = tk.Frame(self.options_frame)
        self.set_frame_2 = tk.Frame(self.options_frame)
        self.help_frame = tk.Frame(self)
        self.buttons_frame = tk.Frame(self)
        self.output_frame = tk.Frame(self, bd=3, relief="groove")

        # #### Target device Section
        # string of actual IP or the file containing list of IPs
        self.ip_label = tk.Label(self.ip_frame, text="IP(s) / Host(s):")
        # Entry for IP or IP list
        self.ip_entry = JaideEntry(self.ip_frame)
        # Button to open file of list of IPs
        self.ip_button = tk.Button(self.ip_frame, text="Select File",
                                   command=lambda:
                                   self.open_file(self.ip_entry), takefocus=0)

        # ### TIMEOUTS AND PORT
        self.timeout_label = tk.Label(self.ip_frame, text="Session Timeout:")
        self.timeout_entry = JaideEntry(self.ip_frame, instance_type=int,
                                        contents=300)
        self.conn_timeout_label = tk.Label(self.ip_frame,
                                           text="Connection Timeout:")
        self.conn_timeout_entry = JaideEntry(self.ip_frame, instance_type=int,
                                             contents=5)

        # #### Authentication
        self.username_label = tk.Label(self.creds_frame, text="Username: ")
        self.username_entry = JaideEntry(self.creds_frame)
        self.password_label = tk.Label(self.creds_frame, text="Password: ")
        self.password_entry = JaideEntry(self.creds_frame, show="*")

        self.port_label = tk.Label(self.creds_frame, text="Port: ")
        self.port_entry = JaideEntry(self.creds_frame, instance_type=int,
                                     contents=22)

        # ## WRITE TO FILE
        self.wtf_entry = JaideEntry(self.wtf_frame)
        self.wtf_button = tk.Button(self.wtf_frame, text="Select File",
                                    command=self.open_wtf, takefocus=0)
        self.wtf_checkbox = JaideCheckbox(self.wtf_frame, text="Write to file",
                                          command=self.check_wtf, takefocus=0)
        self.wtf_radiobuttons = JaideRadiobutton(self.wtf_frame,
                                                 ["Single File",
                                                  "Multiple Files"],
                                                 ["s", "m"], takefocus=0)

        # ## OPTIONS
        # stores which option from options_list is selected
        self.option_value = tk.StringVar()
        # sets defaulted option to first one
        self.option_value.set(self.options_list[0])
        # Actual dropdown list widget. Uses Pmw's option menu because tk base
        # doesn't allow an action to be bound to an option_menu.
        self.option_menu = OM(self.options_frame,
                              command=self.opt_select,
                              menubutton_textvariable=self.option_value,
                              items=self.options_list)
        # Prevents option_menu from taking focus while tabbing
        self.option_menu.component('menubutton').config(takefocus=0)
        self.option_entry = JaideEntry(self.options_frame)
        # format checkbox for operational commands
        self.format_box = JaideCheckbox(self.options_frame,
                                        text="Request XML Format", takefocus=0)

        # ## SCP OPTIONS
        self.scp_direction_value = tk.StringVar()
        self.scp_direction_value.set("Push")
        self.scp_direction_menu = tk.OptionMenu(self.options_frame,
                                                self.scp_direction_value,
                                                'Push', 'Pull')
        self.scp_source_button = tk.Button(self.options_frame,
                                           text="Local Source",
                                           command=lambda:
                                           self.open_file(self.option_entry),
                                           takefocus=0)
        self.scp_dest_button = tk.Button(self.options_frame,
                                         text="Local Destination",
                                         command=lambda: self.open_file(
                                            self.scp_dest_entry),
                                         takefocus=0)
        self.scp_dest_entry = JaideEntry(self.options_frame)

        # ## COMMIT OPTIONS
        self.set_list_button = tk.Button(self.options_frame,
                                         text="Select File",
                                         command=lambda:
                                         self.open_file(self.option_entry),
                                         takefocus=0)
        self.commit_check_button = JaideCheckbox(self.set_frame,
                                                 text="Check Only",
                                                 command=lambda:
                                                 self.commit_option_update(
                                                     'check'),
                                                 takefocus=0)
        self.commit_blank = JaideCheckbox(self.set_frame_2, text="Blank",
                                          command=lambda:
                                          self.commit_option_update('blank'),
                                          takefocus=0)
        self.commit_confirmed_button = JaideCheckbox(self.set_frame,
                                                     text="Confirmed Minutes",
                                                     command=lambda:
                                                     self.commit_option_update(
                                                         'confirmed'),
                                                     takefocus=0)
        self.commit_confirmed_min_entry = JaideEntry(self.set_frame,
                                                     contents="[1-60]")
        self.commit_synch = JaideCheckbox(self.set_frame_2, text="Synchronize",
                                          command=lambda:
                                          self.commit_option_update(
                                              'synchronize'),
                                          takefocus=0)
        self.commit_comment = JaideCheckbox(self.set_frame_2, text="Comment",
                                            command=lambda:
                                            self.commit_option_update(
                                                'comment'),
                                            takefocus=0)
        self.commit_comment_entry = JaideEntry(self.set_frame_2)
        self.commit_at = JaideCheckbox(self.set_frame, text="At Time",
                                       command=lambda:
                                       self.commit_option_update('at'),
                                       takefocus=0)
        self.commit_at_entry = JaideEntry(self.set_frame,
                                          contents="[yyyy-mm-dd ]hh:mm[:ss]")

        # ### Diff Config options
        self.diff_config_mode = tk.StringVar()
        self.diff_config_mode.set("Set")
        self.diff_config_menu = tk.OptionMenu(self.options_frame,
                                              self.diff_config_mode,
                                              "Set", "Stanza")

        # Used to keep rows 1 and 2 of options_frame from being hidden
        self.spacer_label = tk.Label(self.options_frame, takefocus=0)

        # Help label sits next in the target device section
        self.help_value = tk.StringVar("")
        self.help_label = tk.Label(self.help_frame,
                                   textvariable=self.help_value,
                                   justify="left", anchor="nw",
                                   wraplength=790)
        # ## Buttons
        self.go_button = tk.Button(self.buttons_frame, command=lambda:
                                   self.go(None), text="Run Script",
                                   takefocus=0)
        self.stop_button = tk.Button(self.buttons_frame, text="Stop Script",
                                     command=self.stop_script,
                                     state="disabled", takefocus=0)
        self.clear_button = tk.Button(self.buttons_frame, command=lambda:
                                      self.clear_output(None),
                                      text="Clear Output", state="disabled",
                                      takefocus=0)
        self.save_button = tk.Button(self.buttons_frame,
                                     command=self.save_output,
                                     text="Save Output", state="disabled",
                                     takefocus=0)
        self.toggle_frames_button = tk.Button(self.buttons_frame,
                                              command=self.toggle_frames,
                                              text="Toggle Options",
                                              takefocus=0)

        # ## SCRIPT OUTPUT AREA
        self.output_area = tk.Text(self.output_frame, wrap=tk.NONE)
        self.xscrollbar = AutoScrollbar(self.output_frame,
                                        command=self.output_area.xview,
                                        orient=tk.HORIZONTAL, takefocus=0)
        self.yscrollbar = AutoScrollbar(self.output_frame,
                                        command=self.output_area.yview,
                                        takefocus=0)
        self.output_area.config(yscrollcommand=self.yscrollbar.set,
                                xscrollcommand=self.xscrollbar.set,
                                takefocus=0)

        # Separators
        self.sep1 = ttk.Separator(self.ip_cred_frame)
        self.sep2 = ttk.Separator(self)
        self.sep3 = ttk.Separator(self)
        self.sep4 = ttk.Separator(self)
        self.sep5 = ttk.Separator(self)

        #############################################
        # Put the objects we've created on the grid #
        # for the user to see.                      #
        #############################################
        # ## INITIALIZE THE LAYOUT
        self.show_frames()
        self.rowconfigure(9, weight=1)
        self.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(0, weight=1)
        self.output_frame.columnconfigure(0, weight=1)

        # ## GRIDDING FOR ALL WIDGETS VISIBLE AT FIRST LOAD.
        # Section 0 - Target Device(s) - ip_frame
        self.ip_frame.grid(column=0, row=0, sticky="NW")
        self.ip_label.grid(column=0, row=0, sticky="NW")
        self.ip_entry.grid(column=1, row=0, sticky="NW")
        self.ip_button.grid(column=2, row=0, sticky="NW")
        self.timeout_label.grid(column=0, row=1, sticky="NW")
        self.timeout_entry.grid(column=1, row=1, sticky="NW")
        self.conn_timeout_label.grid(column=0, row=2, sticky="NW")
        self.conn_timeout_entry.grid(column=1, row=2, sticky="NW")
        self.sep1.grid(column=1, row=0, sticky="NS", padx=(18, 18))

        # Section 1 - Authentication - creds_frame
        self.creds_frame.grid(column=2, row=0, sticky="NW")
        self.username_label.grid(column=0, row=0, sticky="NW")
        self.username_entry.grid(column=1, row=0, sticky="NW")
        self.password_label.grid(column=0, row=1, sticky="NW")
        self.password_entry.grid(column=1, row=1, sticky="NW")
        self.port_label.grid(column=0, row=2, sticky="NW")
        self.port_entry.grid(column=1, row=2, sticky="NW")

        # This is the help label in the frame below the options frame.
        self.help_label.grid(column=0, row=0, sticky="NWES")

        # Section 2 - Write to File - wtf_frame
        self.wtf_checkbox.grid(column=0, row=0, sticky="NSW")

        # Section 3 - Command Options - options_frame
        self.option_menu.grid(column=0, row=0, sticky="EW")
        self.spacer_label.grid(column=0, row=1, sticky="NW")

        # Section 4 - Action Buttons - buttons_frame
        self.go_button.grid(column=0, row=0, sticky="NW", padx=2)
        self.stop_button.grid(column=1, row=0, sticky="NW", padx=2)
        self.clear_button.grid(column=2, row=0, sticky="NW", padx=2)
        self.save_button.grid(column=3, row=0, sticky="NW", padx=2)
        self.toggle_frames_button.grid(column=4, row=0, sticky="NW", padx=2)

        # Section 5 - Output Area - output_frame
        self.output_area.grid(column=0, row=0, sticky="SWNE")
        self.output_area.columnconfigure(0, weight=100)
        self.xscrollbar.grid(column=0, row=1, sticky="SWNE")
        self.yscrollbar.grid(column=1, row=0, sticky="SWNE")

        # Tie the commit options to the set_frame and set_frame_2
        self.commit_check_button.grid(column=0, row=0, sticky="NW")
        self.commit_confirmed_button.grid(column=3, row=0, sticky="NW")
        self.commit_blank.grid(column=3, row=0, sticky="NW")
        self.commit_synch.grid(column=0, row=0, sticky="NW")
        self.commit_comment.grid(column=1, row=0, sticky="NW")
        self.commit_comment_entry.grid(column=2, row=0, sticky="NW")
        self.commit_at.grid(column=1, row=0, sticky="NW")
        self.commit_at_entry.grid(column=2, row=0, sticky="NW")
        self.commit_confirmed_min_entry.grid(column=4, row=0, sticky="NW")
        # Set the window to a given size. This prevents autoscrollbar
        # 'fluttering' behaviour, and stabilizes the Toggle Output button.
        self.geometry('840x800')

        # Sets the tab order correctly
        self.ip_frame.lift()
        self.creds_frame.lift()
        self.wtf_frame.lift()
        self.options_frame.lift()

        # Run the opt_select method to ensure the proper fields are shown.
        self.opt_select(self.option_value.get())

        # Dictionary for reading and writing template files.
        self.template_opts = {
            "IP": self.ip_entry,
            "Timeout": self.timeout_entry,
            "Username": self.username_entry,
            "Password": self.password_entry,
            "WriteToFileBool": self.wtf_checkbox,
            "WriteToFileLoc": self.wtf_entry,
            "SingleOrMultipleFiles": self.wtf_radiobuttons,
            "Option": self.option_value,
            "FirstArgument": self.option_entry,
            "SCPDest": self.scp_dest_entry,
            "SCPDirection": self.scp_direction_value,
            "CommitCheck": self.commit_check_button,
            "CommitConfirmed": self.commit_confirmed_button,
            "CommitConfirmedMin": self.commit_confirmed_min_entry,
            "CommitBlank": self.commit_blank,
            "CommitAt": self.commit_at,
            "CommitAtTime": self.commit_at_entry,
            "CommitComment": self.commit_comment,
            "CommitCommentValue": self.commit_comment_entry,
            "CommitSynch": self.commit_synch,
            "Format": self.format_box,
            "DiffMode": self.diff_config_mode
        }

        # Load the defaults from file if defaults.ini exists
        if os.path.isfile(self.defaults_file):
            self.open_template(self.defaults_file, "defaults")

    def go(self, event):
        """ Execute the jaide_cli script with the user specified options.

        Purpose: This function is called when the user clicks on the 'Run
               | Script' button. It inserts output letting the user know the
               | script has started, and spawns a subprocess running a
               | WorkerThread instance. It also modifies the different
               | buttons availability, now that the script has started.

        @param event: Any command that tkinter binds a keyboard shortcut to
                    | will receive the event parameter. It is a description of
                    | the keyboard shortcut that generated the event.
        @type event: Tkinter.event object

        @returns: None
        """
        # Ensure the input is valid.
        if self.input_validation():
            # puts cursor at end of text field
            self.output_area.mark_set(tk.INSERT, tk.END)
            self.write_to_output_area("****** Starting Jaide ******\n")

            # Gets username/ip from appropriate StringVars
            username = self.username_entry.get().strip()
            timeout = self.timeout_entry.get()

            # if they are requesting xml.
            out_fmt = 'xml' if self.format_box.get() else 'text'

            # some functions need to know if we're running against >1 device
            multi = True if (len([ip for ip in
                             clean_lines(self.ip_entry.get())]) > 1) else False

            # Looks up the selected option from dropdown against the conversion
            # dictionary to get the right Jaide function to call
            function = self.option_conversion[self.option_value.get()]

            if (self.scp_direction_value.get() == "Pull" and
                    function == wrap.push):
                function = wrap.pull

            # Need to set commit options only if their boxes are checked.
            at_time = self.commit_at_entry.get() if self.commit_at.get() else None
            confirmed = int(self.commit_confirmed_min_entry.get()) * 60 if self.commit_confirmed_button.get() else None
            comment = self.commit_comment_entry.get() if self.commit_comment.get() else None
            # build the args translation array
            args_translation = {
                "Operational Command(s)": [self.option_entry.get().strip(),
                                           out_fmt, False],
                "Device Info": [],
                "Diff Config": [self.option_entry.get().strip(),
                                self.diff_config_mode.get().lower()],
                "Health Check": [],
                "Interface Errors": [],
                "Set Command(s)": [self.option_entry.get().strip(),
                                   self.commit_check_button.get(),
                                   self.commit_synch.get(),
                                   comment,
                                   confirmed,
                                   at_time,
                                   self.commit_blank.get()],
                "SCP Files": [self.option_entry.get().strip(),
                              self.scp_dest_entry.get(), False, multi],
                "Shell Command(s)": [self.option_entry.get().strip()],
                "Show | Compare": [self.option_entry.get().strip()]
            }

            # set the args to pass to the final function based on their choice.
            argsToPass = args_translation[self.option_value.get()]

            # only pass the value of the write_to_file entry if wtf is checked.
            write_to_file = self.wtf_entry.get() if self.wtf_checkbox.get() else ""
            # Create the WorkerThread class to run the Jaide functions.
            self.thread = WorkerThread(
                argsToPass=argsToPass,
                sess_timeout=timeout,
                conn_timeout=self.conn_timeout_entry.get(),
                port=self.port_entry.get(),
                command=function,
                stdout=self.stdout_queue,
                ip=self.ip_entry.get(),
                username=username,
                password=self.password_entry.get().strip(),
                write_to_file=write_to_file,
                wtf_style=self.wtf_radiobuttons.get(),
            )
            self.thread.daemon = True
            self.thread.start()

            # Change the state of the buttons now that the script is running,
            # so the user can save the output, kill the script, etc.
            self.go_button.configure(state="disabled")
            self.clear_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.save_button.configure(state="disabled")
            self.get_output()

    def get_output(self):
        """ Listen to WorkerThread and retrieve stdout from the Jaide script.

        Purpose: This function listens to the sub process generated by the
               | 'Run Script' button, and dumps the output to the output_area
               | using the function write_to_output_area. If the process is no
               | longer alive, it changes the activation of buttons, and lets
               | the user know that the script is done.

        @returns: None
        """
        try:  # pull from the stdout_queue, and write it to the output_area
            self.write_to_output_area(self.stdout_queue.get_nowait())
        # Nothing in the queue, but the thread could be alive.
        except Queue.Empty:
            pass
        # The WorkerThread subprocess has completed, and we need to wrap up.
        if not self.thread.isAlive():
            while not self.stdout_queue.empty():
                self.write_to_output_area(self.stdout_queue.get_nowait())
            self.go_button.configure(state="normal")
            self.clear_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.save_button.configure(state="normal")
            self.write_to_output_area("****** Jaide Command Completed ******\n")
            self.thread.join()
            return
        # recursively call this function every 100ms, writing any new output.
        self.after(100, self.get_output)

    def input_validation(self):
        """ Validate the inputs the user has entered.

        Purpose: This function is used to validate the inputs of the user when
               | they press the 'Run Script' button. It will return a boolean
               | with True for passing the checks, and otherwise False.

        @returns: True if all checks pass, False if any single check fails.
        @rtype: bool
        """
        # Making sure the user typed something into the IP field.
        if self.ip_entry.get() == "":
            tkMessageBox.showinfo("IP Entry", "Please enter an IP address or"
                                  " IP address list file.")
        # Ensure there is a value typed into the username and password fields.
        elif "" in [self.username_entry.get(), self.password_entry.get()]:
            tkMessageBox.showinfo("Credentials", "Please enter both a username"
                                  " and password.")
        elif self.wtf_entry.get() == "" and self.wtf_checkbox.get():
            tkMessageBox.showinfo("Write to File", "When writing to a file, a "
                                  "filename must be specified.")
        # Ensure that if an option is chosen that requires extra input that
        # they have something in the entry widget.
        elif (self.option_value.get() in self.yes_options and
                self.option_entry.get() == "" and
                self.commit_blank.get() == 0):
            tkMessageBox.showinfo("Option Input", "You chose an option that "
                                  "requires extra input, and didn't specify"
                                  " any additional information. For example,"
                                  " when selecting \"Operational Command(s)\","
                                  " a command string must be typed into the "
                                  "entry box.")
        # if doing commit at, check that the datetime format is valid.
        elif ((self.option_value.get() == 'Set Command(s)' and
              self.commit_at.get()) and (self.commit_at_entry.get() == "" or
              (re.match(r'([0-2]\d)(:[0-5]\d){1,2}',
               self.commit_at_entry.get()) is None and
               re.match(r'\d{4}-[01]\d-[0-3]\d [0-2]\d:[0-5]\d(:[0-5]\d)?',
               self.commit_at_entry.get()) is None))):
            tkMessageBox.showinfo("Commit At Time", "The time value you wrote "
                                  "for commit at was not valid. It must be one"
                                  " of two formats (seconds are optional):"
                                  "\n'hh:mm[:ss]'\n'yyyy-mm-dd hh:mm[:ss]'")
        elif ((self.option_value.get() == 'Set Command(s)' and
              self.commit_comment.get()) and (
              self.commit_comment_entry.get() == "" or
              '"' in self.commit_comment_entry.get())):
            tkMessageBox.showinfo("Commit Comment", "If commenting on the "
                                  "commit, you must specify a string, and "
                                  "it cannot contain double-quotes (\").")
        else:
            try:
                if (self.option_value.get() == 'Set Command(s)' and
                        self.commit_confirmed_button.get()):
                    int(self.commit_confirmed_min_entry.get())
            except ValueError:
                tkMessageBox.showinfo("Commit Confirmed", "A Commit Confirmed "
                                      "value must be an integer between 1 and"
                                      " 60 minutes.")
            else:
                # Make sure the timeout value is a number.
                try:
                    isinstance(self.timeout_entry.get(), int)
                except ValueError:
                    tkMessageBox.showinfo("Timeout", "A timeout value must be "
                                          "an integer, in minutes, between 1 "
                                          "and 60.")
                else:  # They've passed all checks.
                    return True
        return False

    def show_about(self):
        """ Show the about text for the application. """
        aboutInfo = tk.Toplevel()
        aboutInfoLabel = tk.Label(aboutInfo, padx=50, pady=50,
                                  text="The Jaide GUI Application is a GUI "
                                  "wrapper for the jaide CLI tool.\nVersion "
                                  "1.1.0\n\rContributors:\n Geoff Rhodes "
                                  "(https://github.com/geoffrhodes) and Nathan"
                                  " Printz (https://github.com/nprintz)\n\r"
                                  "More information about Jaide and the Jaide "
                                  "GUI can be found at https://github.com"
                                  "/NetworkAutomation/jaidegui"
                                  "\n\rThe compiled versions for Windows or "
                                  "Mac can be found at:\n"
                                  "https://github.com/NetworkAutomation/"
                                  "jaidegui/releases/latest")
        aboutInfoLabel.pack()

    def show_help(self):
        """ Show the help file or webpage.

        Purpose: This is called when the user selects the 'Help' menubar
               | option. It opens the readthedocs.org page.
        """
        try:
            webb.open('http://jaidegui.readthedocs.org/')
        except webb.Error:
            pass

    def write_to_output_area(self, output):
        """ Append string to output_area, and scroll to the bottom.

        @param output: String of the output to dump to the output_area
        @type output: str or unicode

        @returns: None
        """
        if isinstance(output, basestring):
            if output[-1:] is not "\n":
                output += "\n"
            self.output_area.insert(tk.END, output)
            self.output_area.see(tk.END)

    def ask_template_save(self, event):
        """ Prompt to save a template.

        Purpose: Asks for the filepath of where to save the template file.
               | If they give us one, we pass it to the save_template()
               | function to actually be opened.

        @param event: Any command that tkinter binds a keyboard shortcut to
                    | will receive the event parameter. It is a description
                    | of the keyboard shortcut that generated the event.
        @type event: Tkinter.event object

        @returns: None
        """
        return_file = tkFileDialog.asksaveasfilename()
        if return_file:
            self.save_template(return_file, "template")

    def save_template(self, filepath, filetype):
        """ Save the template file.

        Purpose: Ask for a file name and writes all variable information to it.
               | Passwords are obfuscated with Base64 encoding, but this is
               | by no means considered secure.

        @param filepath: The filepath of the template file that we are saving
                       | to with the information from the objects in the GUI.
        @type filepath: str or unicode
        @param filetype: This should be a string of either "defaults" or
                       | "template". This is used to notify the user what type
                       | of file failed to open in case of a problem.
        @type filetype: str or unicode

        @returns: None
        """
        try:
            output_file = open(filepath, 'wb')
        except IOError as e:
            self.write_to_output_area("Couldn't open file to save the %s file."
                                      " Attempted location: %s\nError:\n%s" %
                                      (filetype, output_file, str(e)))
        else:
            # Write each template option in the dictionary to the template.
            for key, value in self.template_opts.iteritems():
                if key == "Password":  # passwords need to be encoded.
                    output_file.write(key + ":~:" +
                                      base64.b64encode(value.get()) + "\n")
                else:
                    output_file.write(key + ":~:" + str(value.get()) + "\n")
            output_file.close()

    def ask_template_open(self, event):
        """ Prompt for a filepath to open a template.

        Purpose: Asks for the filepath of a template file. If they give us
               | one, we pass it to the open_template() function to actually
               | be opened.

        @param event: Any command that tkinter binds a keyboard shortcut to
                    | will receive the event parameter. It is a description
                    | of the keyboard shortcut that generated the event.
        @type event: Tkinter.event object

        @returns: None
        """
        return_file = tkFileDialog.askopenfilename()
        if return_file:
            self.open_template(return_file, "template")

    def open_template(self, filepath, filetype):
        """ Open a template file.

        Purpose: Loads information from a template file and replaces the
               | options in the GUI with that of the template file.

            @param filepath: The filepath of the template file that we are
                           | opening to read in and replace the options with
                           | the information from the template.
            @type filepath: str or unicode
            @param filetype: This should be a string of either "defaults" or
                           | "template". This is used to notify the user what
                           | type of file failed to load in case of a problem.
            @type filetype: str or unicode

            @returns: None
        """
        try:
            input_file = open(filepath, "rb")
        except IOError as e:
            self.write_to_output_area("Couldn't open " + filetype + " file to "
                                      "import values. Attempted file: " +
                                      filepath + " Error: \n" + str(e))
        else:
            try:
                # TODO: change templates to be in JSON format.
                # Read the template file and set the fields accordingly.
                for line in input_file.readlines():
                    line = line.split(':~:')
                    if line[0] == "SingleOrMultipleFiles":
                        self.template_opts[line[0]].set("key",
                                                        line[1].rstrip())
                    elif line[0] == "Password":
                        self.password_entry.set(base64.b64decode(line[1].rstrip()))
                    else:
                        self.template_opts[line[0]].set(line[1].rstrip())
                # check the option menu, wtf, commit check, and commit
                # confirmed to update the visible options.
                self.opt_select(self.option_value.get())
                self.check_wtf()
            except Exception as e:
                self.write_to_output_area("Could not open template. Error:\n"
                                          + str(e))
            finally:
                input_file.close()

    def stop_script(self):
        """ Kill the active running script.

        Purpose: Called to kill the subprocess 'thread' which is actually
               | running the jaide command. This is called when the user
               | clicks on the Stop Script button.

            @returns: None
        """
        self.write_to_output_area("****** Attempting to Stop Jaide ******")
        self.thread.kill_proc()

    def opt_select(self, opt):
        """ Show and hide options fields when a drop down item is selected.

        Purpose: This method looks at what option they have chosen from the
               | drop down menu, and show the appropriate fields for the user
               | to fill out for that option. This is the callback function for
               | the Pmw.optionMenu, and this is the reason we use PMW, so that
               | we can point the drop down menu at this callback function.

        @param opt: The name of the option chosen by the user. The PMWmenu
                  | object passes this automatically when the opt_select
                  | function is called by choosing an option.
        @type opt: str

        @returns: None
        """
        # First thing we do is forget all placement and deselect options,
        # then we'll update according to what they chose afterwards.
        self.format_box.grid_forget()
        self.set_frame.grid_forget()
        self.set_frame_2.grid_forget()
        self.option_entry.grid_forget()
        self.set_list_button.grid_forget()
        self.scp_source_button.grid_forget()
        self.scp_dest_entry.grid_forget()
        self.scp_dest_button.grid_forget()
        self.scp_direction_menu.grid_forget()
        self.spacer_label.grid_forget()
        self.diff_config_menu.grid_forget()
        # We only want to deselect the commit options if we're changing to
        # something other than 'Set Command(s)'. This prevents these commit
        # options from being cleared on loading a template/defaults file.
        if opt != "Set Command(s)":
            self.commit_check_button.deselect()
            self.commit_confirmed_button.deselect()
            self.commit_blank.deselect()
            self.commit_synch.deselect()
            self.commit_at.deselect()
            self.commit_comment.deselect()

        if opt == "------":
            self.option_value.set("Device Info")

        if opt == "SCP Files":
            self.scp_direction_menu.grid(column=1, columnspan=2,
                                         row=0, sticky="NW")
            self.option_entry.grid(column=0, row=1, sticky="NW")
            self.scp_source_button.grid(column=1, row=1, sticky="NW", padx=2)
            self.scp_dest_entry.grid(column=2, row=1, sticky="NW")
            self.scp_dest_button.grid(column=3, row=1, sticky="NW", padx=2)

        # Any option that requires a single text arg
        elif opt in self.yes_options:
            self.option_entry.grid(column=1, columnspan=2, row=0, sticky="NEW")

            # If we are getting a list of set command, show file open button
            # and commit check / confirmed boxes
            if opt == "Set Command(s)":
                self.set_list_button.grid(column=3, row=0, sticky="NW", padx=2)
                self.set_frame.grid(column=0, columnspan=4, row=1,
                                    sticky="NW", pady=(2, 2))
                self.set_frame_2.grid(column=0, columnspan=4, row=2,
                                      sticky="NW", pady=(2, 2))
            else:
                self.spacer_label.grid(column=1, columnspan=2,
                                       row=1, sticky="NW")

            if opt == "Operational Command(s)":
                self.set_list_button.grid(column=3, row=0, sticky="NW", padx=2)
                self.format_box.grid(column=0, row=1, sticky="NW")
            elif opt == "Diff Config":
                self.diff_config_menu.grid(column=3, row=0,
                                           sticky="NW", padx=2)
            elif opt == "Show | Compare":
                self.set_list_button.grid(column=3, row=0, sticky="NW", padx=2)
        else:
            # No option
            self.spacer_label.grid(column=1, columnspan=2, row=1, sticky="NW")

        # Update the help text for the new command
        self.help_value.set(self.help_conversion[opt])
        time.sleep(.05)  # sleep needed to avoid artifacts when updating frames
        # Update the UI after we've made our changes
        self.update()

    def open_file(self, entry_object):
        """ Find a filepath and place it in entry_object.

        Purpose: This method is used to prompt the user to find a file on
               | their local machine that already exists. Puts the filepath in
               | the text entry object that was passed to this method. If the
               | user does not specify a file (ie. presses the 'cancel' button
               | on the dialog box), we do nothing.

        @param entry_object: This is the Tkinter Entry object where the
                           | filepath that the user specifies will be set.
        @type entry_object: Tkinter.Entry object

        @returns: None
        """
        return_file = tkFileDialog.askopenfilename()
        if return_file:
            entry_object.delete(0, tk.END)
            entry_object.insert(0, return_file)

    def open_wtf(self):
        """ Ask for and insert a filepath into the write_to_file object. """
        return_file = tkFileDialog.asksaveasfilename()
        if return_file:
            self.wtf_entry.delete(0, tk.END)
            self.wtf_entry.insert(0, return_file)

    def check_wtf(self):
        """ Check if write to file is checked or not.

        Purpose: This function is called whenever the user clicks on the
               | checkbox for writing output to a file. It will take the
               | appropriate action based on whether the box was checked
               | previously or not. If it is now checked, it will add the
               | wtf_entry and wtf_button options for specifying a file to
               | write the output to. If it is now unchecked, it will
               | remove these two objects.

        @returns: None
        """
        # if WTF checkbox is checked, enable the Entry and file load button
        if self.wtf_checkbox.get() == 1:
            self.wtf_entry.grid(column=1, row=0)
            self.wtf_button.grid(column=2, row=0, sticky="NW", padx=2)
            self.wtf_radiobuttons.grid("index", 0, column=4,
                                       row=0, sticky="NSW")
            self.wtf_radiobuttons.grid("index", 1, column=5,
                                       row=0, sticky="NSW")

        # if WTF checkbox is not checked, re-disable the entry options
        if self.wtf_checkbox.get() == 0:
            self.wtf_entry.grid_forget()
            self.wtf_button.grid_forget()
            self.wtf_radiobuttons.grid_forget("index", 0)
            self.wtf_radiobuttons.grid_forget("index", 1)

    def commit_option_update(self, check_type):
        """ Update the commit options.

        Purpose: This function is called when any of the commit option check
               | boxes are clicked. Depending on which one we click, we
               | deselect the other two, and forget or create the grid for
               | the commit confirmed minutes entry as necessary.

        @param check_type: A string identifier stating which commit option
                         | is being clicked. We are expecting one of these
                         | options: 'blank', 'check', 'at', 'comment',
                         | 'synchronize', or 'confirmed'.
        @type check_type: str

        @returns: None
        """
        if check_type == 'blank' and self.commit_blank.get():
            self.commit_confirmed_button.deselect()
            self.commit_check_button.deselect()
        elif check_type == 'check' and self.commit_check_button.get():
            self.commit_confirmed_button.deselect()
            self.commit_blank.deselect()
            self.commit_at.deselect()
            self.commit_synch.deselect()
            self.commit_comment.deselect()
        elif check_type == 'confirmed' and self.commit_confirmed_button.get():
            self.commit_check_button.deselect()
            self.commit_blank.deselect()
            self.commit_at.deselect()
        elif check_type == 'at' and self.commit_at.get():
            self.commit_confirmed_button.deselect()
            self.commit_blank.deselect()
            self.commit_check_button.deselect()
        elif check_type == 'comment' and self.commit_comment.get():
            self.commit_check_button.deselect()
        elif check_type == 'synchronize' and self.commit_synch.get():
            self.commit_check_button.deselect()

    def clear_output(self, event):
        """ Clear the output field.

        @param event: Any command that tkinter binds a keyboard shortcut to
                    | will receive the event parameter. It is a description of
                    | the keyboard shortcut that generated the event.
        @type event: Tkinter.event object

        @returns: None
        """
        self.output_area.delete(1.0, tk.END)

    def save_output(self):
        """ Save the text in the output area to a file. """
        return_file = tkFileDialog.asksaveasfilename()
        # If no file is chosen, do not try to open it.
        if return_file:
            try:
                outFile = open(return_file, 'w+b')
            except IOError:
                tkMessageBox.showinfo("Couldn't open file.", "The file you"
                                      " specified could not be opened.")
            else:
                outFile.write(self.output_area.get(1.0, tk.END))
                outFile.close()

    def quit(self, event):
        """ Quit the application, called on selecting File > Quit.

        @param event: Any command that tkinter binds a keyboard shortcut to
                    | will receive the event parameter. It is a description of
                    | the keyboard shortcut that generated the event.
        @type event: Tkinter.event object

        @returns: None
        """
        sys.exit(0)

    def clear_fields(self, event):
        """ Clear all input fields.

        @param event: Any command that tkinter binds a keyboard shortcut to
                    | will receive the event parameter. It is a description of
                    | the keyboard shortcut that generated the event.
        @type event: Tkinter.event object

        @returns: None
        """
        self.ip_entry.delete(0, tk.END)
        self.timeout_entry.delete(0, tk.END)
        self.timeout_entry.insert(0, '300')
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.wtf_entry.delete(0, tk.END)
        self.wtf_checkbox.deselect()
        self.option_entry.delete(0, tk.END)
        self.option_entry.delete(0, tk.END)
        self.scp_dest_entry.delete(0, tk.END)
        self.commit_comment_entry.delete(0, tk.END)
        self.commit_at_entry.delete(0, tk.END)
        self.commit_check_button.deselect()
        self.commit_confirmed_button.deselect()
        self.commit_blank.deselect()
        self.commit_synch.deselect()
        self.commit_at.deselect()
        self.commit_comment.deselect()

    def show_frames(self):
        """ Grid all separators and frames. """
        self.ip_cred_frame.grid(row=0, column=0, sticky="NEW",
                                padx=(25, 25), pady=(25, 0))
        self.sep2.grid(row=1, column=0, sticky="WE", pady=12, padx=12)

        self.wtf_frame.grid(row=2, column=0, sticky="NW", padx=(25, 0))
        self.sep3.grid(row=3, column=0, sticky="WE", pady=12, padx=12)

        self.options_frame.grid(row=4, column=0, sticky="NEW", padx=(25, 0))
        self.sep4.grid(row=5, column=0, sticky="WE", pady=12, padx=12)

        self.help_frame.grid(row=6, column=0, sticky="NW", padx=(25, 0))
        self.sep5.grid(row=7, column=0, sticky="WE", pady=12, padx=12)

        self.buttons_frame.grid(row=8, column=0, sticky="NW",
                                padx=(25, 25), pady=(0, 10))
        self.output_frame.grid(row=9, column=0, sticky="SWNE",
                               padx=(25, 25), pady=(0, 25))

        self.update()

    def toggle_frames(self):
        """ Show or hide the non-output frames. """
        if self.frames_shown:
            self.ip_cred_frame.grid_forget()
            self.wtf_frame.grid_forget()
            self.help_frame.grid_forget()

            self.sep2.grid_forget()
            self.sep3.grid_forget()
            self.sep4.grid_forget()

            self.update()
            self.frames_shown = False
        else:
            self.show_frames()
            self.frames_shown = True


def main():
    """ Initialize the GUI. """
    # freeze support provides support for compiling to a single executable.
    mp.freeze_support()
    gui = JaideGUI(None)
    gui.mainloop()

if __name__ == "__main__":
    main()
