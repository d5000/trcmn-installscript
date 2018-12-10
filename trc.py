#! /usr/bin/env python
from subprocess import Popen,PIPE,STDOUT
import collections
import os
import os.path
import sys
import time
import math
import os
import time
from urllib2 import urlopen

BOOTSTRAP_URL = "https://mega.nz/#!EipzEYKI!DSL49ZXIXSetPX4nXrEcWGExK1yPeMelckYBPNbcg7Q"
SENTINEL_GIT_URL = "https://github.com/terracoin/sentinel.git"

# Maybe pull this from online, setup a file in bin on terracoin.io?
TERRACOIN_WALLET = "https://terracoin.io/bin/terracoin-core-current/terracoin-LATEST-x86_64-linux-gnu.tar.gz"

MN_USERNAME = "mn1"
MN_PORT = 13333
MN_RPCPORT = 22350
MN_NODELIST = ""

MN_LFOLDER = ".terracoincore"
MN_WFOLDER = "TerracoinCore"
MN_CONFIGFILE = "terracoin.conf"
MN_DAEMON = "terracoind"
MN_CLI = "terracoin-cli"
MN_EXPLORER = "https://explorer.terracoin.io/"

MN_SWAPSIZE = "2G"
SERVER_IP = urlopen('https://api.ipify.org/').read()
DEFAULT_COLOR = "\x1b[0m"
PRIVATE_KEY = ""

def print_info(message):
    BLUE = '\033[94m'
    print(BLUE + "[*] " + str(message) + DEFAULT_COLOR)
    time.sleep(1)

def print_warning(message):
    YELLOW = '\033[93m'
    print(YELLOW + "[*] " + str(message) + DEFAULT_COLOR)
    time.sleep(1)

def print_error(message):
    RED = '\033[91m'
    print(RED + "[*] " + str(message) + DEFAULT_COLOR)
    time.sleep(1)

def get_terminal_size():
    import fcntl, termios, struct
    h, w, hp, wp = struct.unpack('HHHH',
        fcntl.ioctl(0, termios.TIOCGWINSZ,
        struct.pack('HHHH', 0, 0, 0, 0)))
    return w, h
    
def remove_lines(lines):
    CURSOR_UP_ONE = '\x1b[1A'
    ERASE_LINE = '\x1b[2K'
    for l in lines:
        sys.stdout.write(CURSOR_UP_ONE + '\r' + ERASE_LINE)
        sys.stdout.flush()

def run_command_as(user, command, remove=True):
    run_command('su - {} -c "{}" '.format(user, command), remove)

def run_command(command, remove=True):
    if remove:
    	out = Popen(command, stderr=STDOUT, stdout=PIPE, shell=True)
    	lines = []
    	
    	while True:
    	    line = out.stdout.readline()
    	    if (line == ""):
    	        break
    	    
    	    # remove previous lines     
    	    remove_lines(lines)
    	    
    	    w, h = get_terminal_size()
    	    lines.append(line.strip().encode('string_escape')[:w-3] + "\n")
    	    if(len(lines) >= 9):
    	        del lines[0]

    	    # print lines again
    	    for l in lines:
    	        sys.stdout.write('\r')
    	        sys.stdout.write(l)
    	    sys.stdout.flush()

    	remove_lines(lines) 
    	out.wait()
    else:
	os.system(command)

def print_welcome():
    os.system('clear')
    GREEN = '\033[32m'
    print(GREEN + "  _____                             _       " + DEFAULT_COLOR)
    print(GREEN + " |_   _|__ _ __ _ __ __ _  ___ ___ (_)_ __  " + DEFAULT_COLOR)
    print(GREEN + "   | |/ _ \ '__| '__/ _` |/ __/ _ \| | '_ \ " + DEFAULT_COLOR)
    print(GREEN + "   | |  __/ |  | | | (_| | (_| (_) | | | | |" + DEFAULT_COLOR)
    print(GREEN + "   |_|\___|_|  |_|  \__,_|\___\___/|_|_| |_|" + DEFAULT_COLOR)
    print(GREEN + "                                            " + DEFAULT_COLOR)
    print_info("Terracoin masternode installer v1.3")

def update_system():
    print_info("Updating the system...")
    run_command("apt-get update")
    run_command("apt-get upgrade -y")
    run_command("apt-get dist-upgrade -y")

def check_root():
    print_info("Check root privileges")
    user = os.getuid()
    if user != 0:
        print_error("This program requires root privileges.  Run as root user.")
        sys.exit(-1)

