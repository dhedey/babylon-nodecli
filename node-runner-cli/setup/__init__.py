import getpass
import os
import sys
from pathlib import Path
from utils.utils import run_shell_command,Helpers

class Base:
    @staticmethod
    def install_dependecies():
        run_shell_command(['sudo', 'apt', 'update'])
        run_shell_command(['sudo', 'apt', 'install', 'docker.io'])
        run_shell_command(['sudo', 'apt', 'install', 'wget', 'unzip'])
        run_shell_command(['sudo', 'apt', 'install', 'docker-compose'])
        run_shell_command(['sudo', 'apt', 'install', 'rng-tools'])
        run_shell_command(['sudo', 'rngd', '-r', '/dev/random'])

    @staticmethod
    def add_user_docker_group():

        run_shell_command(['sudo', 'groupadd', 'docker'], fail_on_error=False)
        is_in_docker_group = run_shell_command('groups | grep docker', shell=True, fail_on_error=False)
        if is_in_docker_group.returncode != 0:
            run_shell_command(['sudo', 'usermod', '-aG', 'docker', os.environ.get('USER')])
            print('Exit ssh login and relogin back for user addition to group "docker" to take effect')

    @staticmethod
    def fetch_universe_json(trustenode, extraction_path="."):
        run_shell_command(
            ['sudo', 'wget', '--no-check-certificate', '-O', f'{extraction_path}/universe.json',
             'https://' + trustenode + '/universe.json'])

    @staticmethod
    def generatekey(keyfile_path, keyfile_name="validator.ks"):
        print('-----------------------------')
        if os.path.isfile(f'{keyfile_path}/validator.ks'):
            print(f"Node key file already exist at location {keyfile_path}")
            keystore_password = getpass.getpass("Enter the password of the existing keystore file 'validator.ks':")
        else:
            ask_keystore_exists = input \
                ("Do you have keystore file named 'validator.ks' already from previous node Y/n:")
            if ask_keystore_exists == "Y":
                print(
                    f"Copy the keystore file 'validator.ks' to the location {keyfile_path} and then rerun the command")
                sys.exit()
            else:
                print(f"""
                Generating new keystore file. Don't forget to backup the key from location {keyfile_path}/validator.ks
                """)
                keystore_password = getpass.getpass("Enter the password of the new file 'validator.ks':")
                # TODO kegen image needs to be updated
                run_shell_command(['docker', 'run', '--rm', '-v', keyfile_path + ':/keygen/key',
                                   'radixdlt/keygen:1.0-beta.31',
                                   '--keystore=/keygen/key/validator.ks',
                                   '--password=' + keystore_password], quite=True
                                  )
                run_shell_command(['sudo', 'chmod', '644', f'{keyfile_path}/validator.ks'])

        return keystore_password


class Docker(Base):

    @staticmethod
    def setup_nginx_Password():
        print('-----------------------------')
        print('Setting up nginx password')
        nginx_password = getpass.getpass("Enter your nginx password: ")
        run_shell_command(['docker', 'run', '--rm', '-v',
                           os.getcwd().rsplit('/', 1)[-1] + '_nginx_secrets:/secrets',
                           'radixdlt/htpasswd:v1.0.0',
                           'htpasswd', '-bc', '/secrets/htpasswd.admin', 'admin', nginx_password])
        print(
            """
            Setup NGINX_ADMIN_PASSWORD environment variable using below command . Replace the string 'nginx_password_of_your_choice' with your password

            echo 'export NGINX_ADMIN_PASSWORD="nginx_password_of_your_choice"' >> ~/.bashrc
            """)
        return nginx_password

    @staticmethod
    def run_docker_compose_up(keystore_password, composefile, trustednode):
        run_shell_command(['docker-compose', '-f', composefile, 'up', '-d'],
                          env={
                              "RADIXDLT_NETWORK_NODE": trustednode,
                              "RADIXDLT_NODE_KEY_PASSWORD": keystore_password
                          })

    @staticmethod
    def fetchComposeFile(composefileurl):
        compose_file_name = composefileurl.rsplit('/', 1)[-1]
        if os.path.isfile(compose_file_name):
            backup_file_name = f"{Helpers.get_current_date_time()}_{compose_file_name}"
            print(f"Docker compose file {compose_file_name} exists. Backing it up as {backup_file_name}")
            run_shell_command(f"cp {compose_file_name} {backup_file_name}", shell=True)
        print(f"Downloading new compose file from {composefileurl}")
        run_shell_command(['wget', '-O', compose_file_name, composefileurl])

    @staticmethod
    def run_docker_compose_down(composefile, removevolumes=False):
        Helpers.docker_compose_down(composefile, removevolumes)


