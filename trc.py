#! /usr/bin/env python
from subprocess import Popen,PIPE,STDOUT
import collections
import os
import os.path
import binascii
import sys
import time
import math
import json
from urllib2 import urlopen

BOOTSTRAP_URL = "https://terracoin.io/bin/bootstrap/"
SENTINEL_GIT_URL = "https://github.com/terracoin/sentinel.git"
STATUS_PAGE_GIT_URL = "https://github.com/thesin-/terracoind-status.git"
STATUS_ENABLED = False
SERVICES_URL = "https://services.terracoin.io/"
SERVICES_TOOLS = "terracoinservices-updater-v1.tgz"
SERVICES_TOOLS_DIR = "terracoinservices-updater"
SERVICES_ENABLED = False

# Maybe pull this from online, setup a file in bin on terracoin.io?
TERRACOIN_WALLET = "https://terracoin.io/bin/terracoin-core-current/terracoin-LATEST-x86_64-linux-gnu.tar.gz"

MN_USERNAME = "trcmn"
MN_PORT = 13333
MN_RPCPORT = 22350
MN_RPCUSER = binascii.hexlify(os.urandom(6))
MN_RPCPASS = binascii.hexlify(os.urandom(16))
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
COLLATERAL_ADDRESS = ""

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
    print_info("Terracoin masternode installer v1.4")

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
    run_command("apt-get --assume-yes install wget tar")

    print_info("Downloading wallet...")
    run_command("wget {} -O /tmp/wallet.tar.gz".format(TERRACOIN_WALLET))
    run_command("cd /tmp && tar xzf wallet.tar.gz")
    run_command("find /tmp -name {} -exec cp {{}} /usr/local/bin \;".format(MN_DAEMON))
    run_command("find /tmp -name {} -exec cp {{}} /usr/local/bin \;".format(MN_CLI))

def get_collateral_address():
    global COLLATERAL_ADDRESS
    print_info("Enter the public address that holds the 5000TRC collateral for this masternode")
    collateral_address = raw_input("address: ")
    COLLATERAL_ADDRESS = collateral_address
    # FIXME add explorer or insight call to check the address has a collateral?