def setup_wallet():
    print_info("Allocating swap...")
    run_command("fallocate -l {} /swapfile".format(MN_SWAPSIZE))
    run_command("chmod 600 /swapfile")
    run_command("mkswap /swapfile")
    run_command("swapon /swapfile")

    f = open('/etc/fstab','r+b')
    line = '/swapfile   none    swap    sw    0   0 \n'
    lines = f.readlines()
    if (lines[-1] != line):
        f.write(line)
        f.close()

    print_info("Installing wallet dependencies...")
    run_command("apt-get -y install software-properties-common")
    run_command("add-apt-repository ppa:bitcoin/bitcoin -y")
    run_command("apt-get update")
    run_command("apt-get --assume-yes install git unzip libboost-program-options-dev libboost-test-dev libdb4.8-dev "
                "libdb4.8++-dev libminiupnpc-dev libevent-dev libzmq3-dev libboost-filesystem1.58.0 libdb4.8++ "
                "libevent-2.0-5 libevent-core-2.0-5 libevent-pthreads-2.0-5 libminiupnpc10 libsodium18 "
                "libboost-system1.58.0 libboost-thread1.58.0 libevent-2.0-5 libzmq5 libboost-chrono1.58.0")

    print_info("Downloading wallet...")
    run_command("wget {} -O /tmp/wallet.tar.gz".format(TERRACOIN_WALLET ))
    run_command("cd /tmp && tar xzf wallet.tar.gz")
    run_command("find /tmp -name {} -exec cp {{}} /usr/local/bin \;".format(MN_DAEMON))
    run_command("find /tmp -name {} -exec cp {{}} /usr/local/bin \;".format(MN_CLI))

def setup_masternode():
    global PRIVATE_KEY
    print_info("Setting up masternode...")
    run_command("useradd --create-home -G sudo {}".format(MN_USERNAME))

    need_credential = True
    if os.path.isfile("/usr/local/bin/{}".format(MN_DAEMON)) and os.path.isfile("/usr/local/bin/{}".format(MN_CLI)) and os.path.isfile("/home/{}/{}/{}".format(MN_USERNAME, MN_LFOLDER, MN_CONFIGFILE)):
        need_credential = False
        run_command_as(MN_USERNAME, "{} stop".format(MN_CLI))
        PRIVATE_KEY = "using the previous private key"
        print_info("Using the previous rpc username, prc password and private key.")

    if need_credential:
        print_info("Open your desktop wallet config file (%appdata%/{}/{}) and copy\n    your rpc username and password! If it is not there create one! E.g.:\n\trpcuser=[SomeUserName]\n\trpcpassword=[DifficultAndLongPassword]".format(MN_WFOLDER, MN_CONFIGFILE))
        print_warning("The # is an illegal character for rpc username and password!")
        rpc_username = raw_input("rpcuser: ")
        rpc_password = raw_input("rpcpassword: ")
    
        print_info("Open your wallet console (Tools => Debug Console) and create a new masternode private key: masternode genkey")
        masternode_priv_key = raw_input("masternodeprivkey: ")
        PRIVATE_KEY = masternode_priv_key
        
        config = """rpcuser={}
rpcpassword={}
rpcallowip=127.0.0.1
rpcport={}
port={}
server=1
listen=1
daemon=1
logtimestamps=1
mnconflock=1
masternode=1
disablewallet=1
externalip={}:{}
masternodeprivkey={}
{}""".format(rpc_username, rpc_password, MN_RPCPORT, MN_PORT, SERVER_IP, MN_PORT, masternode_priv_key, MN_NODELIST)
    
        # creates folder structure
        run_command_as(MN_USERNAME, "mkdir -p /home/{}/{}/".format(MN_USERNAME, MN_LFOLDER))
        run_command_as(MN_USERNAME, "touch /home/{}/{}/{}".format(MN_USERNAME, MN_LFOLDER, MN_CONFIGFILE))
        
        print_info("Saving config file...")
        with open('/home/{}/{}/{}'.format(MN_USERNAME, MN_LFOLDER, MN_CONFIGFILE), 'w') as f:
            f.write(config)
        
    print_info("Downloading blockchain file...")
    run_command("apt-get --assume-yes install megatools")
    filename = "blockchain.rar"
    run_command_as(MN_USERNAME, "cd && megadl '{}' --path {} 2>/dev/null".format(BOOTSTRAP_URL, filename), False)
    
    print_info("Unzipping the file...")
    run_command_as(MN_USERNAME, "cd && rm -rf {0}/blocks {0}/chainstate".format(MN_LFOLDER))
    run_command("apt-get --assume-yes install unrar")
    run_command_as(MN_USERNAME, "cd && unrar x -o+ {} {}".format(filename, MN_LFOLDER))
       
    os.system('su - {} -c "{}" '.format(MN_USERNAME, MN_DAEMON + ' -daemon'))
    print_warning("Masternode started syncing in the background...")

