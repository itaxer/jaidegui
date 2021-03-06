What is the Jaide GUI?  
======================  

The `jaidegui` package extends the `jaide` package we've built and wraps it to create an easy-to-use interface for network engineers and system administrators who simply want to manipulate Junos devices quickly. Some features of the Jaide GUI include being able to poll devices for interface errors, grab basic system information, send any operational mode commands, send and commit a file containing a list of set commands, copy files to/from devices, get a configuration diff between two devices, perform a commit check, and run shell commands.  

> **NOTE** This tool is most beneficial to those who have a basic understanding of JUNOS. This tool can be used to perform several functions against multiple Juniper devices running Junos very easily.  Please understand the ramifications of your actions when using this script before executing it. You can push very significant changes or CPU intensive commands to a lot of devices in the network from one command or GUI execution. This tool should be used with forethought, and we are not responsible for negligence, misuse, time, outages, damages or other repercussions as a result of using this tool.  

More information on the underlying `jaide` packages can be found on the [Jaide github page](https://github.com/NetworkAutomation/jaide).

Jaide, and therefore the CLI tool and the Jaide GUI, leverage several connection types to JunOS devices using python, including: ncclient, paramiko, and scp. With this base of modules, our goal is the ability to perform as many functions that you can do by directly connecting to a device from a remote interface (either Jaide object, or the CLI tool). Since we can do these remotely from one interface, these functions rapidly against multiple devices very easily. The CLI tool leverages multiprocessing for handling multiple connections simultaneously. Pushing code and upgrading 20 devices is quite a simple task with the Jaide tool in hand. 