def setup_masternode():
    global PRIVATE_KEY
    print_info("Setting up masternode...")
    run_command("useradd --create-home -G sudo {}".format(MN_USERNAME))

    need_credential = True
    if os.path.isfile("/usr/local/bin/{}".format(MN_DAEMON)) and os.path.isfile("/usr/local/bin/{}".format(MN_CLI)) and os.path.isfile("/home/{}/{}/{}".format(MN_USERNAME, MN_LFOLDER, MN_CONFIGFILE)):
        need_credential = False
        run_command_as(MN_USERNAME, "{} stop".format(MN_CLI))
        PRIVATE_KEY = "using the previous private key"
        print_info("Using the previous rpc username, rpc password and private key.")

    if need_credential:
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
{}""".format(MN_RPCUSER, MN_RPCPASS, MN_RPCPORT, MN_PORT, SERVER_IP, MN_PORT, masternode_priv_key, MN_NODELIST)
    
        # creates folder structure
        run_command_as(MN_USERNAME, "mkdir -p /home/{}/{}/".format(MN_USERNAME, MN_LFOLDER))
        run_command_as(MN_USERNAME, "touch /home/{}/{}/{}".format(MN_USERNAME, MN_LFOLDER, MN_CONFIGFILE))
        
        print_info("Saving config file...")
        with open('/home/{}/{}/{}'.format(MN_USERNAME, MN_LFOLDER, MN_CONFIGFILE), 'w') as f:
            f.write(config)
        
    print_info("Installing bootstrap dependencies...")
    run_command("apt-get --assume-yes install wget gpg gzip")
    print_info("Downloading blockchain bootstrap file...")
    filename = "bootstrap.dat.gz"
    run_command_as(MN_USERNAME, "cd && wget '{}/{}'".format(BOOTSTRAP_URL, filename))
    run_command_as(MN_USERNAME, "cd && wget '{}/bootstrap-SHA256SUM.asc'".format(BOOTSTRAP_URL))
    run_command_as(MN_USERNAME, "cd && wget '{}/verify.sh'".format(BOOTSTRAP_URL))
    run_command_as(MN_USERNAME, "cd && wget '{}/verify.sh'".format(BOOTSTRAP_URL))
    print_info("Verifying Authenticity of bootstrap file...")
    run_command_as(MN_USERNAME, "cd && rm -f good && bash verify.sh && touch good")

    bootstrap = ""
    if (os.path.isfile("/home/{}/good".format(MN_USERNAME))):
        print_info("Verification passed, Decompressing...")
        run_command_as(MN_USERNAME, "cd && rm -f good verify.sh bootstrap-SHA256SUM.asc && rm -rf {0}/blocks {0}/chainstate".format(MN_LFOLDER))
        run_command_as(MN_USERNAME, "cd && gzip -d {}".format(filename))
        bootstrap = " -loadblock=/home/{}/bootstrap.dat".format(MN_USERNAME)
    else:
        print_warning("Verification failed, Not using bootstrap...")
       
    os.system('su - {} -c "{}" '.format(MN_USERNAME, MN_DAEMON + '{} -daemon'.format(bootstrap)))
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
    f.write('''/home/{0}/{1}/debug.log /home/{0}/{1}/trcupdater.log {{
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
    print_info("Installing Sentinel dependencies...")
    run_command("apt-get -y install python-virtualenv git virtualenv")

    # download and install sentinel
    run_command_as(MN_USERNAME, "git clone {} /home/{}/{}/sentinel".format(SENTINEL_GIT_URL, MN_USERNAME, MN_LFOLDER))
    run_command_as(MN_USERNAME, "cd /home/{}/{}/sentinel && virtualenv ./venv ".format(MN_USERNAME, MN_LFOLDER))
    run_command_as(MN_USERNAME, "cd /home/{}/{}/sentinel && ./venv/bin/pip install -r requirements.txt".format(MN_USERNAME, MN_LFOLDER))

    # run sentinel every minutes
    job = "* * * * * cd /home/{}/{}/sentinel && SENTINEL_DEBUG=1 ./venv/bin/python bin/sentinel.py >> sentinel.log 2>&1".format(MN_USERNAME, MN_LFOLDER)
    crontab(job)

    # try to update sentinel every day
    job = "* * 1 * * cd /home/{}/{}/sentinel && git pull {}".format(MN_USERNAME, MN_LFOLDER, SENTINEL_GIT_URL)
    crontab(job)

def setup_services():
    global SERVICES_ENABLED

    # no services support
    if SERVICES_URL == "":
        return
    if SERVICES_TOOLS == '':
        return
    if SERVICES_TOOLS_DIR == '':
        return

    # Ask if we want to setup services
    print_info("You will require an account at https://services.terracoin.io")
    res = raw_input("Install Services Tools? (y/n)").lower()
    if (res == 'n' or res == 'no'):
        return

    SERVICES_ENABLED = True

    if COLLATERAL_ADDRESS == '':
        get_collateral_address()

    print_info("Login to https://services.terracoin.io (My Account -> Account Settings) and copy the API key")
    apikey = raw_input("API key: ")

    print_info("Setting up Services (/home/{}/{}/terracoinservices-updater)...".format(MN_USERNAME, MN_LFOLDER))

    # install dependencies
    print_info("Installing Services Tools dependencies...")
    run_command("apt-get -y install wget tar")

    # download and install services tools
    run_command_as(MN_USERNAME, "cd && wget '{}/downloads/{}' -O /home/{}/{}/{}".format(SERVICES_URL, SERVICES_TOOLS, MN_USERNAME, MN_LFOLDER, SERVICES_TOOLS))
    run_command_as(MN_USERNAME, "cd /home/{}/{} && tar xzf {}".format(MN_USERNAME, MN_LFOLDER, SERVICES_TOOLS))

    # configure services tools
    config = """################
# terracoinservices-updater configuration
################

our %settings = (
	# Enter your Terracoin Services api key here
	'api_key' => '{}'
);

our %masternodes = (
	'{}' => {{
		'rpc_host'				=> 'localhost',
		'rpc_port'				=> {},
		'rpc_user'				=> '{}',
		'rpc_password'				=> '{}',
		'daemon_autorestart'			=> 'disabled',
		'daemon_binary'				=> '/usr/local/bin/{}',
		'daemon_datadir'			=> '/home/{}/{}'
	}}
);