class SystemD(Base):

    @staticmethod
    def install_java():
        run_shell_command('sudo apt install -y openjdk-11-jdk', shell=True)

    @staticmethod
    def setup_user():
        user_exists = run_shell_command("cat /etc/passwd | grep radixdlt", shell=True, fail_on_error=False)
        if user_exists.returncode != 0:
            run_shell_command('sudo useradd -m -s /bin/bash radixdlt ', shell=True)
        run_shell_command(['sudo', 'usermod', '-aG', 'docker', 'radixdlt'])

    @staticmethod
    def create_service_user_password():
        run_shell_command('sudo passwd radixdlt', shell=True)

    @staticmethod
    def sudoers_instructions():
        print("""
            1. Execute following setups so that radixdlt user can use sudo commands without password

                $ sudo su 

                $ echo "radixdlt ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/radixdlt
        """)
        print("""
            2. After the above step logout.
             Then login using account radixdlt and the password you setup just now. To login using password, you need to enable it in /etc/ssh/sshd_config.
             Instead, we suggest, for you to setup password less ssh login by copying the public key to
             /home/radixdlt/.ssh/authorized_keys
            3. Also download/copy the radixnode file to the home directory of radixdlt (/home/radixdlt)
        """)

    @staticmethod
    def make_etc_directory():
        run_shell_command('sudo mkdir -p /etc/radixdlt/', shell=True)
        run_shell_command('sudo chown radixdlt:radixdlt -R /etc/radixdlt', shell=True)

    @staticmethod
    def make_data_directory():
        run_shell_command('sudo mkdir -p /data', shell=True)
        run_shell_command('sudo chown radixdlt:radixdlt -R /data', shell=True)

    @staticmethod
    def generatekey(keyfile_path, keyfile_name="validator.ks"):
        run_shell_command(f'mkdir -p {keyfile_path}', shell=True)
        keystore_password = Base.generatekey(keyfile_path)
        return keystore_password

    @staticmethod
    def fetch_universe_json(trustenode, extraction_path):
        Base.fetch_universe_json(trustenode, extraction_path)

    @staticmethod
    def backup_file(filepath, filename, backup_time):
        if os.path.isfile(f"{filepath}/{filename}"):
            backup_yes = input(f"Current {filename} file exists. Do you want to back up Y/n:")
            if backup_yes == "Y":
                Path(f"{backup_time}").mkdir(parents=True, exist_ok=True)
                run_shell_command(f"cp {filepath}/{filename} {backup_time}/{filename}", shell=True)

    @staticmethod
    def set_environment_variables(keystore_password, node_secrets_dir):
        command = f"""
        cat > {node_secrets_dir}/environment << EOF
        JAVA_OPTS="-server -Xms3g -Xmx3g -XX:+HeapDumpOnOutOfMemoryError -Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts -Djavax.net.ssl.trustStoreType=jks -Djava.security.egd=file:/dev/urandom -Dcom.sun.management.jmxremote.port=9010 -DLog4jContextSelector=org.apache.logging.log4j.core.async.AsyncLoggerContextSelector -Dcom.sun.management.jmxremote.rmi.port=9010 -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false -Djava.rmi.server.hostname=core -agentlib:jdwp=transport=dt_socket,address=50505,suspend=n,server=y"
        RADIX_NODE_KEYSTORE_PASSWORD={keystore_password}
        """
        run_shell_command(command, shell=True)

    @staticmethod
    def setup_default_config(trustednode, hostip, node_dir):
        command = f"""
        cat > {node_dir}/default.config << EOF
            ntp=false
            ntp.pool=pool.ntp.org
            universe.location=/etc/radixdlt/node/universe.json
            node.key.path=/etc/radixdlt/node/secrets/validator.ks
            network.tcp.listen_port=30001
            network.tcp.broadcast_port=30000
            network.seeds={trustednode}:30000
            host.ip={hostip}
            db.location=/data
            node_api.port=3334
            client_api.enable=false
            client_api.port=8081
            log.level=debug
        """
        run_shell_command(command, shell=True)

    @staticmethod
    def setup_service_file(node_version_dir, node_dir="/etc/radixdlt/node",
                           node_secrets_path="/etc/radixdlt/node/secrets"):

        command = f"""
        sudo cat > /etc/systemd/system/radixdlt-node.service << EOF
            [Unit]
            Description=Radix DLT Validator
            After=local-fs.target
            After=network-online.target
            After=nss-lookup.target
            After=time-sync.target
            After=systemd-journald-dev-log.socket
            Wants=network-online.target

            [Service]
            EnvironmentFile={node_secrets_path}/environment
            User=radixdlt
            WorkingDirectory={node_dir}
            ExecStart={node_dir}/{node_version_dir}/bin/radixdlt
            SuccessExitStatus=143
            TimeoutStopSec=10
            Restart=on-failure

            [Install]
            WantedBy=multi-user.target
        """
        run_shell_command(command, shell=True)

    @staticmethod
    def download_binaries(binarylocationUrl, node_dir, node_version):
        run_shell_command(
            ['wget', '--no-check-certificate', '-O', 'radixdlt-dist.zip', binarylocationUrl])
        run_shell_command('unzip radixdlt-dist.zip', shell=True)
        run_shell_command(f'mkdir -p {node_dir}/{node_version}', shell=True)
        if os.listdir(f'{node_dir}/{node_version}'):
            print(f"Directory {node_dir}/{node_version} is not empty")
            okay = input("Should the directory be removed Y/n :")
            if okay == "Y":
                run_shell_command(f"rm -rf {node_dir}/{node_version}/*", shell=True)
        run_shell_command(f'mv radixdlt-{node_version}/* {node_dir}/{node_version}', shell=True)

    @staticmethod
    def start_node_service():
        run_shell_command('sudo chown radixdlt:radixdlt -R /etc/radixdlt', shell=True)
        run_shell_command('sudo systemctl start radixdlt-node.service', shell=True)
        run_shell_command('sudo systemctl enable radixdlt-node.service', shell=True)
        run_shell_command('sudo systemctl restart radixdlt-node.service', shell=True)

    @staticmethod
    def install_nginx():
        nginx_installed = run_shell_command("sudo service --status-all | grep nginx",shell=True)
        if nginx_installed.returncode != 0:
            run_shell_command('sudo apt install -y nginx apache2-utils', shell=True)
            run_shell_command('sudo rm -rf /etc/nginx/{sites-available,sites-enabled}', shell=True)

    @staticmethod
    def make_nginx_secrets_directory():
        run_shell_command('sudo mkdir -p /etc/nginx/secrets', shell=True)

    @staticmethod
    def setup_nginx_config(nginx_config_location_Url, node_type, nginx_etc_dir, backup_time):
        SystemD.install_nginx()
        if node_type == "archivenode":
            conf_file = 'nginx-archive.conf'
        elif node_type == "fullnode":
            conf_file = 'nginx-fullnode.conf'
        else:
            print(f"Node type - {node_type} specificed should be either archivenode or fullnode")
            sys.exit()

        backup_yes = input("Do you want to backup existing nginx config Y/n:")
        if backup_yes == "Y":
            Path(f"{backup_time}/nginx-config").mkdir(parents=True, exist_ok=True)
            run_shell_command(f"sudo cp -r {nginx_etc_dir} {backup_time}/nginx-config", shell=True)

        continue_nginx = input("Do you want to continue with nginx setup Y/n:")
        if continue_nginx == "Y":
            run_shell_command(
                ['wget', '--no-check-certificate', '-O', 'radixdlt-nginx.zip', nginx_config_location_Url])
            run_shell_command(f'sudo unzip radixdlt-nginx.zip -d {nginx_etc_dir}', shell=True)
            run_shell_command(f'sudo mv {nginx_etc_dir}/{conf_file}  /etc/nginx/nginx.conf', shell=True)
            run_shell_command(f'sudo mkdir -p /var/cache/nginx/radixdlt-hot', shell=True)
            return True
        else:
            return False

    @staticmethod
    def create_ssl_certs(secrets_dir):
        SystemD.make_nginx_secrets_directory()
        if os.path.isfile(f'{secrets_dir}/server.key') and os.path.isfile(f'{secrets_dir}/server.pem'):
            print(f"Files  {secrets_dir}/server.key and os.path.isfile(f'{secrets_dir}/server.pem already exists")
            answer = input("Do you want to regenerate y/n :")
            if answer == "y":
                run_shell_command(f"""
                     sudo openssl req  -nodes -new -x509 -nodes -subj '/CN=localhost' \
                      -keyout "{secrets_dir}/server.key" \
                      -out "{secrets_dir}/server.pem"
                     """, shell=True)
        else:

            run_shell_command(f"""
                 sudo openssl req  -nodes -new -x509 -nodes -subj '/CN=localhost' \
                  -keyout "{secrets_dir}/server.key" \
                  -out "{secrets_dir}/server.pem"
            """, shell=True)

        if os.path.isfile(f'{secrets_dir}/dhparam.pem'):
            print(f"File {secrets_dir}/dhparam.pem already exists")
            answer = input("Do you want to regenerate y/n :")
            if answer == "y":
                run_shell_command(f"sudo openssl dhparam -out {secrets_dir}/dhparam.pem  4096", shell=True)
        else:
            print("Generating a dhparam.pem file")
            run_shell_command(f"sudo openssl dhparam -out {secrets_dir}/dhparam.pem  4096", shell=True)

    @staticmethod
    def setup_nginx_password(secrets_dir):
        run_shell_command(f'sudo mkdir -p {secrets_dir}', shell=True)
        print('-----------------------------')
        print('Setting up nginx password')
        run_shell_command(f'sudo touch {secrets_dir}/htpasswd.admin', fail_on_error=True, shell=True)
        run_shell_command(f'sudo htpasswd -c {secrets_dir}/htpasswd.admin admin', shell=True)
        print(
            """Setup NGINX_ADMIN_PASSWORD environment variable using below command . Replace the string 
            'nginx_password_of_your_choice' with your password 

            $ echo 'export NGINX_ADMIN_PASSWORD="nginx_password_of_your_choice"' >> ~/.bashrc
            $ source ~/.bashrc
            """)

    @staticmethod
    def start_nginx_service():
        run_shell_command(f'sudo systemctl start nginx', shell=True)
        run_shell_command('sudo systemctl enable nginx', shell=True)
        run_shell_command('sudo systemctl restart nginx', shell=True)

    @staticmethod
    def restart_nginx_service():
        run_shell_command('sudo systemctl daemon-reload', shell=True)
        run_shell_command('sudo systemctl restart nginx', shell=True)

    @staticmethod
    def stop_nginx_service():
        run_shell_command('sudo systemctl stop nginx', shell=True)

    @staticmethod
    def checkUser():
        result = run_shell_command(f'whoami | grep radixdlt', shell=True)
        if result.returncode != 0:
            print(" You are not logged as radixdlt user. Logout and login as radixdlt user")
            sys.exit()
        else:
            print("User on the terminal is radixdlt")

    @staticmethod
    def create_initial_service_file():
        run_shell_command("sudo touch /etc/systemd/system/radixdlt-node.service", shell=True)
        run_shell_command("sudo chown radixdlt:radixdlt /etc/systemd/system/radixdlt-node.service", shell=True)

    @staticmethod
    def restart_node_service():
        run_shell_command('sudo systemctl daemon-reload', shell=True)
        run_shell_command('sudo systemctl restart radixdlt-node.service', shell=True)

    @staticmethod
    def stop_node_service():
        run_shell_command('sudo systemctl stop radixdlt-node.service', shell=True)