def crontab(job):
    p = Popen("crontab -l -u {} 2> /dev/null".format(MN_USERNAME), stderr=STDOUT, stdout=PIPE, shell=True)
    p.wait()
    lines = p.stdout.readlines()
    job = job + "\n"
    if job not in lines:
        print_info("Cron job doesn't exist yet, adding it to crontab")
        lines.append(job)
        p = Popen('echo "{}" | crontab -u {} -'.format(''.join(lines), MN_USERNAME), stderr=STDOUT, stdout=PIPE, shell=True)
        p.wait()


def autostart_masternode():
    job = "@reboot /usr/local/bin/{}".format(MN_DAEMON)
    crontab(job)

def rotate_logs():
    print_info("Enable logfile rotating...")
    f = open('/etc/logrotate.d/terracoin_masternode_{}'.format(MN_USERNAME),'w')
    f.write('''/home/{0}/{1}/debug.log {{
    daily
    missingok
    rotate 14
    size 10M
    compress
    notifempty
    create 0640 {0} {0}
    copytruncate
}}

/home/{0}/{1}/sentinel/sentinel.log {{
    daily
    missingok
    rotate 14
    size 10M
    compress
    notifempty
    create 0640 {0} {0}
}}
'''.format(MN_USERNAME, MN_LFOLDER, MN_CLI, MN_DAEMON))
    f.close()

    

def setup_sentinel():
    # no sentinel support
    if SENTINEL_GIT_URL == "":
        return
    
    print_info("Setting up Sentinel (/home/{}/{}/sentinel)...".format(MN_USERNAME, MN_LFOLDER))

    # install dependencies
    run_command("apt-get -y install python-virtualenv git virtualenv")

    # download and install sentinel
    run_command_as(MN_USERNAME, "git clone {} /home/{}/{}/sentinel".format(SENTINEL_GIT_URL, MN_USERNAME, MN_LFOLDER))
    run_command_as(MN_USERNAME, "cd /home/{}/{}/sentinel && virtualenv ./venv ".format(MN_USERNAME, MN_LFOLDER))
    run_command_as(MN_USERNAME, "cd /home/{}/{}/sentinel && ./venv/bin/pip install -r requirements.txt".format(MN_USERNAME, MN_LFOLDER))

    # run sentinel every minutes
    job = "* * * * * cd /home/{}/{}/sentinel && SENTINEL_DEBUG=1 ./venv/bin/python bin/sentinel.py >> sentinel.log 2>&1".format(MN_USERNAME, MN_LFOLDER)
    crontab(job)

    # try to update sentinel every day
    job = "* * 1 * * cd /home/{}/{}/sentinel && git pull https://github.com/terracoin/sentinel.git".format(MN_USERNAME, MN_LFOLDER)
    crontab(job)
    
def end():

    mn_base_data = """
    Alias: Masternode1
    IP: {}
    Private key: {}
    Transaction ID: [The transaction id of the desposit. 'masternode outputs']
    Transaction index: [The transaction index of the desposit. 'masternode outputs']
    --------------------------------------------------
"""

    mn_data = mn_base_data.format(SERVER_IP + ":" + str(MN_PORT), PRIVATE_KEY)

    imp = R"""Vs lbh sbhaq gur thvqr naq guvf fpevcg hfrshy pbafvqre gb fhccbeg zr.\a    GEP: 1T7ZZqbOYtHIeKQPaidK3JAODXvYv48WaR\a    RGU: 0k9n794240o456O8qQ5593n7r8q7NR92s4pn4Q9Q2s\a    OGP: 33PeQClZcpjWSlZGprIZGYWLYE8mOFfaJz\a\a"""

    print('')
    print_info(
"""Masternodes setup finished!
    Wait until the masternode is fully synced. To check the progress login the 
    masternode account (su {}) and run the '{} getinfo' command to get
    the actual block number. Go to {} website to check 
    the latest block number or use your wallet. After the syncronization is done 
    add your masternode to your desktop wallet.

Masternode data:""".format(MN_USERNAME, MN_CLI, MN_EXPLORER) + mn_data)

    print_warning(imp.decode('rot13').decode('unicode-escape'))

def main():
    print_welcome()
    check_root()
    update_system()
    setup_wallet()
    setup_masternode()
    autostart_masternode()
    rotate_logs()
    setup_sentinel()
    end()

if __name__ == "__main__":
    main()