#
1;""".format(apikey, COLLATERAL_ADDRESS, MN_RPCPORT, MN_RPCUSER, MN_RPCPASS, MN_DAEMON, MN_USERNAME, MN_LFOLDER)

    run_command_as(MN_USERNAME, "cd && rm -f /home/{}/{}/{}/terracoinservices.conf".format(MN_USERNAME, MN_LFOLDER, SERVICES_TOOLS_DIR))
    run_command_as(MN_USERNAME, "touch /home/{}/{}/{}/terracoinservices.conf".format(MN_USERNAME, MN_LFOLDER, SERVICES_TOOLS_DIR))

    print_info("Saving config file...")
    with open('/home/{}/{}/{}/terracoinservices.conf'.format(MN_USERNAME, MN_LFOLDER, SERVICES_TOOLS_DIR), 'w') as f:
        f.write(config)

    # run services tool every 2 minutes
    job = "*/2 * * * *   /home/{}/{}/{}/trcupdater >> /home/{}/{}/trcupdater.log 2>&1".format(MN_USERNAME, MN_LFOLDER, SERVICES_TOOLS_DIR, MN_USERNAME, MN_LFOLDER)
    crontab(job)

    regstatus = False
    try:
        apicall = '{}api/v1/setappdata?api_key={}&do=add_masternode&name={}&address={}'.format(SERVICES_URL, apikey, 'MN_' + SERVER_IP.replace('.', '_'), COLLATERAL_ADDRESS)
        response = urlopen(apicall)
        reg = json.load(response)
        if (reg['status'] == 'ok'):
            regstatus = True
    except urllib2.HTTPError, e:
        print_error('HTTPError = ' + str(e.code))
    except urllib2.URLError, e:
        print_error('URLError = ' + str(e.reason))
    except httplib.HTTPException, e:
        print_error('HTTPException')
    except Exception:
        print_error('generic exception')

    if (regstatus):
        print_info('Masternode is registered on Services in your account!')
        SERVICES_ENABLED = False
    else:
        print_warning('Auto registration on Services failed ({}), please do it manually'.format(reg['message']))

def setup_statuspage():
    global STATUS_ENABLED
    # no status page support
    if STATUS_PAGE_GIT_URL == "":
        return

    print_info("This will install and setup a web status page for your masternode")
    res = raw_input("Install Status Page? (y/n)").lower()
    if (res == 'n' or res == 'no'):
        return

    # FIXME Not ready
    print_warning('Status Page setup is not yet implemented')
    return
    STATUS_ENABLED = True

    # Ask if we want to setup status page
    if COLLATERAL_ADDRESS == '':
        get_collateral_address()

    print_info("Setting up Status Page Using Apache (/var/www/terracoind-status)...")

    # install dependencies
    print_info("Installing Status Page dependencies...")
    run_command("apt-get -y install libapache-mod-php curl")

    # download and install status page
    run_command("cd /var/www && git clone {}".format(STATUS_PAGE_GIT_URL))

    # configure status page
    # FIXME Add config

    # setup cron jobs
    job = "*/5 *  *   *   *  curl -Ssk http://127.0.0.1/stats.php > /dev/null"
    crontab(job)
    job = "*/5 *  *   *   *  curl -Ssk http://127.0.0.1/peercount.php > /dev/null"
    crontab(job)
    job = "*/5 *  *   *   *  curl -Ssk http://127.0.0.1/masternodecount.php > /dev/null"
    crontab(job)
    job = "*/5 *  *   *   *  curl -Ssk http://127.0.0.1/difficulty.php > /dev/null"
    crontab(job)
    job = "*/5 *  *   *   *  curl -Ssk http://127.0.0.1/sysstats.php > /dev/null"
    crontab(job)

    # try to update status page every day
    job = "* * 1 * * cd /var/www/terracoind-status && git pull {}".format(STATUS_PAGE_GIT_URL)
    crontab(job)
    
def end():

    mn_base_data = """
    Masternode Info
    IP: {}
    Private key: {}
    Transaction ID: [The transaction id of the desposit. 'masternode outputs']
    Transaction index: [The transaction index of the desposit. 'masternode outputs']
    --------------------------------------------------
"""

    mn_data = mn_base_data.format(SERVER_IP + ":" + str(MN_PORT), PRIVATE_KEY)

    services_data = ""
    if SERVICES_ENABLED:
        services_base_data = """

    Do not forget to register your MasterNode on {}

"""
        services_data = services_base_data.format(SERVICES_URL)

    status_data = ""
    if STATUS_ENABLED:
        status_base_data = """
    Status Page available at: http://{}/
    --------------------------------------------------
"""
        status_data = status_base_data.format(SERVER_IP)

    print('')
    print_info(
"""Masternodes setup finished!
    Wait until the masternode is fully synced. To check the progress login the
    masternode account (su {}) and run the '{} getinfo' command
    to get the actual block number. Go to {}
    website to check the latest block number or use your wallet. After the
    syncronization is done add your masternode to your desktop wallet.
{}
Masternode data:""".format(MN_USERNAME, MN_CLI, MN_EXPLORER, services_data) + mn_data + status_data)

def main():
    print_welcome()
    check_root()
    update_system()
    setup_wallet()
    setup_masternode()
    autostart_masternode()
    rotate_logs()
    setup_sentinel()
    setup_services()
    setup_statuspage()
    end()

if __name__ == "__main__":
    main()
